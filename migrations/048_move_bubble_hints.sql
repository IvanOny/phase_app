-- Move: how many times we've explained the round-video gesture.
--
-- The instruction now goes to people who upload a video file instead of
-- recording a bubble — the moment it's useful, rather than in a welcome message
-- read before they've tried anything. Capped so it's a hint and not a lecture:
-- after three, they've either learned it or they prefer uploading, and both are
-- answers.

ALTER TABLE move_users ADD COLUMN IF NOT EXISTS bubble_hints INTEGER NOT NULL DEFAULT 0;
