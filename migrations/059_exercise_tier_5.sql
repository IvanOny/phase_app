-- A fifth tier, and everything drops one again.
--
-- Same move as migration 058, one step further: the top of the scale is being
-- kept clear so that "tier 1" means something when an item is put there, rather
-- than being where things sit by default.
--
-- Weights double again: 6/4/2/1 becomes 12/8/4/2/1. Tiers 1-4 keep the exact
-- frequencies they had (12:8:4:2 is 6:4:2:1) and tier 5 comes up half as often
-- as tier 4. Doubling rather than adding fractions keeps the serve query in
-- integers -- see _TIER_WEIGHT and _serve_next in phase_app/exercise_bot.py.
--
-- Not re-runnable, like 058: running it twice would shift twice. The ledger
-- from migration 055 is what makes that safe.
--
-- Constraint first, then the shift: the UPDATE moves rows to 5, which the old
-- CHECK would reject.

ALTER TABLE exercise_items DROP CONSTRAINT IF EXISTS exercise_items_tier_check;
ALTER TABLE exercise_items
  ADD CONSTRAINT exercise_items_tier_check CHECK (tier IN (1, 2, 3, 4, 5));

-- One statement, so every row is read from the same snapshot: 4 -> 5 can't be
-- re-read as 5 -> 6 mid-update.
UPDATE exercise_items SET tier = tier + 1 WHERE tier < 5;
