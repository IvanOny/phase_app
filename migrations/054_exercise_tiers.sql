-- Movement Snacks: one queue, three tiers.
--
-- The model had three scheduling modes (fixed cadence / opportunistic queue /
-- acquisition pins) and a dozen descriptive fields. In practice only the queue
-- was used, and the extra fields were filled in once and never read again.
--
-- What replaces it: everything is a queue item, and an item carries a tier that
-- says how much it matters. Tier 1 surfaces more often than tier 2, which
-- surfaces more often than tier 3 -- see _serve_next for the weighting.
--
-- The old columns are deliberately NOT dropped. Existing items still hold data
-- in them, the change is an experiment, and a nullable unused column costs
-- nothing. Dropping them is a separate decision once tiers have proven out.

ALTER TABLE exercise_items
  ADD COLUMN IF NOT EXISTS tier SMALLINT NOT NULL DEFAULT 2;

-- Seed tiers from the mode each item used to be in. The original schema called
-- fixed-cadence items "Tier 2" and queue items "Tier 3", and an acquisition pin
-- was something you were actively trying to build -- so it earns tier 1.
UPDATE exercise_items SET tier =
  CASE schedule_type
    WHEN 'acquisition' THEN 1
    WHEN 'fixed'       THEN 2
    ELSE 3
  END
WHERE tier = 2;

ALTER TABLE exercise_items DROP CONSTRAINT IF EXISTS exercise_items_tier_check;
ALTER TABLE exercise_items
  ADD CONSTRAINT exercise_items_tier_check CHECK (tier IN (1, 2, 3));

-- One scheduling mode from here on. The check constraint keeps allowing the old
-- values so nothing breaks mid-deploy; the bot and the web form stop offering
-- them, and nothing writes anything but 'queue'.
UPDATE exercise_items SET schedule_type = 'queue' WHERE schedule_type <> 'queue';

-- The serve query orders by weighted staleness across the whole active set, so
-- the useful index is the filter, not the sort.
CREATE INDEX IF NOT EXISTS idx_exercise_items_tier_serve
    ON exercise_items (user_id, status, tier);
