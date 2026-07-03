ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_freq TEXT NOT NULL DEFAULT 'daily';
ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_last_received TIMESTAMPTZ;

-- Set existing users who still have the old default to daily
UPDATE telegram_bot_users SET radar_freq = 'daily' WHERE radar_freq = 'never';
