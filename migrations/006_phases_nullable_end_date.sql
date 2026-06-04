-- Allow powerlifting phases to have no end date.
-- The existing phases_check constraint enforces end_date IS NOT NULL; drop it.
-- A partial constraint keeps the NOT NULL rule for all other phase types.

ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_check;

-- Re-add as a partial constraint: end_date required unless phase_type = 'powerlifting'
ALTER TABLE phases
  ADD CONSTRAINT phases_end_date_required
  CHECK (end_date IS NOT NULL OR phase_type = 'powerlifting');
