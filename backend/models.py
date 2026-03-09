"""
Design notes — SME Rhizome Builder.

The schema is in schema.sql. The queries are in queries.py.
This file is for things the code can't say on its own.

────────────────────────────────────────────────────────────────────────────────

# Orphaned frontend stores

src/stores/session.ts and src/stores/courseContext.ts are from the chatbot branch.
session.ts calls /api/sessions/* endpoints that no longer exist.
Both are only imported by SettingsDrawer.svelte, which needs to be rewritten
against the current data model before either store can be removed.

────────────────────────────────────────────────────────────────────────────────

# Modules

Module titles, descriptions, and outcome connections are hardcoded in
CourseMap.svelte. They belong in the database.

Proposed schema:
    id, course_id, canvas_module_id, title, description,
    position, outcome_ids (JSON array of learning_outcome ids), created_at

Assignments currently use module_label (TEXT) as a grouping key. Once modules
is a table, assignments get a module_id FK. _assignment_dict() in app.py
serializes module_label as "module" — reconcile that when the migration happens.

────────────────────────────────────────────────────────────────────────────────

# Bearing evaluation

The evaluator wakes up when a human writes a new log entry — not on its own
entries, not on a timer. It gets a window of recent log_entries for that context,
evaluates BearingStatements against what it sees, and optionally appends its own
log entry (a likelihood update, a margin observation). Then it sleeps.

The log is the evidence source. The window is enough context even if it misses turns.

Open: rubric validation (wait for GRAD to start reading snapshot content),
version diffing (snapshots cover saves and pushes — is that enough?).
"""
