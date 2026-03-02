"""
All SQL queries for SME Rhizome Builder.

One function per operation. Parameters always parameterized — no string interpolation.
Returns sqlite3.Row objects (dict-like). Callers convert to response dicts.

The garden wall: SQL lives here. Business logic lives in app.py.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional


# ── Users ─────────────────────────────────────────────────────────────────────

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


# ── Courses ───────────────────────────────────────────────────────────────────

def get_course(conn: sqlite3.Connection, course_id: int, user_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM courses WHERE id = ? AND user_id = ?", (course_id, user_id)
    ).fetchone()


def list_courses(conn: sqlite3.Connection, user_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM courses WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()


def create_course(
    conn: sqlite3.Connection,
    user_id: int,
    course_code: str = "",
    course_title: str = "",
    learning_outcomes: str = "",
    canvas_course_id: Optional[str] = None,
    period_type: str = "Week",
) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO courses (user_id, course_code, course_title, learning_outcomes,
           canvas_course_id, period_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, course_code, course_title, learning_outcomes, canvas_course_id, period_type),
    )
    conn.commit()
    return conn.execute("SELECT * FROM courses WHERE id = ?", (cur.lastrowid,)).fetchone()


def update_course(
    conn: sqlite3.Connection,
    course_id: int,
    course_code: str,
    course_title: str,
    learning_outcomes: str,
    canvas_course_id: Optional[str],
) -> sqlite3.Row:
    conn.execute(
        """UPDATE courses SET course_code=?, course_title=?, learning_outcomes=?,
           canvas_course_id=? WHERE id=?""",
        (course_code, course_title, learning_outcomes, canvas_course_id, course_id),
    )
    conn.commit()
    return conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()


# ── Learning outcomes ─────────────────────────────────────────────────────────

def list_learning_outcomes(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM learning_outcomes WHERE course_id = ? ORDER BY position",
        (course_id,),
    ).fetchall()


def get_learning_outcomes_by_ids(
    conn: sqlite3.Connection, ids: list[int], course_id: int
) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    return conn.execute(
        f"SELECT * FROM learning_outcomes WHERE id IN ({placeholders}) AND course_id = ?",
        (*ids, course_id),
    ).fetchall()


def create_learning_outcome(
    conn: sqlite3.Connection, course_id: int, text: str, position: int,
    canvas_outcome_id: Optional[str] = None,
) -> sqlite3.Row:
    cur = conn.execute(
        "INSERT INTO learning_outcomes (course_id, text, position, canvas_outcome_id) VALUES (?, ?, ?, ?)",
        (course_id, text, position, canvas_outcome_id),
    )
    conn.commit()
    return conn.execute("SELECT * FROM learning_outcomes WHERE id = ?", (cur.lastrowid,)).fetchone()


# ── Assignments ───────────────────────────────────────────────────────────────

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
    description: str = "",
    learning_outcomes: list = None,
    aligned_outcomes: list = None,
    points_possible: int = 100,
    submission_types: list = None,
    rubric: list = None,
    position: Optional[int] = None,
) -> sqlite3.Row:
    assignment_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO assignments (id, user_id, course_id, module_label, title, description,
           learning_outcomes, aligned_outcomes, points_possible, submission_types, rubric, position)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            assignment_id, user_id, course_id, module_label, title, description,
            json.dumps(learning_outcomes or []),
            json.dumps(aligned_outcomes or []),
            points_possible,
            json.dumps(submission_types or []),
            json.dumps(rubric or []),
            position,
        ),
    )
    conn.commit()
    return get_assignment(conn, assignment_id, user_id)


def update_assignment(
    conn: sqlite3.Connection,
    assignment_id: str,
    user_id: int,
    **fields,
) -> Optional[sqlite3.Row]:
    """Update arbitrary fields on an assignment. Only touches what's passed."""
    allowed = {"title", "description", "position", "canvas_assignment_id",
               "canvas_html_url", "shared", "module_label",
               "learning_outcomes", "aligned_outcomes", "rubric",
               "points_possible", "submission_types"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_assignment(conn, assignment_id, user_id)

    # JSON-encode list fields
    for list_field in ("learning_outcomes", "aligned_outcomes", "rubric", "submission_types"):
        if list_field in updates and isinstance(updates[list_field], list):
            updates[list_field] = json.dumps(updates[list_field])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [assignment_id, user_id]
    conn.execute(
        f"UPDATE assignments SET {set_clause} WHERE id = ? AND user_id = ?",
        values,
    )
    conn.commit()
    return get_assignment(conn, assignment_id, user_id)


# ── Log entries ───────────────────────────────────────────────────────────────

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


# ── Bearings ──────────────────────────────────────────────────────────────────

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


# ── BearingStatements ─────────────────────────────────────────────────────────

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
