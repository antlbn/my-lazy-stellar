import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("sessions.db")


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Initialize the SQLite database table for sessions."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                history_json TEXT NOT NULL
            )
            """
        )


def load_session(
    session_id: str, db_path: str | Path = DEFAULT_DB_PATH
) -> list[dict[str, Any]] | None:
    """Load serialized message history from the database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT history_json FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None


def save_session(
    session_id: str,
    history: list[dict[str, Any]],
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Save serialized message history to the database."""
    history_json = json.dumps(history)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, history_json) VALUES (?, ?)",
            (session_id, history_json),
        )
