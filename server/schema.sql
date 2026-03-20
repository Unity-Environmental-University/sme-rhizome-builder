-- SME Rhizome Builder — PostgreSQL schema
-- Authoritative for the Hono backend (server/).
-- SQLite schema lives at backend/schema.sql (Flask, deprecated).
--
-- Session is not a table. Reconstructible from timestamps when needed.

CREATE TABLE IF NOT EXISTS users (
    id                   SERIAL PRIMARY KEY,
    canvas_user_id       TEXT        UNIQUE NOT NULL,
    name                 TEXT        NOT NULL DEFAULT '',
    email                TEXT        NOT NULL DEFAULT '',
    canvas_access_token  TEXT,
    canvas_refresh_token TEXT,
    token_expires_at     TIMESTAMPTZ,
    canvas_base_url      TEXT        NOT NULL DEFAULT 'https://unity.instructure.com',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS courses (
    id                INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id           INTEGER     NOT NULL REFERENCES users(id),
    canvas_course_id  TEXT,
    course_code       TEXT        NOT NULL DEFAULT '',
    course_title      TEXT        NOT NULL DEFAULT '',
    learning_outcomes TEXT        NOT NULL DEFAULT '',
    period_type       TEXT        NOT NULL DEFAULT 'Week',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS learning_outcomes (
    id                INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    course_id         INTEGER     NOT NULL REFERENCES courses(id),
    text              TEXT        NOT NULL,
    canvas_outcome_id TEXT,
    position          INTEGER     NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS modules (
    id               INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    course_id        INTEGER     NOT NULL REFERENCES courses(id),
    canvas_module_id TEXT,
    title            TEXT        NOT NULL DEFAULT '',
    description      TEXT        NOT NULL DEFAULT '',
    position         INTEGER     NOT NULL DEFAULT 0,
    outcome_ids      JSONB       NOT NULL DEFAULT '[]',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS assignments (
    id           TEXT        PRIMARY KEY,  -- uuid, generated in app
    user_id      INTEGER     NOT NULL REFERENCES users(id),
    course_id    INTEGER     NOT NULL REFERENCES courses(id),
    module_label TEXT        NOT NULL DEFAULT '',
    title        TEXT        NOT NULL DEFAULT 'Untitled',
    position     INTEGER,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Snapshots are frozen moments — explicit save points or Canvas pushes.
-- content: JSONB. Shape documented in SQLite schema.
CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    assignment_id TEXT        NOT NULL REFERENCES assignments(id),
    user_id       INTEGER     NOT NULL REFERENCES users(id),
    content       JSONB       NOT NULL,
    label         TEXT,
    snapshot_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The log. Every action is an entry. context_type is open-ended.
CREATE TABLE IF NOT EXISTS log_entries (
    id           INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id      INTEGER     NOT NULL REFERENCES users(id),
    context_type TEXT        NOT NULL,
    context_id   TEXT        NOT NULL,
    action_type  TEXT        NOT NULL,
    content      TEXT        NOT NULL DEFAULT '',
    replied_to   INTEGER     REFERENCES log_entries(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_log_context
    ON log_entries (context_type, context_id, created_at);

-- Bearings: the learning designer's compass. Stars, not destinations.
-- weight: -1 to 1 (sail toward / sail away from)
-- likelihood: 0 to 1 (current read on whether we're there)
CREATE TABLE IF NOT EXISTS bearings (
    id                  INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    course_id           INTEGER     REFERENCES courses(id),
    learning_outcome_id INTEGER     REFERENCES learning_outcomes(id),
    text                TEXT        NOT NULL,
    weight              REAL        NOT NULL DEFAULT 0.5,
    likelihood          REAL        NOT NULL DEFAULT 0.5,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- BearingStatements: observable evidence layer.
-- observed: true = confirmed, false = disconfirmed, null = not yet evaluated
CREATE TABLE IF NOT EXISTS bearing_statements (
    id         INTEGER     PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    bearing_id INTEGER     NOT NULL REFERENCES bearings(id),
    text       TEXT        NOT NULL,
    observed   BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
