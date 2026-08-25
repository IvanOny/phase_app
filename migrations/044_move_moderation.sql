-- Move: warnings, suspension and bans.
--
-- Reports (043) are raw signal. This is what the bot does with them:
--   2 distinct reporters on one entry  -> a warning to its author
--   3 active warnings                  -> radar sharing suspended, pending review
--
-- Everything here is reversible by a moderator, deliberately. Reports are
-- unverified, so a handful of coordinated accounts must not be able to silence
-- someone permanently without a human ever looking.
--
-- Warnings expire (90 days, enforced in code): a warning from last year and
-- nothing since shouldn't leave someone one strike from suspension.

CREATE TABLE IF NOT EXISTS move_warnings (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,        -- who was warned
    entry_id INTEGER REFERENCES move_entries(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cleared_at TIMESTAMPTZ,                  -- a moderator decided it was unfair
    cleared_by BIGINT,
    UNIQUE (telegram_user_id, entry_id)      -- one warning per move, however many reports
);

CREATE INDEX IF NOT EXISTS idx_move_warnings_user
    ON move_warnings (telegram_user_id, created_at DESC);

-- Suspension is a pause, not a verdict: lifted_at is how a moderator undoes it.
CREATE TABLE IF NOT EXISTS move_suspensions (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    suspended_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    lifted_at TIMESTAMPTZ,
    lifted_by BIGINT
);

CREATE INDEX IF NOT EXISTS idx_move_suspensions_user
    ON move_suspensions (telegram_user_id, suspended_at DESC);

-- A ban is the moderator's own decision, never automatic. It stops radar in
-- both directions and can't be undone by the user flipping the share toggle.
-- Crew is untouched: those relationships were consented to on both sides.
ALTER TABLE move_users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMPTZ;
