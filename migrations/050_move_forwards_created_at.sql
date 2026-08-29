-- Move: when each delivered copy was placed.
--
-- Undoing a comment needs its age, and move_forwards recorded where a message
-- went but never when. Existing rows get the current time as a floor, which is
-- wrong in the past-facing direction only: they read as newer than they are, and
-- the sole consumer is a 60-second window that treats anything older as expired.
-- Since every existing row is far older than that either way, nothing changes
-- except that they now have a value at all.

ALTER TABLE move_forwards ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
