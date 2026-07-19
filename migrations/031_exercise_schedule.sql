-- Exercise Queue: web UI scheduling layer.
--
-- The bot decides due-ness from cadence (last_done_at + interval). The web
-- calendar adds an explicit occurrence layer so a user can DRAG an exercise onto
-- a specific day. A manual occurrence is a commitment that overrides the cadence
-- suggestion for that day — "drag beats every-N-days".

-- Per-user token so the web UI can authenticate the same way the burpee app does
-- (a ?token= link issued by the bot via /exapp).
ALTER TABLE exercise_users ADD COLUMN IF NOT EXISTS token TEXT UNIQUE;

CREATE TABLE IF NOT EXISTS exercise_schedule (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES exercise_users(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercise_items(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    -- 'manual' = user placed it (authoritative). 'auto' is reserved for
    -- materialized cadence suggestions; v1 projects those on the fly instead.
    origin TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual', 'auto')),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'done', 'skipped')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- One placement per exercise per day.
    UNIQUE (exercise_id, scheduled_date)
);

CREATE INDEX IF NOT EXISTS idx_exercise_schedule_range
    ON exercise_schedule (user_id, scheduled_date);
