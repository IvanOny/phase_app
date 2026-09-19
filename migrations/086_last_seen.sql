-- The read receipt, once the ⚡ is gone.
--
-- Telegram gives a bot no read receipts, and the first ⚡ on a move was the
-- only proof of a viewer we ever got -- it is what stopped Undo. With zaps
-- dropped, the signal is the one the bot already receives on every update:
-- the person did something in Move. In a private bot chat the newest message
-- is at the bottom, so if the last thing that arrived was your video, opening
-- the chat is seeing it.
--
-- Stamped on every incoming update. Undo is refused when any recipient's
-- last_seen_at is later than their copy's created_at -- which covers the
-- people who never reacted to anything and always saw everything.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

-- move_reactions stays as a record of what was; nothing writes to it any more.
