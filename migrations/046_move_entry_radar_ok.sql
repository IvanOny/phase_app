-- Move: a per-move radar decision.
--
-- radar_send on move_users is a standing preference: share every move with
-- strangers, or none. That's a big commitment, and most people won't make it —
-- which is why the radar pool stays small. This column lets one move be
-- decided on its own: today's video, yes; tomorrow's, no.
--
-- NULL means "follow my standing preference", so every move already in the
-- table keeps behaving exactly as it does now, and the button only has to write
-- a value when someone actually disagrees with their own default.
--
-- The choice never rewrites radar_send: one move's decision shouldn't silently
-- become the standing one.

ALTER TABLE move_entries ADD COLUMN IF NOT EXISTS radar_ok BOOLEAN;

COMMENT ON COLUMN move_entries.radar_ok IS
    'TRUE/FALSE = this move overrides move_users.radar_send; NULL = follow it.';
