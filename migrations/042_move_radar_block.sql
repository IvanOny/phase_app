-- Move: let a radar viewer retire a stranger for good.
--
-- Radar is anonymous — the viewer never learns whose move they saw — so the
-- block is stored by telegram id, resolved from the entry behind the button.
-- The 7-day repeat window in move_radar_history is a cooldown; this is
-- permanent, and is checked in the same place.

CREATE TABLE IF NOT EXISTS move_radar_block (
    telegram_user_id BIGINT NOT NULL,   -- who pressed the button
    blocked_tg_id BIGINT NOT NULL,      -- whose moves they never want again
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_user_id, blocked_tg_id)
);
