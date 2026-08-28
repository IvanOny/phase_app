-- Move: two things the bot needs to remember so it can prompt once, not daily.
--
-- nudged_at: someone who registered and never posted gets one nudge, the
-- morning after. last_greeted (040) is unused but is a DATE with a name that
-- promises something else, so this gets its own column rather than borrowing it.
--
-- radar_seen_at: set the first time someone opens the radar menu. It's the only
-- way to tell "never found this" from "looked and chose off" — radar_freq is
-- 'never' by default, so the setting itself can't distinguish the two, and
-- nagging someone about a feature they deliberately declined is worse than
-- staying quiet.

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS nudged_at DATE;
ALTER TABLE move_users ADD COLUMN IF NOT EXISTS radar_seen_at TIMESTAMPTZ;
ALTER TABLE move_users ADD COLUMN IF NOT EXISTS radar_hinted_at DATE;

-- Backfill: anyone whose radar settings differ from the defaults has plainly
-- been in that menu, and shouldn't be told the feature exists. Without this,
-- everyone who set radar up before this column existed reads as "never found it".
UPDATE move_users
   SET radar_seen_at = NOW()
 WHERE radar_seen_at IS NULL
   AND (radar_send = TRUE OR COALESCE(radar_freq, 'never') <> 'never');
