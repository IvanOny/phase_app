-- One person belongs to at most one of your circles.
--
-- Circles are about to decide how many moves a day someone can receive: one to
-- the crew, one to their circle. That cap only holds if a person is in a single
-- circle — in two, they would get one move per circle plus the crew-wide one,
-- and the guarantee is gone.
--
-- The rule needs the owner, and move_circle_members only knew the circle. Adding
-- owner_tg_id denormalises it, which is the price of the database being able to
-- enforce this rather than every call site remembering to.
--
-- Nothing to clean up: no member belongs to two circles today.

ALTER TABLE move_circle_members
    ADD COLUMN IF NOT EXISTS owner_tg_id BIGINT;

UPDATE move_circle_members m SET owner_tg_id = c.owner_tg_id
FROM move_circles c WHERE c.id = m.circle_id AND m.owner_tg_id IS NULL;

ALTER TABLE move_circle_members ALTER COLUMN owner_tg_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS move_circle_members_one_per_owner
    ON move_circle_members (owner_tg_id, member_tg_id);
