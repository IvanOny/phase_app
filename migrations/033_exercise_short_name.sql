-- Movement Snacks: optional short label for calendar chips.
-- Long names (e.g. "Resistance band ankle eversion/inversion") are unreadable in
-- a narrow day cell. short_name, when set, is shown on chips/pills; the full
-- name stays as the hover tooltip and everywhere else.

ALTER TABLE exercise_items ADD COLUMN IF NOT EXISTS short_name TEXT;
