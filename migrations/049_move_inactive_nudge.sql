-- Move: when someone was last nudged for going quiet.
--
-- Separate from nudged_at, which marks the one-and-only "you registered and
-- never posted" message. This one repeats on a schedule, so the two can't share
-- a column without the first nudge silently starting the second clock.

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS inactive_nudged_at DATE;
