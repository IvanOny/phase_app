CREATE TABLE IF NOT EXISTS telegram_bot_receive (
    telegram_user_id   BIGINT NOT NULL,
    receive_participant TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, receive_participant)
);
