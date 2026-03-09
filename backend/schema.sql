-- SME Rhizome Builder — authoritative schema
--
-- Session is not a table. A session is reconstructible from
-- (user_id, context_type, context_id, created_at) when you need it.
-- The artifact and its log are the primary records.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY,
    canvas_user_id       TEXT    UNIQUE NOT NULL,
    name                 TEXT    NOT NULL DEFAULT '',
    email                TEXT    NOT NULL DEFAULT '',
    canvas_access_token  TEXT,
    canvas_refresh_token TEXT,
    token_expires_at     TEXT,
    canvas_base_url      TEXT    NOT NULL DEFAULT 'https://unity.instructure.com',
    created_at           TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS courses (
    id               INTEGER PRIMARY KEY,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    canvas_course_id TEXT,
    course_code      TEXT    NOT NULL DEFAULT '',
    course_title     TEXT    NOT NULL DEFAULT '',
    learning_outcomes TEXT   NOT NULL DEFAULT '',  -- text blob, fallback for prompt
    period_type      TEXT    NOT NULL DEFAULT 'Week',
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS learning_outcomes (
    id               INTEGER PRIMARY KEY,
    course_id        INTEGER NOT NULL REFERENCES courses(id),
    text             TEXT    NOT NULL,
    canvas_outcome_id TEXT,
    position         INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Modules: the weeks (or units) that structure a course.
-- outcome_ids: JSON array of learning_outcome.id values — the outcomes this module addresses.
-- canvas_module_id: optional link to a Canvas module, for future sync.
-- position: display order within the course.
CREATE TABLE IF NOT EXISTS modules (
    id               INTEGER PRIMARY KEY,
    course_id        INTEGER NOT NULL REFERENCES courses(id),
    canvas_module_id TEXT,
    title            TEXT    NOT NULL DEFAULT '',
    description      TEXT    NOT NULL DEFAULT '',
    position         INTEGER NOT NULL DEFAULT 0,
    outcome_ids      TEXT    NOT NULL DEFAULT '[]',  -- JSON array of learning_outcome ids
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Assignments are identity records — the thing that exists in a course.
-- The live document lives in log_entries (action_type: 'edit').
-- title and module_label are here for list views without reducing the log.
-- position: order within module; null = created_at order
CREATE TABLE IF NOT EXISTS assignments (
    id           TEXT    PRIMARY KEY,  -- uuid
    user_id      INTEGER NOT NULL REFERENCES users(id),
    course_id    INTEGER NOT NULL REFERENCES courses(id),
    module_label TEXT    NOT NULL DEFAULT '',
    title        TEXT    NOT NULL DEFAULT 'Untitled',
    position     INTEGER,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Snapshots are frozen moments — what got pushed to Canvas, or an explicit save point.
-- content: JSON blob. Root fields are portable. canvas{} namespace is Canvas-specific.
-- format_version: migration handle for the melty future.
--
-- content shape:
-- {
--   "format_version": "1",
--   "title": "...",
--   "description": "...",          -- HTML, student-facing
--   "points_possible": 100,
--   "submission_types": [...],
--   "rubric": [...],
--   "aligned_outcomes": [
--     { "id": "...", "text": "...", "source": "canvas_outcome" }
--   ],
--   "canvas": {
--     "assignment_id": "...",
--     "html_url": "...",
--     "course_id": "..."
--   }
-- }
CREATE TABLE IF NOT EXISTS snapshots (
    id           INTEGER PRIMARY KEY,
    assignment_id TEXT   NOT NULL REFERENCES assignments(id),
    user_id      INTEGER NOT NULL REFERENCES users(id),
    content      TEXT    NOT NULL,  -- JSON blob
    label        TEXT,              -- 'canvas_push' | 'manual' | null
    snapshot_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- The log. Every action is an entry.
-- context_type: 'assignment' | 'course' | 'thread' — open-ended, not an enum
-- context_id:   id of that thing (TEXT to accommodate uuid assignments)
-- action_type:  'ai_turn' | 'comment' | 'edit' | 'save' | 'created' | ...
--               action_type tells you how to read content. Don't over-specify.
-- content:      text — JSON-as-text when the action warrants it
-- replied_to:   self-referential — threads are linked lists, not containers
CREATE TABLE IF NOT EXISTS log_entries (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    context_type TEXT    NOT NULL,
    context_id   TEXT    NOT NULL,
    action_type  TEXT    NOT NULL,
    content      TEXT    NOT NULL DEFAULT '',
    replied_to   INTEGER REFERENCES log_entries(id),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_log_context
    ON log_entries (context_type, context_id, created_at);

-- Bearings: the learning designer's compass.
-- Stars, not destinations. course-level or outcome-level.
-- weight:     -1 to 1 (sail toward / sail away from)
-- likelihood: 0 to 1 (current read on whether we're there)
CREATE TABLE IF NOT EXISTS bearings (
    id                  INTEGER PRIMARY KEY,
    course_id           INTEGER REFERENCES courses(id),
    learning_outcome_id INTEGER REFERENCES learning_outcomes(id),
    text                TEXT    NOT NULL,
    weight              REAL    NOT NULL DEFAULT 0.5,
    likelihood          REAL    NOT NULL DEFAULT 0.5,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- BearingStatements: observable evidence layer.
-- observed: 1 = confirmed, 0 = disconfirmed, NULL = not yet evaluated
CREATE TABLE IF NOT EXISTS bearing_statements (
    id         INTEGER PRIMARY KEY,
    bearing_id INTEGER NOT NULL REFERENCES bearings(id),
    text       TEXT    NOT NULL,
    observed   INTEGER,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
