import json

from fastapi.testclient import TestClient

from chat_service import create_app
from config import config
from tests.fakes import ScriptedChat


def test_create_conversation_stays_in_memory(client: TestClient, memory_db):
    response = client.post("/conversations", json={"title": "pipeline test"})
    assert response.status_code == 200
    conv_id = response.json()["id"]
    assert isinstance(conv_id, int)

    listed = client.get("/conversations")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["id"] == conv_id
    assert rows[0]["title"] == "pipeline test"

    db_row = memory_db.execute(
        "SELECT title FROM conversations WHERE id = ?", (conv_id,)
    ).fetchone()
    assert db_row == ("pipeline test",)


def test_generate_runs_full_pipeline_without_llama(
    client: TestClient, memory_db, scripted_chat: ScriptedChat
):
    conv_id = client.post("/conversations", json={"title": "chat"}).json()["id"]

    response = client.post(
        "/generate",
        json={"prompt_text": "hello angel", "conversation_id": conv_id},
    )
    assert response.status_code == 200
    assert response.json() == "mock assistant reply"

    assert len(scripted_chat.calls) == 1
    sent = scripted_chat.calls[0]
    assert sent[-1] == {"role": "user", "content": "hello angel"}

    messages = memory_db.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    ).fetchall()
    assert messages == [
        ("user", "hello angel"),
        ("assistant", "mock assistant reply"),
    ]


def test_generate_for_unknown_conversation_writes_system_prompt(
    client: TestClient, memory_db, scripted_chat: ScriptedChat
):
    # conversation_id 99 is not in the in-memory DB, so generate() creates one.
    response = client.post(
        "/generate",
        json={"prompt_text": "hello", "conversation_id": 99},
    )
    assert response.status_code == 200
    assert response.json() == "mock assistant reply"

    sent = scripted_chat.calls[0]
    assert sent[0] == {"role": "system", "content": config["llama"]["system_prompt"]}
    assert sent[1] == {"role": "user", "content": "hello"}

    titles = [
        row[0] for row in memory_db.execute("SELECT title FROM conversations").fetchall()
    ]
    assert "99" in titles


def test_second_turn_loads_history_from_memory_db(
    client: TestClient, memory_db, scripted_chat: ScriptedChat
):
    conv_id = client.post("/conversations", json={"title": "chat"}).json()["id"]
    client.post(
        "/generate",
        json={"prompt_text": "first", "conversation_id": conv_id},
    )
    scripted_chat.responses.append({"content": "second reply", "tool_calls": []})

    response = client.post(
        "/generate",
        json={"prompt_text": "second", "conversation_id": conv_id},
    )
    assert response.json() == "second reply"

    last_request = scripted_chat.calls[-1]
    contents = [message["content"] for message in last_request]
    assert "first" in contents
    assert "mock assistant reply" in contents
    assert contents[-1] == "second"

    roles = [
        row[0]
        for row in memory_db.execute(
            "SELECT role FROM messages WHERE conversation_id = ? ORDER BY id",
            (conv_id,),
        ).fetchall()
    ]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_tool_round_dispatch_and_persistence(memory_db, registry, fake_search):
    chat = ScriptedChat(
        [
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "web_search",
                            "arguments": json.dumps({"query": "pytest docs"}),
                        },
                    }
                ],
            },
            {"content": "I used search.", "tool_calls": []},
        ]
    )
    app = create_app(memory_db, registry=registry, chat_fn=chat)
    with TestClient(app) as client:
        conv_id = client.post("/conversations", json={"title": "tools"}).json()["id"]
        response = client.post(
            "/generate",
            json={"prompt_text": "search please", "conversation_id": conv_id},
        )

    assert response.json() == "I used search."
    assert fake_search.calls == [{"query": "pytest docs"}]
    assert len(chat.calls) == 2
    tool_message = next(m for m in chat.calls[1] if m["role"] == "tool")
    assert tool_message["content"] == fake_search.result
    assert tool_message["tool_call_id"] == "call_1"

    stored = memory_db.execute(
        "SELECT role, content, metadata FROM messages WHERE conversation_id = ? ORDER BY id",
        (conv_id,),
    ).fetchall()
    roles = [row[0] for row in stored]
    assert roles == ["user", "assistant", "tool", "assistant"]
    assistant_tool_turn = stored[1]
    assert json.loads(assistant_tool_turn[2])["tool_calls"][0]["id"] == "call_1"
    tool_row = stored[2]
    assert tool_row[1] == fake_search.result
    assert json.loads(tool_row[2]) == {"tool_call_id": "call_1", "name": "web_search"}


def test_jobs_snapshot_after_generate(client: TestClient):
    conv_id = client.post("/conversations", json={"title": "jobs"}).json()["id"]
    client.post(
        "/generate",
        json={"prompt_text": "hello", "conversation_id": conv_id},
    )
    jobs = client.get("/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "done"
    assert jobs[0]["conversation_id"] == conv_id

    snapshot = client.get("/").json()
    assert snapshot["queued_count"] == 0
    assert snapshot["current"] is None
