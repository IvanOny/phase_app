-- A note about a training day as a whole, one per date.
--
-- A note about one exercise lives on that log's session (sessions.notes):
-- Quick log writes one session per exercise, so the two are the same thing.
-- A day, though, is several sessions, and none of them owns "slept badly,
-- everything felt heavy". Keyed on the date, like monthly_metrics on the
-- month: a fact about the person on that day, not about a phase.
CREATE TABLE IF NOT EXISTS day_notes (
    note_date   DATE PRIMARY KEY,
    note        TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
