-- Add is_planned flag to sessions table.
-- Run this in Supabase SQL editor before deploying the updated backend.
ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS is_planned BOOLEAN NOT NULL DEFAULT FALSE;
