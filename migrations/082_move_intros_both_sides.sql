-- Introductions become symmetric: nobody asks, both answer.
--
-- 081 had one person receive the suggestion and send the other an ordinary
-- crew request. This puts the same question to both at once — "Iv thinks you
-- and X should be moving together" — and connects them when both have said
-- yes. Neither is the asker, so neither is the one who was turned down.
ALTER TABLE move_intros DROP COLUMN IF EXISTS sent_at;
ALTER TABLE move_intros DROP COLUMN IF EXISTS declined_at;

ALTER TABLE move_intros ADD COLUMN IF NOT EXISTS a_ok_at   TIMESTAMPTZ;
ALTER TABLE move_intros ADD COLUMN IF NOT EXISTS b_ok_at   TIMESTAMPTZ;
ALTER TABLE move_intros ADD COLUMN IF NOT EXISTS a_no_at   TIMESTAMPTZ;
ALTER TABLE move_intros ADD COLUMN IF NOT EXISTS b_no_at   TIMESTAMPTZ;

-- No opt-out for now, so no column to hold one. It was dead schema the moment
-- the switch came off the settings menu, and a boolean nothing reads is worse
-- than no boolean: the next person to find it has to work out whether it means
-- anything. intro_hinted_at stays — the hint stays.
ALTER TABLE move_users DROP COLUMN IF EXISTS intros_ok;
