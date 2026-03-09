import sqlite3
from typing import Optional


def list_log(
    conn: sqlite3.Connection, context_type: str, context_id: str
) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM log_entries WHERE context_type = ? AND context_id = ? ORDER BY created_at",
        (context_type, context_id),
    ).fetchall()


def append_log(
    conn: sqlite3.Connection,
    user_id: int,
    context_type: str,
    context_id: str,
    action_type: str,
    content: str = "",
    replied_to: Optional[int] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO log_entries (user_id, context_type, context_id, action_type, content, replied_to)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, context_type, context_id, action_type, content, replied_to),
    )
    conn.commit()
    return conn.execute("SELECT * FROM log_entries WHERE id = ?", (cur.lastrowid,)).fetchone()


def get_log_entry(conn: sqlite3.Connection, entry_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM log_entries WHERE id = ?", (entry_id,)).fetchone()
