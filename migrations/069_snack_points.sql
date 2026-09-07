-- What a snack was worth when it was done.
--
-- Snacks are about to have a score, and the score is tier-weighted: a tier-1
-- item counts 12, a tier-5 counts 1. Tier lives on exercise_items and can be
-- changed at any time with `tier <name> <n>`, so computing the score by joining
-- to it would mean every past day silently re-scoring itself the moment an
-- item is re-rated. A September total should not move because of a decision
-- made in October.
--
-- So the weight is written into the history row when the row is written. The
-- backfill below is the one place the join is the right answer: for rows that
-- pre-date this column there is no record of what the tier was then, and the
-- current tier is the only evidence available.
--
-- Items deleted since leave history rows with no tier to look up. Those get 1,
-- the smallest weight, rather than 0 — the snack was done, and a row worth
-- nothing would read as if it hadn't been.

ALTER TABLE exercise_history
    ADD COLUMN IF NOT EXISTS points SMALLINT;

UPDATE exercise_history h
SET points = COALESCE(
        CASE i.tier WHEN 1 THEN 12 WHEN 2 THEN 8 WHEN 3 THEN 4
                    WHEN 4 THEN 2 WHEN 5 THEN 1 END, 1)
FROM exercise_items i
WHERE i.id = h.exercise_id AND h.points IS NULL;

UPDATE exercise_history SET points = 1 WHERE points IS NULL;

ALTER TABLE exercise_history ALTER COLUMN points SET NOT NULL;
ALTER TABLE exercise_history ALTER COLUMN points SET DEFAULT 1;

CREATE INDEX IF NOT EXISTS exercise_history_user_day
    ON exercise_history (user_id, done_at);

COMMENT ON COLUMN exercise_history.points IS
    'Tier weight at the moment the snack was done. Frozen: re-tiering an item does not rescore the past.';
