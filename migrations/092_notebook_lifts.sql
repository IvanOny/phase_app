-- Monthly lift records from the training notebook (a spreadsheet kept by
-- hand before and alongside the app): one load per month per protocol, and
-- the average reps managed at it across the sets.
--
-- "60 7.37" in the sheet's bench row under "4-8 reps, 2min break" is 60 kg
-- for 7.37 reps on average. The protocol is part of the key: the same sheet
-- has a bench row under "reps, 1:30min break" at 50-55 kg, and the two are
-- different tests that must not be drawn as one line.
--
-- Pull-ups by season are in pullup_seasons (migration 091); this table is
-- for the monthly rows.
CREATE TABLE IF NOT EXISTS notebook_lifts (
    exercise    TEXT         NOT NULL,
    protocol    TEXT         NOT NULL,
    month       CHAR(7)      NOT NULL CHECK (month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    load_kg     NUMERIC(5,1) NOT NULL CHECK (load_kg >= 0),
    avg_reps    NUMERIC(5,2) NOT NULL CHECK (avg_reps >= 0),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (exercise, protocol, month)
);
