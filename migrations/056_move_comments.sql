-- Every comment, kept.
--
-- Until now a comment between two people was sent and forgotten: the text
-- existed only in the Telegram message the bot had already delivered. Nothing
-- in the database knew what anyone had said, which is why "what was in that
-- deleted message?" was unanswerable.
--
-- It has to be kept now, because a conversation is no longer a pile of
-- messages: each pair of people gets ONE message per move, rebuilt from these
-- rows and re-sent every time a line is added. Without the rows there is
-- nothing to rebuild from.
--
-- The thread key is (entry_id, the two people) regardless of direction, so the
-- index covers lookups either way round.

CREATE TABLE IF NOT EXISTS move_comments (
    id          BIGSERIAL PRIMARY KEY,
    entry_id    BIGINT NOT NULL REFERENCES move_entries(id) ON DELETE CASCADE,
    from_tg_id  BIGINT NOT NULL,
    to_tg_id    BIGINT NOT NULL,
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS move_comments_thread
    ON move_comments (entry_id, from_tg_id, to_tg_id, id);
CREATE INDEX IF NOT EXISTS move_comments_thread_rev
    ON move_comments (entry_id, to_tg_id, from_tg_id, id);

COMMENT ON TABLE move_comments IS
    'One row per comment. A thread is every row for an entry between two people.';
