ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS token TEXT UNIQUE;

-- Backfill tokens for anyone already registered
UPDATE telegram_bot_users
SET token = 'бурчик-' || LOWER(participant_name)
WHERE token IS NULL;
