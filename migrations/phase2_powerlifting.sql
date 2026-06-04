-- Phase 2: Powerlifting migration
-- Run once against the Supabase DB.

-- 1. Exercise classification flags
ALTER TABLE exercises
  ADD COLUMN IF NOT EXISTS is_squat    INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS is_deadlift INTEGER NOT NULL DEFAULT 0;

-- 2. Per-session bodyweight log
--    session_id is nullable — user can log bodyweight without tying it to a session.
CREATE TABLE IF NOT EXISTS bodyweight_log (
  log_id       SERIAL PRIMARY KEY,
  phase_id     INTEGER REFERENCES phases(phase_id) ON DELETE CASCADE,
  session_id   INTEGER REFERENCES sessions(session_id) ON DELETE SET NULL,
  logged_date  DATE NOT NULL,
  weight_kg    NUMERIC(5,2) NOT NULL
);

-- 3. Confirmed 1RM entries (manual override over e1RM)
CREATE TABLE IF NOT EXISTS confirmed_1rm (
  rm_id        SERIAL PRIMARY KEY,
  phase_id     INTEGER REFERENCES phases(phase_id) ON DELETE CASCADE,
  session_id   INTEGER REFERENCES sessions(session_id) ON DELETE SET NULL,
  logged_date  DATE NOT NULL,
  lift_type    VARCHAR(20) NOT NULL CHECK (lift_type IN ('bench', 'squat', 'deadlift')),
  weight_kg    NUMERIC(6,2) NOT NULL
);
