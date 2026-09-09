-- Every message the bot places, kept, so a chat can be replayed verbatim.
--
-- Their side of a conversation was always recoverable: move_log_summary keeps
-- each person's actions for the day and outlives the Telegram message it was
-- rendered into. The bot's side was not stored at all — move_transient and
-- move_forwards hold ids, times and kinds, so a reply could only be replayed
-- as "[confirm] #1398" and never as the sentence somebody actually read. Two
-- days of debugging by screenshot made the case for this.
--
-- Written from _api_call, the one funnel every outgoing call already goes
-- through, so nothing has to be remembered at sixty call sites. Edits and
-- deletions are recorded too: a thread that is deleted and re-sent whenever a
-- line is added replays as nonsense without them.
--
-- Pruned by the morning sweep. This is a debugging record, not an archive, and
-- keeping people's messages longer than they are useful is its own decision.

CREATE TABLE IF NOT EXISTS move_sent (
    id         BIGSERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL,
    message_id BIGINT,
    method     TEXT   NOT NULL,
    body       TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS move_sent_chat_day ON move_sent (chat_id, created_at);
CREATE INDEX IF NOT EXISTS move_sent_created ON move_sent (created_at);

COMMENT ON TABLE move_sent IS
    'What the bot said, when, and in which chat. Replay evidence; swept after 30 days.';
