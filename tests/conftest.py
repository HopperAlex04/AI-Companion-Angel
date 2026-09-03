import os

# Must run before chat_service is imported so production does not open chat.db.
os.environ["ANGEL_TESTING"] = "1"

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from chat_service import create_app
from db import init_schema
from tests.fakes import FakeTool, ScriptedChat
from tools import ToolRegistry


@pytest.fixture
def memory_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def scripted_chat() -> ScriptedChat:
    return ScriptedChat([{"content": "mock assistant reply", "tool_calls": []}])


@pytest.fixture
def fake_search() -> FakeTool:
    return FakeTool()


@pytest.fixture
def registry(fake_search: FakeTool) -> ToolRegistry:
    tools = ToolRegistry()
    tools.register(fake_search)
    return tools


@pytest.fixture
def app(memory_db: sqlite3.Connection, registry: ToolRegistry, scripted_chat: ScriptedChat):
    return create_app(memory_db, registry=registry, chat_fn=scripted_chat)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
