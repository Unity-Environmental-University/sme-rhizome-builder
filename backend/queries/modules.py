import json
import sqlite3
from typing import Optional


def list_modules(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM modules WHERE course_id = ? ORDER BY position",
        (course_id,),
    ).fetchall()


def get_module(conn: sqlite3.Connection, module_id: int, course_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM modules WHERE id = ? AND course_id = ?", (module_id, course_id)
    ).fetchone()


def create_module(
    conn: sqlite3.Connection,
    course_id: int,
    title: str,
    description: str = "",
    position: int = 0,
    outcome_ids: list[int] = [],
    canvas_module_id: Optional[str] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO modules (course_id, canvas_module_id, title, description, position, outcome_ids)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (course_id, canvas_module_id, title, description, position, json.dumps(outcome_ids)),
    )
    conn.commit()
    return conn.execute("SELECT * FROM modules WHERE id = ?", (cur.lastrowid,)).fetchone()


def update_module(
    conn: sqlite3.Connection,
    module_id: int,
    course_id: int,
    **fields,
) -> Optional[sqlite3.Row]:
    allowed = {"title", "description", "position", "outcome_ids", "canvas_module_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_module(conn, module_id, course_id)
    if "outcome_ids" in updates:
        updates["outcome_ids"] = json.dumps(updates["outcome_ids"])
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE modules SET {set_clause} WHERE id = ? AND course_id = ?",
        [*updates.values(), module_id, course_id],
    )
    conn.commit()
    return get_module(conn, module_id, course_id)
