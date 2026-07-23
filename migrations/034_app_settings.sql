-- Key/value store for single-account web-app settings (shared across browsers).
-- Run in Supabase SQL editor.
CREATE TABLE IF NOT EXISTS app_settings (
  key   TEXT PRIMARY KEY,
  value JSONB NOT NULL
);
