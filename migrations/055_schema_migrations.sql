-- A ledger of which migrations have been applied.
--
-- Until now there wasn't one: migrations were written to be re-runnable
-- (CREATE TABLE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS) and you were expected
-- to remember what you'd run. That holds right up until a migration can't be
-- written idempotently -- a backfill, a one-way data change, a DROP -- and then
-- the only way to know whether it ran is to go and look at the schema. It also
-- means a second person, or a second machine, has no way to catch up.
--
-- checksum is the sha256 of the file as applied. It doesn't gate anything; it
-- lets the runner say "this file has changed since it ran here", which is the
-- interesting case when a migration is edited after the fact.

CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum    TEXT
);

COMMENT ON TABLE schema_migrations IS
    'One row per applied migration file. Written by scripts/run_migration.py.';
