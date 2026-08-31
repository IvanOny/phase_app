-- Move: bot messages that exist to be used, not kept.
--
-- Menus, prompts and confirmations are scaffolding: once the setting is set or
-- the question answered they are noise in a chat whose point is a record of what
-- you did. Moves, comments and the morning report are the record; everything
-- here is swept the next morning.
--
-- Next morning, not later: Telegram lets a bot delete its own messages for 48
-- hours, so an 8:00 sweep of yesterday's messages is comfortably inside the
-- window and anything slower would make them permanent.

CREATE TABLE IF NOT EXISTS move_transient (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_move_transient_age ON move_transient (created_at);
