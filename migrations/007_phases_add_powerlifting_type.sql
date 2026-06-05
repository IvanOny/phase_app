-- Add 'powerlifting' to the allowed phase_type values.
ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_phase_type_check;

ALTER TABLE phases
  ADD CONSTRAINT phases_phase_type_check
  CHECK (phase_type IN ('bench', 'pull_ups', 'run', 'powerlifting'));
