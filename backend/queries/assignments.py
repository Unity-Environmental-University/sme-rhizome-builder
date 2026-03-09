import json
import sqlite3
import uuid
from typing import Optional


# ── Assignments ────────────────────────────────────────────────────────────────
# Assignments are identity records. The live document is in log_entries (action_type='edit').
# title and module_label are here for list views without reducing the log.

def get_assignment(
    conn: sqlite3.Connection, assignment_id: str, user_id: int
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM assignments WHERE id = ? AND user_id = ?", (assignment_id, user_id)
    ).fetchone()


def list_assignments(conn: sqlite3.Connection, course_id: int, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM assignments
           WHERE course_id = ? AND user_id = ?
           ORDER BY CASE WHEN position IS NULL THEN 1 ELSE 0 END, position, created_at""",
        (course_id, user_id),
    ).fetchall()


def next_position_in_module(
    conn: sqlite3.Connection, course_id: int, user_id: int, module_label: str
) -> int:
    row = conn.execute(
        """SELECT MAX(position) as max_pos FROM assignments
           WHERE course_id = ? AND user_id = ? AND module_label = ? AND position IS NOT NULL""",
        (course_id, user_id, module_label),
    ).fetchone()
    max_pos = row["max_pos"]
    return (max_pos + 1) if max_pos is not None else 0


def create_assignment(
    conn: sqlite3.Connection,
    user_id: int,
    course_id: int,
    module_label: str,
    title: str,
    position: Optional[int] = None,
) -> sqlite3.Row:
    assignment_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO assignments (id, user_id, course_id, module_label, title, position) VALUES (?, ?, ?, ?, ?, ?)",
        (assignment_id, user_id, course_id, module_label, title, position),
    )
    conn.commit()
    return get_assignment(conn, assignment_id, user_id)


def update_assignment(
    conn: sqlite3.Connection,
    assignment_id: str,
    user_id: int,
    **fields,
) -> Optional[sqlite3.Row]:
    allowed = {"title", "module_label", "position"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_assignment(conn, assignment_id, user_id)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn.execute(
        f"UPDATE assignments SET {set_clause} WHERE id = ? AND user_id = ?",
        [*updates.values(), assignment_id, user_id],
    )
    conn.commit()
    return get_assignment(conn, assignment_id, user_id)


# ── Snapshots ──────────────────────────────────────────────────────────────────
# Frozen moments. What got pushed to Canvas, or an explicit save point.
# content is a JSON blob — see schema.sql for the documented shape.

def create_snapshot(
    conn: sqlite3.Connection,
    assignment_id: str,
    user_id: int,
    content: dict,
    label: Optional[str] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO snapshots (assignment_id, user_id, content, label) VALUES (?, ?, ?, ?)",
        (assignment_id, user_id, json.dumps(content), label),
    )
    conn.commit()
    return conn.execute("SELECT * FROM snapshots WHERE id = ?", (cur.lastrowid,)).fetchone()


def list_snapshots(conn: sqlite3.Connection, assignment_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM snapshots WHERE assignment_id = ? ORDER BY snapshot_at",
        (assignment_id,),
    ).fetchall()


def latest_snapshot(conn: sqlite3.Connection, assignment_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM snapshots WHERE assignment_id = ? ORDER BY snapshot_at DESC LIMIT 1",
        (assignment_id,),
    ).fetchone()
