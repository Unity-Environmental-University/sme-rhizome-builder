"""
All SQL queries for SME Rhizome Builder.

One function per operation. Parameters always parameterized — no string interpolation.
Returns sqlite3.Row objects (dict-like). Callers convert to response dicts.

The garden wall: SQL lives here. Business logic lives in app.py (and blueprints).
"""

from queries.users import (
    get_user,
    get_user_by_canvas_id,
    upsert_user,
    create_demo_user,
)

from queries.courses import (
    get_course,
    list_courses,
    create_course,
    update_course,
    list_learning_outcomes,
    get_learning_outcomes_by_ids,
    create_learning_outcome,
)

from queries.assignments import (
    get_assignment,
    list_assignments,
    next_position_in_module,
    create_assignment,
    update_assignment,
    create_snapshot,
    list_snapshots,
    latest_snapshot,
)

from queries.log import (
    list_log,
    append_log,
    get_log_entry,
)

from queries.modules import (
    list_modules,
    get_module,
    create_module,
    update_module,
)

from queries.bearings import (
    list_bearings,
    get_bearing,
    create_bearing,
    update_bearing,
    delete_bearing,
    list_statements,
    get_statement,
    create_statement,
    update_statement,
)
