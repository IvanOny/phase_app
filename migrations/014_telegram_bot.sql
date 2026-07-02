CREATE TABLE IF NOT EXISTS telegram_bot_users (
    telegram_user_id BIGINT PRIMARY KEY,
    participant_name  TEXT NOT NULL,
    chat_id           BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_bot_pending (
    telegram_user_id BIGINT PRIMARY KEY,
    chat_id          BIGINT NOT NULL,
    message_id       BIGINT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Who each user wants to forward their videos to
CREATE TABLE IF NOT EXISTS telegram_bot_notify (
    telegram_user_id  BIGINT NOT NULL,
    notify_participant TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, notify_participant)
);

-- Tracks mid-conversation state (e.g. awaiting name input)
CREATE TABLE IF NOT EXISTS telegram_bot_state (
    telegram_user_id BIGINT PRIMARY KEY,
    state            TEXT NOT NULL
);
