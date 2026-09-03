"""SQLite schema bootstrap and light migrations."""

from sqlite3 import Connection


def init_schema(conn: Connection) -> None:
    """Create tables if missing, then add columns older databases may lack."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            deleted_at DATETIME,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
        """
    )

    message_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()
    }
    if "metadata" not in message_columns:
        conn.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")
    if "deleted_at" not in message_columns:
        conn.execute("ALTER TABLE messages ADD COLUMN deleted_at DATETIME")

    conversation_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
    }
    if "deleted_at" not in conversation_columns:
        conn.execute("ALTER TABLE conversations ADD COLUMN deleted_at DATETIME")

    conn.commit()
