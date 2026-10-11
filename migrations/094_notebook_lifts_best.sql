-- The best set of each notebook month, beside the average across sets
-- (migration 092): "8" over "60 7.37" is 8 reps in the best set at 60 kg,
-- 7.37 on average. Optional -- older rows may only have the average.
ALTER TABLE notebook_lifts ADD COLUMN IF NOT EXISTS best_reps SMALLINT CHECK (best_reps >= 0);
