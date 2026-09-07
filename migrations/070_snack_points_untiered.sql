-- Three snacks that scored 1 when they were worth more.
--
-- Migration 069 backfilled points from each item's tier and fell back to 1
-- where the tier was NULL. Three rows took that fallback — two of "Shoulder"
-- (now tier 1, so worth 12) and one of "Lock" (now tier 3, worth 4) — because
-- those items had no tier at the moment 069 ran, and were rated afterwards.
--
-- Fixed by id rather than by rule. A blanket "any 1-point row whose item is now
-- tiered higher" would also rewrite rows that were honestly worth 1 when they
-- were ticked and whose exercise has since been promoted, which is the exact
-- thing the frozen column exists to prevent. These three are checked: each was
-- ticked before 069 ran, so its 1 is the fallback rather than a judgement.
--
-- From here the freeze holds: exercise_bot writes the weight at tick time.

UPDATE exercise_history h
SET points = COALESCE(
        CASE i.tier WHEN 1 THEN 12 WHEN 2 THEN 8 WHEN 3 THEN 4
                    WHEN 4 THEN 2 WHEN 5 THEN 1 END, 1)
FROM exercise_items i
WHERE i.id = h.exercise_id
  AND h.id IN (42, 72, 80)
  AND h.points = 1;
