ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_freq TEXT NOT NULL DEFAULT 'never';
ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_last_received TIMESTAMPTZ;
