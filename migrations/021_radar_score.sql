ALTER TABLE telegram_bot_users ADD COLUMN IF NOT EXISTS radar_score INTEGER NOT NULL DEFAULT 10;

CREATE TABLE IF NOT EXISTS radar_candidates (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    message_id INTEGER,
    participant_name TEXT NOT NULL,
    reps INTEGER NOT NULL,
    logged_at TIMESTAMPTZ DEFAULT NOW(),
    candidate_date DATE NOT NULL DEFAULT CURRENT_DATE,
    processed BOOLEAN DEFAULT FALSE,
    UNIQUE (telegram_user_id, candidate_date)
);
