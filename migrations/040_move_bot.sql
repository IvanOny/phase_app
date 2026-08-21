-- Move — "the move of the day" Telegram bot.
--
-- Same skeleton as the burpee bot (identity, crew sharing, radar, streaks,
-- i18n, cron) but the unit of logging is a MOVE, not a rep count: everyone
-- does their own activity, so there is nothing to compare. The currency is
-- showing up (streaks) and ⚡ from your crew.
--
-- All tables are move_-prefixed and live alongside the burpee tables in the
-- same database. cron_log is shared (keyed by job_name).

CREATE TABLE IF NOT EXISTS move_users (
    telegram_user_id BIGINT PRIMARY KEY,
    chat_id BIGINT,
    participant_name TEXT UNIQUE,
    language_code TEXT,
    paused_until TIMESTAMPTZ,
    radar_freq TEXT NOT NULL DEFAULT 'never',      -- daily/weekly/monthly/once/never
    radar_send BOOLEAN NOT NULL DEFAULT FALSE,     -- may my moves go out to strangers
    radar_last_received TIMESTAMPTZ,
    last_greeted DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversational state for /start, /rename, /move (10-min timeout in code).
CREATE TABLE IF NOT EXISTS move_state (
    telegram_user_id BIGINT PRIMARY KEY,
    state TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One move per person per day.
CREATE TABLE IF NOT EXISTS move_entries (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL REFERENCES move_users(telegram_user_id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    media_type TEXT,             -- video_note / video / photo / animation / text
    chat_id BIGINT,              -- source chat, for copyMessage
    message_id BIGINT,           -- source message, for copyMessage
    text_body TEXT,              -- when logged via /log <text>
    comment TEXT,                -- optional, may arrive minutes later
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (telegram_user_id, entry_date)
);

CREATE INDEX IF NOT EXISTS idx_move_entries_user_date
    ON move_entries (telegram_user_id, entry_date DESC);

-- Share list ("Move with"): whose feed I send my move to. '__all__' = everyone.
CREATE TABLE IF NOT EXISTS move_crew (
    telegram_user_id BIGINT NOT NULL,
    crew_name TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, crew_name)
);

-- Follow list: whose moves I accept. Empty = accept from anyone in my crew.
CREATE TABLE IF NOT EXISTS move_receive (
    telegram_user_id BIGINT NOT NULL,
    from_name TEXT NOT NULL,
    PRIMARY KEY (telegram_user_id, from_name)
);

CREATE TABLE IF NOT EXISTS move_mute (
    telegram_user_id BIGINT NOT NULL,
    muted_name TEXT NOT NULL,
    muted_until TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (telegram_user_id, muted_name)
);

-- Where each entry landed. Needed to thread a late comment under the forwarded
-- copy (reply_to_message_id) and to refresh the ⚡ counter on the button.
CREATE TABLE IF NOT EXISTS move_forwards (
    id SERIAL PRIMARY KEY,
    entry_id INTEGER NOT NULL REFERENCES move_entries(id) ON DELETE CASCADE,
    recipient_tg_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_move_forwards_entry ON move_forwards (entry_id);

-- One ⚡ per person per entry.
CREATE TABLE IF NOT EXISTS move_reactions (
    entry_id INTEGER NOT NULL REFERENCES move_entries(id) ON DELETE CASCADE,
    reactor_tg_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entry_id, reactor_tg_id)
);

-- Radar: a stranger's move, at your chosen frequency. The same stranger may not
-- reappear for you within 7 days (enforced in code against this table).
CREATE TABLE IF NOT EXISTS move_radar_history (
    id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT NOT NULL,   -- recipient
    from_tg_id BIGINT NOT NULL,         -- whose move was shown
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_move_radar_history_pair
    ON move_radar_history (telegram_user_id, from_tg_id, sent_at DESC);

-- Streak milestones (7/14/30/50/100/200/365), cheered once each.
CREATE TABLE IF NOT EXISTS move_milestones (
    telegram_user_id BIGINT NOT NULL,
    streak_days INTEGER NOT NULL,
    notified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (telegram_user_id, streak_days)
);
