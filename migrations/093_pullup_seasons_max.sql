-- Seasonal pull-up maxima beside the averages (migration 091).
--
-- The notebook keeps a second table, "pull ups max", on the same seasons:
-- the best set of the season, and in brackets how many times it was hit --
-- "15(3)". It has seasons the averages do not (winter 2021), so an average
-- can now be absent; a row needs one of the two.
ALTER TABLE pullup_seasons ALTER COLUMN avg_reps DROP NOT NULL;
ALTER TABLE pullup_seasons ADD COLUMN IF NOT EXISTS max_reps  SMALLINT CHECK (max_reps >= 0);
ALTER TABLE pullup_seasons ADD COLUMN IF NOT EXISTS max_times SMALLINT CHECK (max_times >= 1);
ALTER TABLE pullup_seasons ADD CONSTRAINT pullup_seasons_has_value
    CHECK (avg_reps IS NOT NULL OR max_reps IS NOT NULL);
