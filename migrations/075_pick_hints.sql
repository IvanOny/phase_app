-- How many times the audience picker has explained itself.
--
-- The picker reads as a menu: a beta tester tapped a circle and waited, and
-- the move sat unaddressed because nothing said the choice had to be
-- confirmed with Send. A line of instruction fixes that, and then becomes
-- clutter — so it is counted, like the bubble and invite hints before it.
--
-- Counted on pickers shown rather than moves logged: three sightings is either
-- understood or a problem a sentence cannot fix.

ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS pick_hints SMALLINT NOT NULL DEFAULT 0;

COMMENT ON COLUMN move_users.pick_hints IS
    'Times the picker has shown its how-to. Stops at _PICK_HINTS.';
