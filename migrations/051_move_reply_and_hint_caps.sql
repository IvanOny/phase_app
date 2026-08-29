-- Move: two things the bot couldn't answer.
--
-- from_tg_id: move_forwards recorded who a message went TO, never who it came
-- FROM. That's enough to route a reply to a crew copy (the move's author is on
-- the entry) but not a reply to a comment someone sent you — the one case where
-- replying is the obvious thing to do. Backfilled from the entry's author, which
-- is correct for every kind except 'note'; those older rows keep pointing at the
-- author, so a reply to a pre-existing note reaches the person whose move it was
-- rather than the commenter. New note rows carry the real sender.
--
-- radar_hints: the radar hint repeated every 21 days for as long as someone
-- never opened the menu, which is forever. Counting them lets it stop.

ALTER TABLE move_forwards ADD COLUMN IF NOT EXISTS from_tg_id BIGINT;

UPDATE move_forwards f
   SET from_tg_id = e.telegram_user_id
  FROM move_entries e
 WHERE e.id = f.entry_id AND f.from_tg_id IS NULL;

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS radar_hints INTEGER NOT NULL DEFAULT 0;

-- Anyone already hinted has had exactly one.
UPDATE move_users SET radar_hints = 1 WHERE radar_hinted_at IS NOT NULL AND radar_hints = 0;
