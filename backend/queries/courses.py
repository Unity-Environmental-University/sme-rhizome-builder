import sqlite3
from typing import Optional


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
