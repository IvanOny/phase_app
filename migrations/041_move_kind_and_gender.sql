-- Move: distinguish what each forwarded message is, and remember grammatical
-- gender for Ukrainian.
--
-- kind: move_forwards tracks three different things now — the copied media
-- ("move"), the "<name> moved today" line ("header") and each comment reply
-- ("comment"). Undo must delete all of them, but only the "move" row carries
-- the ⚡ button, so refreshing that button has to target it specifically.
--
-- gender: Ukrainian past-tense verbs are gendered ("рухався" vs "рухалася"),
-- so a female user was being described in the masculine. NULL = unknown, which
-- falls back to a genderless phrasing.

ALTER TABLE move_forwards ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'move';

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS gender TEXT;
