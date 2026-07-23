-- Give Run a catalog identity so it can be a tier-1 exercise and appear in
-- filter dropdowns. Run metrics (distance, duration, HR, pace) stay on the
-- sessions row; this exercise is just the catalog handle.
-- Run in Supabase SQL editor.
ALTER TABLE exercises
  ADD COLUMN IF NOT EXISTS is_run BOOLEAN NOT NULL DEFAULT false;

-- Note: is_barbell_bench_press / is_bodyweight / is_squat / is_deadlift are
-- INTEGER columns (0/1), not boolean; only is_run (added above) is boolean.
INSERT INTO exercises (exercise_name, is_barbell_bench_press, is_bodyweight, is_squat, is_deadlift, is_run)
SELECT 'Run', 0, 0, 0, 0, true
WHERE NOT EXISTS (SELECT 1 FROM exercises WHERE is_run = true);
