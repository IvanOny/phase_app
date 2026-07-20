-- Movement Snacks: let a drag re-phase a recurring exercise.
--
-- Cadence suggestions are normally derived from last_done_at + interval. When a
-- user drags an item in "shift series" mode, we record the dropped day here and
-- project the series from it instead (anchor, anchor+interval, ...), so every
-- future occurrence follows and the rhythm is preserved.
-- NULL = no manual re-phasing; fall back to the last_done_at behaviour.

ALTER TABLE exercise_items ADD COLUMN IF NOT EXISTS anchor_date DATE;
