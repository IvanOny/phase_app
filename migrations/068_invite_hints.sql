-- How many times the invite screen has explained what a circle is.
--
-- "Ця людина обмінюватиметься рухами лише з тобою" is worth saying while
-- someone is forming the idea and noise once they have it. The 🤝 screen is the
-- most-tapped in the bot -- six times in twenty minutes in one real trace -- so
-- a permanent paragraph there is a permanent tax.
--
-- Counted like bubble_hints and radar_hints, the two hints that already work
-- this way: shown a few times, then silent.
ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS invite_hints SMALLINT NOT NULL DEFAULT 0;
