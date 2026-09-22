-- Garmin's monthly running summary, one row per month, pasted in whole.
--
-- Twenty-two metrics after the month name, in the order Garmin's table has
-- them. Stored typed -- time in seconds, pace in seconds per kilometre,
-- distances in km, everything else in the unit Garmin shows -- and the pasted
-- line is kept beside them, so a parsing mistake can be re-read from the
-- source rather than re-typed.
--
-- Keyed on the month, like monthly_metrics: a history of the person.
CREATE TABLE IF NOT EXISTS monthly_run (
    month              CHAR(7) PRIMARY KEY,
    activities         INTEGER,
    total_km           NUMERIC(7,2),
    avg_km             NUMERIC(6,2),
    max_km             NUMERIC(6,2),
    total_time_s       INTEGER,
    calories           INTEGER,
    total_ascent_m     INTEGER,
    avg_ascent_m       INTEGER,
    max_ascent_m       INTEGER,
    total_descent_m    INTEGER,
    avg_descent_m      INTEGER,
    max_descent_m      INTEGER,
    avg_pace_s         INTEGER,      -- seconds per km
    gap_pace_s         INTEGER,      -- grade-adjusted
    best_pace_s        INTEGER,
    avg_hr             INTEGER,
    max_hr             INTEGER,
    avg_cadence_spm    INTEGER,
    max_cadence_spm    INTEGER,
    vertical_osc_cm    NUMERIC(4,1),
    ground_contact_ms  INTEGER,
    avg_stride_m       NUMERIC(4,2),
    raw                TEXT,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT monthly_run_month_shape CHECK (month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$')
);
