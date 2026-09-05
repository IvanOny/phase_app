-- One move a day to the crew, and one a day to each circle.
--
-- Until now move_entries had UNIQUE (telegram_user_id, entry_date): one move per
-- person per day, full stop. With circles that is too strict — a move for the
-- gym and a move for everyone are different things with different audiences —
-- and dropping it outright is too loose, because "one a day" is what keeps any
-- single receiver at no more than two messages from one person.
--
-- The rule that gives both: at most one crew-wide move a day, and at most one
-- move a day per circle. Because circles partition the crew (migration 066),
-- that bounds every receiver at two.
--
-- Neither half is expressible against move_entries alone: crew-wide-ness lives
-- in the absence of rows in move_entry_circles, and a circle's use lives in that
-- table too. So each half is denormalised to where it can be indexed —
-- is_crew_wide on the entry, and the owner and date on the circle link.
--
-- Every existing move is crew-wide, which is what the default records.

ALTER TABLE move_entries
    ADD COLUMN IF NOT EXISTS is_crew_wide BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE move_entries
    DROP CONSTRAINT IF EXISTS move_entries_telegram_user_id_entry_date_key;

CREATE UNIQUE INDEX IF NOT EXISTS move_entries_one_crew_wide_per_day
    ON move_entries (telegram_user_id, entry_date) WHERE is_crew_wide;

ALTER TABLE move_entry_circles
    ADD COLUMN IF NOT EXISTS owner_tg_id BIGINT,
    ADD COLUMN IF NOT EXISTS entry_date  DATE;

UPDATE move_entry_circles ec
SET owner_tg_id = e.telegram_user_id, entry_date = e.entry_date
FROM move_entries e WHERE e.id = ec.entry_id AND ec.owner_tg_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS move_entry_circles_one_per_day
    ON move_entry_circles (owner_tg_id, entry_date, circle_id);

COMMENT ON COLUMN move_entries.is_crew_wide IS
    'True when the move went to the whole crew rather than to named circles.';
