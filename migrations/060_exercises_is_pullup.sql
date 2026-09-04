-- Mark pull-up variants, so the lift trend can plot them.
--
-- The other lifts each have a flag (is_squat, is_deadlift,
-- is_barbell_bench_press) and pull-ups had none, because until now nothing
-- needed to find them as a group. Matching on the name is not an option: this
-- database already holds "Pull-up", "Chin-up", "Weighted Pull-up" and
-- "Weighted Pull-ups" as four separate exercises, and the next variant typed
-- into the app would be a fifth.
--
-- Chin-up counts. It is the same movement with the hands turned round, it is
-- logged in the same sessions, and separating it would leave a one-set series.

ALTER TABLE exercises
  ADD COLUMN IF NOT EXISTS is_pullup SMALLINT NOT NULL DEFAULT 0;

UPDATE exercises SET is_pullup = 1
WHERE exercise_name ILIKE '%pull-up%'
   OR exercise_name ILIKE '%pullup%'
   OR exercise_name ILIKE '%chin-up%'
   OR exercise_name ILIKE '%chinup%';

-- Not lat pulldowns, face pulls, or anything else with "pull" in the name:
-- the trend is about hanging from a bar and moving your own weight.
UPDATE exercises SET is_pullup = 0
WHERE exercise_name ILIKE '%pulldown%' OR exercise_name ILIKE '%face pull%';
