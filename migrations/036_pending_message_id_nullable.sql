-- Allow a pending row to hold reps that arrived BEFORE a video (message_id NULL),
-- so the following video note binds to them instead of asking for reps again.
-- Run in Supabase SQL editor.
ALTER TABLE telegram_bot_pending ALTER COLUMN message_id DROP NOT NULL;
