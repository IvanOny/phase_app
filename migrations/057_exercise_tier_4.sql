-- A fourth tier: things you want in the rotation but rarely.
--
-- Three tiers made "occasional" carry two jobs at once — the things that
-- should come up now and then, and the things you don't want to lose but
-- barely want to see. Tier 4 is the second one.
--
-- The weights change shape but not ratio. They were 3/2/1; they are now
-- 6/4/2/1, so tiers 1-3 keep exactly the frequencies they had (6:4:2 is 3:2:1)
-- and tier 4 comes up half as often as tier 3. Doubling rather than adding a
-- fraction keeps the arithmetic in integers, which is what the serve query
-- multiplies by. See _TIER_WEIGHT and _serve_next in phase_app/exercise_bot.py.
--
-- Nothing is re-tiered here. Existing items keep the tier they have; tier 4 is
-- somewhere to move things to, not a place anything lands automatically.

ALTER TABLE exercise_items DROP CONSTRAINT IF EXISTS exercise_items_tier_check;
ALTER TABLE exercise_items
  ADD CONSTRAINT exercise_items_tier_check CHECK (tier IN (1, 2, 3, 4));
