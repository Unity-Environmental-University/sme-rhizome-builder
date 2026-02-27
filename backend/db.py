"""
Database connection — raw sqlite3, no ORM.

get_db()  → sqlite3.Connection, scoped to the Flask request via g.
Schema initialised once at app startup via init_db().

All queries live in queries.py. This file is only plumbing.
"""

import os
import sqlite3

from flask import g

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "rhizome.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        g.db = conn
    return g.db


def close_db(e=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(app):
    """Create tables from schema.sql if they don't exist. Called once at startup."""
    with app.app_context():
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA foreign_keys=ON")
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()

    app.teardown_appcontext(close_db)
