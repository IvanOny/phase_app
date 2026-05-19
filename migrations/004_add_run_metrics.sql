-- Add structured run metrics to sessions table.
-- Run in Supabase SQL editor before deploying.
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS distance_km     NUMERIC(6, 2),
  ADD COLUMN IF NOT EXISTS duration_seconds INTEGER,
  ADD COLUMN IF NOT EXISTS avg_hr          INTEGER,
  ADD COLUMN IF NOT EXISTS avg_pace_sec_per_km INTEGER;
