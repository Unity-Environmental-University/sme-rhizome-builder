import sqlite3
from datetime import datetime
from typing import Optional


def list_bearings(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bearings WHERE course_id = ? ORDER BY created_at",
        (course_id,),
    ).fetchall()


def get_bearing(conn: sqlite3.Connection, bearing_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM bearings WHERE id = ?", (bearing_id,)).fetchone()


def create_bearing(
    conn: sqlite3.Connection,
    course_id: int,
    text: str,
    weight: float = 0.5,
    likelihood: float = 0.5,
    learning_outcome_id: Optional[int] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO bearings (course_id, learning_outcome_id, text, weight, likelihood)
           VALUES (?, ?, ?, ?, ?)""",
        (course_id, learning_outcome_id, text, weight, likelihood),
    )
    conn.commit()
    return conn.execute("SELECT * FROM bearings WHERE id = ?", (cur.lastrowid,)).fetchone()


def update_bearing(
    conn: sqlite3.Connection, bearing_id: int, **fields
) -> Optional[sqlite3.Row]:
    allowed = {"text", "weight", "likelihood"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_bearing(conn, bearing_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    updates["updated_at"] = datetime.utcnow().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE bearings SET {set_clause} WHERE id = ?",
        [*updates.values(), bearing_id],
    )
    conn.commit()
    return get_bearing(conn, bearing_id)


def delete_bearing(conn: sqlite3.Connection, bearing_id: int):
    conn.execute("DELETE FROM bearing_statements WHERE bearing_id = ?", (bearing_id,))
    conn.execute("DELETE FROM bearings WHERE id = ?", (bearing_id,))
    conn.commit()


def list_statements(conn: sqlite3.Connection, bearing_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bearing_statements WHERE bearing_id = ? ORDER BY created_at",
        (bearing_id,),
    ).fetchall()


def get_statement(conn: sqlite3.Connection, statement_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM bearing_statements WHERE id = ?", (statement_id,)
    ).fetchone()


def create_statement(
    conn: sqlite3.Connection, bearing_id: int, text: str, observed=None
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO bearing_statements (bearing_id, text, observed) VALUES (?, ?, ?)",
        (bearing_id, text, observed),
    )
    conn.commit()
    return conn.execute("SELECT * FROM bearing_statements WHERE id = ?", (cur.lastrowid,)).fetchone()


def update_statement(
    conn: sqlite3.Connection, statement_id: int, **fields
) -> Optional[sqlite3.Row]:
    allowed = {"text", "observed"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_statement(conn, statement_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE bearing_statements SET {set_clause} WHERE id = ?",
        [*updates.values(), statement_id],
    )
    conn.commit()
    return get_statement(conn, statement_id)
