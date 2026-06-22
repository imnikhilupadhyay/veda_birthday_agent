import sqlite3
from pathlib import Path

DB_PATH = Path("chat_history.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                thread_id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


def get_history(thread_id: str, limit: int = 4):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM chat_history
            WHERE thread_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (thread_id, limit),
        ).fetchall()

    rows.reverse()
    return [{"role": role, "content": content} for role, content in rows]


def save_message(thread_id: str, role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO chat_history(thread_id, role, content)
            VALUES (?, ?, ?)
            """,
            (thread_id, role, content),
        )

        conn.execute(
            """
            DELETE FROM chat_history
            WHERE thread_id = ?
            AND id NOT IN (
                SELECT id
                FROM chat_history
                WHERE thread_id = ?
                ORDER BY id DESC
                LIMIT 4
            )
            """,
            (thread_id, thread_id),
        )

        conn.commit()


def get_user_profile(thread_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT name
            FROM user_profile
            WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()

    if not row or not row[0]:
        return {}

    return {"name": row[0]}


def upsert_user_name(thread_id: str, name: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO user_profile(thread_id, name, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(thread_id)
            DO UPDATE SET
                name = excluded.name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (thread_id, name),
        )

        conn.commit()