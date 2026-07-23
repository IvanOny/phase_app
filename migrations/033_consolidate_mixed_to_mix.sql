-- Consolidate legacy 'mixed' powerlifting sessions into 'mix'.
-- Run in Supabase SQL editor.
--
-- Order matters: drop the constraint first so the UPDATE can't be blocked,
-- migrate the data, then re-add the constraint WITH 'mix' and WITHOUT 'mixed'.

ALTER TABLE sessions DROP CONSTRAINT sessions_session_type_check;

UPDATE sessions SET session_type = 'mix' WHERE session_type = 'mixed';

ALTER TABLE sessions ADD CONSTRAINT sessions_session_type_check
  CHECK (session_type IN (
    'heavy_bench', 'volume_bench', 'speed_bench',
    'run', 'pull', 'rest', 'other',
    'squat', 'deadlift', 'mix'
  ));
