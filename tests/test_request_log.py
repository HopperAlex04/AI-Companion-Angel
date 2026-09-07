import logging
import time

import pytest
from fastapi.testclient import TestClient

import request_log
from main import app
from request_log import RequestLog


PROMPT = {"prompt_text": "hello", "conversation_id": 1}


class FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    def __init__(self, *, get_result=None, post_result=None, error: Exception | None = None):
        self.get_result = get_result
        self.post_result = post_result
        self.error = error

    async def get(self, url):
        if self.error:
            raise self.error
        return self.get_result

    async def post(self, url, json=None):
        if self.error:
            raise self.error
        return self.post_result


class FakeClock:
    """Feeds fixed perf_counter values so duration matches RequestLog._duration()."""

    def __init__(self, values: list[float]):
        self.values = list(values)

    def __call__(self) -> float:
        return self.values.pop(0)


class _TimeProxy:
    """Only RequestLog sees the fake clock; httpx keeps the real perf_counter."""

    def __init__(self, clock: FakeClock):
        self.perf_counter = clock

    def __getattr__(self, name: str):
        return getattr(time, name)


def pin_request_clock(monkeypatch: pytest.MonkeyPatch, values: list[float]) -> None:
    monkeypatch.setattr(request_log, "time", _TimeProxy(FakeClock(values)))


def _records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if hasattr(record, "request_id")]


def _pair(records: list[logging.LogRecord]) -> tuple[logging.LogRecord, logging.LogRecord]:
    assert len(records) == 2
    started, finished = records
    assert started.request_id == finished.request_id
    assert started.request_id
    return started, finished


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def caplog_info(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.INFO)
    return caplog


def test_request_log_duration_is_rounded_perf_counter_delta(monkeypatch, caplog_info):
    # Mirrors RequestLog: start captures perf_counter, complete subtracts and rounds to 2 places.
    pin_request_clock(monkeypatch, [10.0, 12.3456])

    req = RequestLog("chat/angel", label="Chat Request")
    req.complete(200)

    started, finished = _pair(_records(caplog_info))
    assert started.getMessage() == f"Chat Request {req.request_id} started"
    assert finished.getMessage() == f"Chat Request {req.request_id} completed"
    assert finished.duration == round(12.3456 - 10.0, 2)
    assert finished.duration == 2.35
    assert finished.status == 200
    assert started.endpoint == finished.endpoint == "chat/angel"


def test_request_log_fail_uses_same_id_and_duration(monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [5.0, 5.004])

    req = RequestLog("conversations")
    req.fail(RuntimeError("boom"))

    started, finished = _pair(_records(caplog_info))
    assert started.levelno == logging.INFO
    assert finished.levelno == logging.ERROR
    assert finished.request_id == req.request_id
    assert finished.duration == round(5.004 - 5.0, 2)
    assert finished.status == 500
    assert finished.error == "boom"


def test_chat_mock_logs_start_and_completion_with_matching_ids(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [1.0, 1.2, 3.0, 3.105])

    first = client.post("/chat/mock", json=PROMPT)
    second = client.post("/chat/mock", json=PROMPT)

    assert first.status_code == 200
    assert first.json() == "prompt recieved: hello"
    assert second.status_code == 200

    records = _records(caplog_info)
    assert len(records) == 4
    first_start, first_done = records[0], records[1]
    second_start, second_done = records[2], records[3]

    assert first_start.request_id == first_done.request_id
    assert second_start.request_id == second_done.request_id
    assert first_start.request_id != second_start.request_id
    assert "started" in first_start.getMessage()
    assert "completed" in first_done.getMessage()
    assert first_done.endpoint == "chat/mock"
    assert first_done.duration == round(1.2 - 1.0, 2)
    assert second_done.duration == round(3.105 - 3.0, 2)
    assert first_done.status == 200


def test_chat_angel_logs_start_and_completion(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [20.0, 20.678])
    monkeypatch.setattr(
        "main.client",
        FakeClient(post_result=FakeResponse(201, {"reply": "ok"})),
    )

    response = client.post("/chat/angel", json=PROMPT)

    assert response.status_code == 200
    assert response.json() == {"reply": "ok"}
    started, finished = _pair(_records(caplog_info))
    assert started.endpoint == finished.endpoint == "chat/angel"
    assert finished.duration == round(20.678 - 20.0, 2)
    assert finished.status == 201


def test_chat_angel_failure_logs_start_and_fail_with_same_id(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [8.0, 8.019])
    monkeypatch.setattr("main.client", FakeClient(error=RuntimeError("upstream down")))

    response = client.post("/chat/angel", json=PROMPT)

    assert response.status_code == 200
    started, finished = _pair(_records(caplog_info))
    assert "failed" in finished.getMessage()
    assert started.request_id == finished.request_id
    assert finished.duration == round(8.019 - 8.0, 2)
    assert finished.status == 500
    assert finished.error == "upstream down"


def test_get_conversations_logs_start_and_completion(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [4.5, 4.54])
    monkeypatch.setattr(
        "main.client",
        FakeClient(get_result=FakeResponse(200, [{"id": 1, "title": "chat"}])),
    )

    response = client.get("/conversations")

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "title": "chat"}]
    started, finished = _pair(_records(caplog_info))
    assert started.endpoint == "conversations"
    assert finished.duration == round(4.54 - 4.5, 2)
    assert finished.status == 200


def test_get_conversations_failure_logs_start_and_fail(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [7.0, 7.011])
    monkeypatch.setattr("main.client", FakeClient(error=RuntimeError("db unavailable")))

    response = client.get("/conversations")

    assert response.status_code == 200
    assert response.json() == {"error": "db unavailable"}
    started, finished = _pair(_records(caplog_info))
    assert started.request_id == finished.request_id
    assert finished.duration == round(7.011 - 7.0, 2)
    assert finished.status == 500
    assert finished.error == "db unavailable"


def test_new_conversation_logs_start_and_completion(client, monkeypatch, caplog_info):
    pin_request_clock(monkeypatch, [9.0, 9.999])
    monkeypatch.setattr(
        "main.client",
        FakeClient(post_result=FakeResponse(200, {"id": 42})),
    )

    response = client.post("/conversations", json={"title": "new"})

    assert response.status_code == 200
    assert response.json() == {"id": 42}
    started, finished = _pair(_records(caplog_info))
    assert started.endpoint == finished.endpoint == "conversations"
    assert finished.duration == round(9.999 - 9.0, 2)
    assert finished.status == 200
