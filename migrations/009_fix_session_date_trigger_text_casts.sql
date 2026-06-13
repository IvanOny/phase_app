-- Fix check_session_date_in_phase trigger for TEXT-typed date columns.
-- session_date, start_date, and end_date are stored as TEXT, so explicit
-- ::date casts are required for comparisons.

CREATE OR REPLACE FUNCTION check_session_date_in_phase()
RETURNS TRIGGER AS $$
DECLARE
  p_start DATE;
  p_end   DATE;
BEGIN
  SELECT start_date::date, end_date::date INTO p_start, p_end
  FROM phases WHERE phase_id = NEW.phase_id;

  IF NEW.session_date::date < p_start THEN
    RAISE EXCEPTION 'session_date must be within phase window';
  END IF;

  -- Only check end_date if it is set (open-ended phases have no end_date)
  IF p_end IS NOT NULL AND NEW.session_date::date > p_end THEN
    RAISE EXCEPTION 'session_date must be within phase window';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
