-- «Всі» becomes a checkbox, so "nothing chosen" needs to exist.
--
-- Until now an empty circle selection MEANT everyone: the crew-wide send was
-- the default, and the "all" row was a radio marker because tapping it when
-- it was already on had nothing to do. As a checkbox it can be unticked, and
-- an unticked "all" with no group ticked is a state the row could not
-- represent -- the empty set and the whole crew were the same value.
--
-- pick_all is that missing bit. TRUE with no groups = everyone (the default,
-- and what every existing row means). FALSE with no groups = nobody yet, and
-- Send refuses until something is ticked. Groups ticked = pick_all is FALSE.
ALTER TABLE move_entries
    ADD COLUMN IF NOT EXISTS pick_all BOOLEAN NOT NULL DEFAULT TRUE;
