-- Two explicit radar permissions: receiving and sending
ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_send BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_asked BOOLEAN NOT NULL DEFAULT FALSE;

-- Opt all existing users out of both until they explicitly choose
UPDATE telegram_bot_users SET radar_freq = 'never', radar_send = FALSE, radar_asked = FALSE;
