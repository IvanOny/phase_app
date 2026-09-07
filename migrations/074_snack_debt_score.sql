-- A snack's score is what it owes, not what it has earned.
--
-- Until now the number on a snack was the sum of everything it had ever
-- scored: it only ever grew, so skipping something cost nothing visible and
-- the pill that looked best was often one untouched for a fortnight.
--
-- The new score is a debt. It rises every day by the tier weight — 12 a day at
-- tier 1, then 8, 4, 2, 1 — and falls by that same weight each time the snack
-- is done. One tick buys exactly one day of quiet, so anything kept at its
-- intended cadence hovers flat, and anything neglected climbs at a rate set by
-- how often it was meant to come round. Sorting by it puts the most overdue
-- thing on top, which is a question "oldest first" could never answer: a
-- tier-1 left three days is more urgent than a tier-5 left three weeks.
--
-- score_day is what makes it honest without a nightly job that must never be
-- missed. Accrual is `weight × (today − score_day)`, applied whenever anything
-- reads the list, so a week when the cron never fired catches up in one go
-- instead of vanishing. Running it twice in a day adds nothing.
--
-- Everything starts at 50: a deliberate flat start rather than a backfill from
-- history, which would have opened with a ranking nobody chose. A new snack
-- starts there too — added but never done, it should sit mid-list and climb,
-- not begin at the bottom.
--
-- No ceiling, on purpose. Something ignored for a year should read as ignored
-- for a year; tier and pause are the ways to say you meant it.

ALTER TABLE exercise_items
    ADD COLUMN IF NOT EXISTS score    INTEGER NOT NULL DEFAULT 50,
    ADD COLUMN IF NOT EXISTS score_day DATE   NOT NULL DEFAULT CURRENT_DATE;

UPDATE exercise_items SET score = 50, score_day = CURRENT_DATE;

COMMENT ON COLUMN exercise_items.score IS
    'How overdue this snack is. Rises by the tier weight per day, falls by it per tick. Sorted descending.';
COMMENT ON COLUMN exercise_items.score_day IS
    'Date the score was last brought up to today. Accrual is weight x (CURRENT_DATE - score_day).';
