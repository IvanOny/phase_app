ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS run_type              TEXT,
  ADD COLUMN IF NOT EXISTS max_hr               INTEGER,
  ADD COLUMN IF NOT EXISTS avg_cadence          INTEGER,
  ADD COLUMN IF NOT EXISTS avg_gct_ms           INTEGER,
  ADD COLUMN IF NOT EXISTS avg_vo_cm            NUMERIC(5, 1),
  ADD COLUMN IF NOT EXISTS ascent_m             INTEGER,
  ADD COLUMN IF NOT EXISTS rpe                  NUMERIC(3, 1),
  ADD COLUMN IF NOT EXISTS avg_gap_pace_sec_per_km INTEGER;
