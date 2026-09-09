-- How many times the hold has explained itself.
--
-- "📹 Надсилаю через 45 с — є час передумати." teaches something once and
-- repeats it every day after. Counted, like the bubble, invite and picker
-- hints before it.
--
-- The message does not disappear entirely, because it is not only a sentence:
-- it carries the 🗑 that cancels the send, and it is the only sign that the
-- video arrived at all during the 45 seconds nothing else happens. Past the
-- count it shrinks to the countdown and the button.

ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS hold_hints SMALLINT NOT NULL DEFAULT 0;

COMMENT ON COLUMN move_users.hold_hints IS
    'Times the hold has shown its explanation. Stops at _HOLD_HINTS; the button stays.';
