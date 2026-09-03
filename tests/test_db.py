import sqlite3

from db import init_schema


def test_init_schema_creates_tables():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "conversations" in tables
    assert "messages" in tables


def test_init_schema_is_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)
    conn.execute("INSERT INTO conversations (title) VALUES ('once')")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0] == 1


def test_init_schema_adds_missing_columns():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        );
        """
    )
    conn.commit()
    init_schema(conn)
    message_cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
    conversation_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(conversations)")
    }
    assert "metadata" in message_cols
    assert "deleted_at" in message_cols
    assert "deleted_at" in conversation_cols
