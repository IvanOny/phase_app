-- Move: one log message per person per day, edited as the day goes on.
--
-- Tracing wrote a message per incoming update, which buried the ⚠️ reports and
-- crashes that are the reason the log chat exists. The activity is still worth
-- having, so it collapses into a single message per person per day that gets
-- edited in place; alerts keep sending messages of their own.
--
-- body is kept because Telegram has no "append to message" — an edit replaces
-- the whole text, so the bot has to remember what it said. When a message fills
-- up (4096 characters), a new one starts and this row points at it instead.

CREATE TABLE IF NOT EXISTS move_log_summary (
    telegram_user_id BIGINT NOT NULL,
    log_date DATE NOT NULL,
    message_id BIGINT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_user_id, log_date)
);
