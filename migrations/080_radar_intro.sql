-- How many times radar has explained itself to a person.
--
-- The first delivery already carried the explanation, decided for free from
-- radar_last_received being NULL. Three needs counting, and radar_hints is
-- taken: that one nudges people who have never found radar at all, which is
-- the opposite population.

ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS radar_intro SMALLINT NOT NULL DEFAULT 0;

COMMENT ON COLUMN move_users.radar_intro IS
    'Times a radar delivery has explained the setting behind it. Stops at _RADAR_INTRO.';
