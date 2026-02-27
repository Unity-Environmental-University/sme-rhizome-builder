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

-- Assignments belong directly to a course + user.
-- No session intermediary.
-- shared: the unit of provenance — this assignment + its log goes to GRAD, otter, etc.
CREATE TABLE IF NOT EXISTS assignments (
    id                   TEXT    PRIMARY KEY,  -- uuid
    user_id              INTEGER NOT NULL REFERENCES users(id),
    course_id            INTEGER NOT NULL REFERENCES courses(id),
    module_label         TEXT    NOT NULL DEFAULT '',
    title                TEXT    NOT NULL DEFAULT 'Untitled',
    description          TEXT    NOT NULL DEFAULT '',
    learning_outcomes    TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    aligned_outcomes     TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    points_possible      INTEGER NOT NULL DEFAULT 100,
    submission_types     TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    rubric               TEXT    NOT NULL DEFAULT '[]',  -- JSON array
    position             INTEGER,                        -- order within module; null = created_at order
    canvas_assignment_id TEXT,
    canvas_html_url      TEXT,
    shared               INTEGER NOT NULL DEFAULT 0,     -- boolean
    created_at           TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Messages attach to any context — an assignment, a course, or a free thread.
-- context_type: 'assignment' | 'course' | 'thread'
-- context_id:   the id of that thing (TEXT to accommodate uuid assignments)
-- role:         'user' | 'assistant'
-- The chat interface is an implementation detail. The log is the record.
CREATE TABLE IF NOT EXISTS messages (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    context_type TEXT    NOT NULL,
    context_id   TEXT    NOT NULL,
    role         TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    position     INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_context
    ON messages (context_type, context_id, position);

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
