import sqlite3
from typing import Optional


def get_user(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_canvas_id(conn: sqlite3.Connection, canvas_user_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM users WHERE canvas_user_id = ?", (canvas_user_id,)
    ).fetchone()


def upsert_user(
    conn: sqlite3.Connection,
    canvas_user_id: str,
    name: str,
    email: str,
    canvas_access_token: Optional[str] = None,
    canvas_refresh_token: Optional[str] = None,
    token_expires_at: Optional[str] = None,
    canvas_base_url: str = "https://unity.instructure.com",
) -> sqlite3.Row:
    existing = get_user_by_canvas_id(conn, canvas_user_id)
    if existing:
        conn.execute(
            """UPDATE users SET name=?, email=?, canvas_access_token=?,
               canvas_refresh_token=?, token_expires_at=?, canvas_base_url=?
               WHERE canvas_user_id=?""",
            (name, email, canvas_access_token, canvas_refresh_token,
             token_expires_at, canvas_base_url, canvas_user_id),
        )
        conn.commit()
        return get_user_by_canvas_id(conn, canvas_user_id)
    else:
        conn.execute(
            """INSERT INTO users (canvas_user_id, name, email, canvas_access_token,
               canvas_refresh_token, token_expires_at, canvas_base_url)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (canvas_user_id, name, email, canvas_access_token,
             canvas_refresh_token, token_expires_at, canvas_base_url),
        )
        conn.commit()
        return get_user_by_canvas_id(conn, canvas_user_id)


def create_demo_user(conn: sqlite3.Connection) -> sqlite3.Row:
    existing = get_user_by_canvas_id(conn, "demo")
    if existing:
        return existing
    conn.execute(
        "INSERT INTO users (canvas_user_id, name, email) VALUES ('demo', 'Demo User', 'demo@localhost')"
    )
    conn.commit()
    return get_user_by_canvas_id(conn, "demo")
