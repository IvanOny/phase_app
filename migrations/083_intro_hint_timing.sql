-- The hint stops arriving the instant it becomes true, and gains a second try.
--
-- Becoming able to introduce two people happens as a side effect of something
-- else -- a third person joining your crew -- and a message about a new feature
-- landing in the same second as that is a message about the wrong thing. It
-- waits a day now, so it arrives on its own.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS intro_eligible_since TIMESTAMPTZ;

-- And one reminder, once, for someone who was told and did nothing. Not a
-- repeat of the same nudge: the bar is higher (four people who could be
-- connected, rather than two), so it fires when there is visibly more to do
-- than there was the first time, and it never fires for anyone who has
-- actually suggested somebody.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS intro_hinted2_at TIMESTAMPTZ;

-- Anyone already hinted counts as eligible from the moment they were hinted;
-- without this their intro_eligible_since would be NULL and the 24-hour rule
-- would have nothing to measure from.
UPDATE move_users
   SET intro_eligible_since = intro_hinted_at
 WHERE intro_hinted_at IS NOT NULL
   AND intro_eligible_since IS NULL;
