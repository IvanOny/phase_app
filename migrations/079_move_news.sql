-- Who has been told about what.
--
-- Announcements have been one-offs so far, each with its own column:
-- circles_told_at, invite_hints, pick_hints. That works for a permanent piece
-- of teaching attached to a feature, and not at all for "here is what changed
-- this week", which happens repeatedly and is dated.
--
-- One row per person per announcement, keyed by a string the code picks. An
-- announcement that half-sends because the run was cut short resumes on the
-- next run and nobody hears it twice.

CREATE TABLE IF NOT EXISTS move_news_sent (
    news_key         TEXT   NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    sent_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (news_key, telegram_user_id)
);

COMMENT ON TABLE move_news_sent IS
    'One row per person per announcement. The guard that stops anyone being told twice.';
