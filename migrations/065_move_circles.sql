-- Circles: named subsets of your crew, and a move that waits to be addressed.
--
-- Until now a move went to everyone in your crew the moment you sent it. With
-- circles you pick who gets each one — one circle, several, and radar
-- alongside them — and the move is held until you have.
--
-- Membership is stored by telegram id, not by name. move_crew keys on
-- participant_name because that is how someone is added, but /rename exists and
-- a circle whose members silently emptied on a rename would be worse than no
-- circle at all.
--
-- pending_since on move_entries is the held state: set when a move is recorded
-- by someone who has circles, cleared when it is delivered. A move with it set
-- exists, counts for the streak, and has reached nobody yet.

CREATE TABLE IF NOT EXISTS move_circles (
    id          BIGSERIAL PRIMARY KEY,
    owner_tg_id BIGINT NOT NULL,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One circle per name per person, case-insensitively: "Зал" and "зал" are the
-- same circle to everyone except a database.
CREATE UNIQUE INDEX IF NOT EXISTS move_circles_owner_name
    ON move_circles (owner_tg_id, LOWER(name));
CREATE INDEX IF NOT EXISTS move_circles_owner ON move_circles (owner_tg_id);

CREATE TABLE IF NOT EXISTS move_circle_members (
    circle_id     BIGINT NOT NULL REFERENCES move_circles(id) ON DELETE CASCADE,
    member_tg_id  BIGINT NOT NULL,
    PRIMARY KEY (circle_id, member_tg_id)
);

-- Which circles a move was addressed to. Kept after delivery: it is the record
-- of who was meant to see it, which move_forwards only shows indirectly and
-- only until the rows are cleaned up.
CREATE TABLE IF NOT EXISTS move_entry_circles (
    entry_id   BIGINT NOT NULL REFERENCES move_entries(id) ON DELETE CASCADE,
    circle_id  BIGINT NOT NULL REFERENCES move_circles(id) ON DELETE CASCADE,
    PRIMARY KEY (entry_id, circle_id)
);

ALTER TABLE move_entries
    ADD COLUMN IF NOT EXISTS pending_since TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS move_entries_pending
    ON move_entries (pending_since) WHERE pending_since IS NOT NULL;

COMMENT ON COLUMN move_entries.pending_since IS
    'Set while a move waits to be addressed; NULL once it has been delivered.';
