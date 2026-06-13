-- Add powerlifting session types to the sessions_session_type_check constraint.
ALTER TABLE sessions DROP CONSTRAINT sessions_session_type_check;

ALTER TABLE sessions ADD CONSTRAINT sessions_session_type_check
  CHECK (session_type IN (
    'heavy_bench', 'volume_bench', 'speed_bench',
    'run', 'pull', 'rest', 'other',
    'squat', 'deadlift', 'mix'
  ));
