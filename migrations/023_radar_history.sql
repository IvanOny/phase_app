CREATE TABLE IF NOT EXISTS radar_history (
    id SERIAL PRIMARY KEY,
    sender_participant TEXT NOT NULL,
    recipient_telegram_user_id BIGINT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);
