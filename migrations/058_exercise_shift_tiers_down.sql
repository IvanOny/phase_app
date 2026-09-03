-- Everything drops one tier, leaving tier 1 empty.
--
-- Tier 1 was carrying eight of eighteen items, which is not what a top tier is
-- for: if nearly half the queue is "most often", the tier says nothing. Empty,
-- it becomes somewhere to put the one or two things actually being pushed right
-- now, and everything else sits below.
--
-- This is the first migration in the repo that is NOT re-runnable. Running it
-- twice would shift twice, and a third time would fail the CHECK rather than
-- quietly do the wrong thing. What makes that safe is the ledger added in
-- migration 055: schema_migrations records this file, and the runner skips it
-- from then on.
--
-- One statement, so every row is read from the same snapshot: 3 -> 4 can't be
-- re-read as 4 -> 5 mid-update. Nothing is in tier 4 at the time of writing, so
-- nothing lands outside the constraint.

UPDATE exercise_items SET tier = tier + 1 WHERE tier < 4;
