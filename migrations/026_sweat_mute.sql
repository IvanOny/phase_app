CREATE TABLE IF NOT EXISTS sweat_mute (
    telegram_user_id BIGINT NOT NULL,
    muted_participant TEXT NOT NULL,
    muted_until TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (telegram_user_id, muted_participant)
);
