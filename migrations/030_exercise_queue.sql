-- Exercise Queue feature (Tier 2 fixed / Tier 3 opportunistic queue / acquisition pins)
-- Single-user behavior in v1 (gated by EXERCISE_BOT_ADMIN_ID), multi-user schema.

CREATE TABLE IF NOT EXISTS exercise_users (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    chat_id BIGINT,
    name TEXT,
    timezone TEXT NOT NULL DEFAULT 'Europe/Berlin',
    overview_time TEXT NOT NULL DEFAULT '19:00',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exercises (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES exercise_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    schedule_type TEXT NOT NULL CHECK (schedule_type IN ('queue', 'fixed', 'acquisition')),
    repeat_interval_days INTEGER,
    estimated_minutes INTEGER,
    dose TEXT,
    focus_area TEXT,
    location TEXT NOT NULL DEFAULT 'anywhere',
    equipment TEXT,
    load_tag TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'parked')),
    last_done_at TIMESTAMPTZ,
    skipped_until TIMESTAMPTZ,
    consecutive_skips INTEGER NOT NULL DEFAULT 0,
    acq_target_sessions INTEGER,
    acq_sessions_done INTEGER NOT NULL DEFAULT 0,
    acq_interval_days INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, name)
);

CREATE INDEX IF NOT EXISTS idx_exercises_serve
    ON exercises (user_id, schedule_type, status, last_done_at);

-- One active served-but-unanswered item per user
CREATE TABLE IF NOT EXISTS exercise_pending_serves (
    user_id INTEGER PRIMARY KEY REFERENCES exercise_users(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    served_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS exercise_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES exercise_users(id) ON DELETE CASCADE,
    exercise_id INTEGER REFERENCES exercises(id) ON DELETE SET NULL,
    done_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dose_actual TEXT,
    source TEXT
);

CREATE INDEX IF NOT EXISTS idx_exercise_history_recent
    ON exercise_history (user_id, done_at DESC);

-- Conversational state for the add / edit flows (separate from burpee state)
CREATE TABLE IF NOT EXISTS exercise_bot_state (
    user_id INTEGER PRIMARY KEY REFERENCES exercise_users(id) ON DELETE CASCADE,
    state TEXT,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
