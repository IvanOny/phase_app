-- Pull-up averages by season, kept by hand since 2021 -- years before the
-- app logged a single set, and since June 2026 the app logs pull-ups only on
-- PR attempts, so this is the longer and steadier series of the two.
--
-- One number per season as the athlete recorded it: the season's average.
-- Stored as given, keyed on (year, season) and not turned into dates --
-- whether "winter 2024" means Dec 2024-Feb 2025 or the start of 2024 is the
-- notebook's convention, and guessing would move every winter by a year.
-- A season with no record has no row.
CREATE TABLE IF NOT EXISTS pullup_seasons (
    year        SMALLINT     NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    season      TEXT         NOT NULL CHECK (season IN ('spring', 'summer', 'autumn', 'winter')),
    avg_reps    NUMERIC(4,1) NOT NULL CHECK (avg_reps >= 0),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (year, season)
);
