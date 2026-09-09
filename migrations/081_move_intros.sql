-- Introductions: one person in your crew suggesting two others to each other.
--
-- Radar finds strangers by algorithm. This finds them by someone who actually
-- knows both people — which is better information than any cooldown table has.
--
-- One row per suggestion, and the unique index makes it one per pair for good:
-- a suggestion that can be repeated is a nagging channel between friends, which
-- is worse than one from a stranger.
CREATE TABLE IF NOT EXISTS move_intros (
    id            SERIAL PRIMARY KEY,
    suggested_by  BIGINT      NOT NULL,
    a_id          BIGINT      NOT NULL,     -- gets the nudge, sends the request
    b_id          BIGINT      NOT NULL,     -- gets the request, decides
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at       TIMESTAMPTZ,              -- a_id passed it on
    declined_at   TIMESTAMPTZ               -- a_id didn't
);

-- LEAST/GREATEST so the pair is the same pair whichever way round it was made,
-- and whoever made it. Two people are introduced once.
CREATE UNIQUE INDEX IF NOT EXISTS move_intros_pair
    ON move_intros (LEAST(a_id, b_id), GREATEST(a_id, b_id));

-- Opt-out, not opt-in — unlike radar. Radar hands your existence to strangers;
-- this hands it to someone who is already in your crew and chose you, mutually.
-- That is a much smaller step, so the default is on and the switch is for people
-- who want it off rather than a gate everyone must pass first.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS intros_ok BOOLEAN NOT NULL DEFAULT TRUE;

-- Fired once, the first moment there is a pair worth suggesting. The feature
-- lives inside the crew menu, which nobody opens looking for a thing they have
-- never heard of; without this it would be discovered by accident or not at all.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS intro_hinted_at TIMESTAMPTZ;
