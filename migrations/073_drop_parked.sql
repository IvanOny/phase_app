-- One way to shelve a snack, not two.
--
-- exercise_items.status held 'active', 'paused' and 'parked'. Nothing ever
-- distinguished the last two: every query that reads status filters on
-- 'active', so pausing and parking removed an item from the queue, the daily
-- report and `next` in exactly the same way. The difference existed only in the
-- word and in one prompt ("You keep skipping X — park it?").
--
-- Anything parked becomes paused. Nothing observable changes, which is the
-- argument for the removal: a distinction that costs a decision and buys
-- nothing is worse than no distinction.
--
-- No constraint to drop — status was never enumerated in the schema. The
-- validation lived in exercise_api and the bot's own mapping, and both now
-- know two values.

UPDATE exercise_items SET status = 'paused' WHERE status = 'parked';
