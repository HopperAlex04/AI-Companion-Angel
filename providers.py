from typing import override, Any
import json
import requests
from sqlite3 import Connection
from dtos import PromptItem
from tools import ToolRegistry

# import os
# import json
# import requests

SYSTEM_PROMPT = '''You are Angel, AI companion and research assistant.
You are designed to aid the user in designing AI systems by searching documentation, finding bugs, providing analysis of planned features and proposing implementations when requested
Use web_search when facts may be stale or unknown. Do not search for casual conversation.'''

MAX_TOOL_ROUNDS = 4
LLAMA_CHAT_URL = "http://0.0.0.0:8080/v1/chat/completions"
LLAMA_MODEL = "google/gemma-4-E4B-it-qat-q4_0-gguf:IT"


class ModelProvider:
    def generate(self, prompt: PromptItem) -> str:
        raise NotImplementedError("Subclasses must implement this method")

class MockProvider(ModelProvider):
    @override
    def generate(self, prompt: PromptItem):
        return f"prompt recieved: {prompt.prompt_text}"

class LlamaCPPProvider(ModelProvider):
    def __init__(self, conn: Connection, registry: ToolRegistry | None = None):
        self.conn = conn
        self.registry = registry or ToolRegistry()
        self._ensure_schema()

    @override
    def generate(self, prompt: PromptItem) -> str:
        # self.conversation.append({"role": "user", "content": prompt.prompt_text})
        conversation = []
        if not self.conversation_exists(prompt.conversation_id):
            conversation.append({"role": "system", "content": SYSTEM_PROMPT})
            conversation.append({"role": "user", "content": prompt.prompt_text})
            # TODO: Set up title generation
            self.add_conversation(str(prompt.conversation_id))
            self.add_message(prompt.conversation_id, "system", SYSTEM_PROMPT)
            self.add_message(prompt.conversation_id, "user", prompt.prompt_text)
        else:
            conversation = self.convert_conv(self.retrieve_conversation(prompt.conversation_id))
            print(conversation)
            conversation.append({"role": "user", "content": prompt.prompt_text})
            self.add_message(prompt.conversation_id, "user", prompt.prompt_text)

        for _ in range(MAX_TOOL_ROUNDS):
            assistant_message = self._chat(conversation)
            content = assistant_message.get("content") or ""
            tool_calls = assistant_message.get("tool_calls") or []

            if not tool_calls:
                conversation.append({"role": "assistant", "content": content})
                self.add_message(prompt.conversation_id, "assistant", content)
                return content

            assistant_row = {
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            }
            conversation.append(assistant_row)
            self.add_message(
                prompt.conversation_id,
                "assistant",
                content,
                metadata={"tool_calls": tool_calls},
            )

            for call in tool_calls:
                function = call.get("function") or {}
                name = function.get("name") or ""
                raw_args = function.get("arguments") or "{}"
                call_id = call.get("id") or ""
                result = self.registry.dispatch(name, raw_args)
                conversation.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result,
                })
                self.add_message(
                    prompt.conversation_id,
                    "tool",
                    result,
                    metadata={"tool_call_id": call_id, "name": name},
                )

        assistant_message = self._chat(conversation)
        content = assistant_message.get("content") or ""
        conversation.append({"role": "assistant", "content": content})
        self.add_message(prompt.conversation_id, "assistant", content)
        return content

    def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": LLAMA_MODEL,
            "messages": messages,
            "temperature": 0.7,
        }
        tools = self.registry.openai_tools()
        if tools:
            payload["tools"] = tools
        response = requests.post(LLAMA_CHAT_URL, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]

    def _ensure_schema(self) -> None:
        columns = [
            row[1]
            for row in self.conn.execute("PRAGMA table_info(messages)").fetchall()
        ]
        if "metadata" not in columns:
            self.conn.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")
            self.conn.commit()

    def retrieve_conversation(self, conv_id: int) -> list[tuple[str, str | None, str | None]]:
        # Grabs all messages, sorted by id, that belong to a conversation
        rows = self.conn.execute(
            "select role, content, metadata from messages where conversation_id = ? order by id",
            (conv_id,),
        ).fetchall()
        return rows

    def add_message(
        self,
        conv_id: int,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Add a message to a specified conversation by adding an entry to the messages table
        metadata_json = json.dumps(metadata) if metadata is not None else None
        self.conn.execute(
            "INSERT INTO messages (role, content, conversation_id, metadata) values (?,?,?,?)",
            (role, content, conv_id, metadata_json),
        )
        self.conn.commit()

    def add_conversation(self, title: str) -> int:
        # Add new conversation, use default time
        cursor = self.conn.execute("INSERT INTO conversations (title) VALUES (?) RETURNING id", (title,))
        con_id = cursor.fetchone()[0]
        self.conn.commit()
        return con_id

    def conversation_exists(self, conv_id: int) -> bool:
        # Check if a conversation with the given ID exists
        row = self.conn.execute("SELECT 1 FROM conversations WHERE id = ? LIMIT 1", (conv_id,)).fetchone()
        return row is not None

    def convert_conv(
        self, raw_conv: list[tuple[str, str | None, str | None]]
    ) -> list[dict[str, Any]]:
        conversation = []
        for role, content, metadata_raw in raw_conv:
            message: dict[str, Any] = {"role": role, "content": content or ""}
            metadata: dict[str, Any] = {}
            if metadata_raw:
                try:
                    metadata = json.loads(metadata_raw)
                except json.JSONDecodeError:
                    metadata = {}
            if role == "assistant" and metadata.get("tool_calls"):
                message["tool_calls"] = metadata["tool_calls"]
            if role == "tool":
                if metadata.get("tool_call_id"):
                    message["tool_call_id"] = metadata["tool_call_id"]
                if metadata.get("name"):
                    message["name"] = metadata["name"]
            conversation.append(message)
        return conversation

    def get_all_conversations(self) -> list[dict[str, Any]]:
        # Retrieve all conversations from the database
        rows = self.conn.execute("SELECT * FROM conversations").fetchall()
        return [{"id": row[0], "title": row[1], "created_at": row[2]} for row in rows]
