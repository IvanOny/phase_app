-- Who has been told they have circles.
--
-- Circles appear as one extra button inside 🤝, which is not somewhere people
-- look twice. Someone added to the beta would have the feature for weeks
-- without knowing, and telling them on every visit would be worse than never.
--
-- One timestamp: set when the notice goes out, and never cleared. Nobody is
-- told twice, and anyone added to MOVE_BETA_IDS later is told once, on their
-- next visit or the next morning, whichever comes first.

ALTER TABLE move_users
    ADD COLUMN IF NOT EXISTS circles_told_at TIMESTAMPTZ;

COMMENT ON COLUMN move_users.circles_told_at IS
    'When this person was told circles exist. NULL means the notice is still owed.';
