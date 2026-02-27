"""
Seed script — creates demo user and MARI 515 with learning outcomes.

Run from the backend/ directory:
    python seed.py
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))

from db import DB_PATH, SCHEMA_PATH

OUTCOMES = [
    (0, "Identify the physiological mechanisms underlying coral bleaching and evaluate "
        "the relative contribution of thermal stress, ocean acidification, and local stressors."),
    (1, "Analyze a reef system using field or remotely-sensed data and characterize its "
        "current health state, trajectory, and dominant stressors."),
    (2, "Evaluate restoration intervention strategies — including coral gardening, assisted "
        "gene flow, and substrate stabilization — against the ecological and logistical "
        "constraints of a specific site."),
    (3, "Articulate a monitoring protocol that could detect early warning signals of "
        "degradation before bleaching thresholds are reached."),
    (4, "Situate a conservation decision within the social and political context of the reef "
        "— including Indigenous stewardship, tourism economies, and fisheries — and defend "
        "the tradeoffs made."),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # Demo user
    user = conn.execute("SELECT * FROM users WHERE canvas_user_id = 'demo'").fetchone()
    if user is None:
        conn.execute(
            "INSERT INTO users (canvas_user_id, name, email) VALUES ('demo', 'Demo User', 'demo@localhost')"
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE canvas_user_id = 'demo'").fetchone()
        print("Created demo user.")
    else:
        print("Demo user already exists.")

    # MARI 515
    course = conn.execute(
        "SELECT * FROM courses WHERE course_code = 'MARI 515' AND user_id = ?", (user["id"],)
    ).fetchone()

    if course is None:
        conn.execute(
            """INSERT INTO courses (user_id, course_code, course_title, learning_outcomes)
               VALUES (?, 'MARI 515', 'Coral Ecology and Conservation', ?)""",
            (user["id"], "\n".join(text for _, text in OUTCOMES)),
        )
        conn.commit()
        course = conn.execute(
            "SELECT * FROM courses WHERE course_code = 'MARI 515' AND user_id = ?", (user["id"],)
        ).fetchone()
        print("Created MARI 515.")
    else:
        print("MARI 515 already exists.")

    # Learning outcome rows
    existing = conn.execute(
        "SELECT COUNT(*) as n FROM learning_outcomes WHERE course_id = ?", (course["id"],)
    ).fetchone()["n"]

    if existing == 0:
        for position, text in OUTCOMES:
            conn.execute(
                "INSERT INTO learning_outcomes (course_id, text, position) VALUES (?, ?, ?)",
                (course["id"], text, position),
            )
        conn.commit()
        print(f"Seeded {len(OUTCOMES)} learning outcomes.")
    else:
        print(f"Learning outcomes already seeded ({existing} rows).")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
