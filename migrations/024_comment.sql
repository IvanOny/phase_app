-- Comment field for burpee entries (logged via bot or web form)
ALTER TABLE burpee_entries ADD COLUMN IF NOT EXISTS comment TEXT;

-- Store comment alongside reps in pending so late-arriving video can include it
ALTER TABLE telegram_bot_pending ADD COLUMN IF NOT EXISTS comment TEXT;
