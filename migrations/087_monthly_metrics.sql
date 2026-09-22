-- One row per month of recovery metrics, typed in by hand at month's end.
--
-- HRV and resting heart rate as best-and-average; VO2 max as the month's best;
-- sleep as the month's average. "Best" is stored as the number entered -- the
-- form knows that a low resting HR is the good one, the table does not need
-- to. Every value is optional: a month with only HRV is a valid month.
--
-- Keyed on the month, not a phase. Like the lift trend, this is a history of
-- the person, and phases are training blocks laid over it.
CREATE TABLE IF NOT EXISTS monthly_metrics (
    month          CHAR(7) PRIMARY KEY,      -- 'YYYY-MM'
    hrv_best       NUMERIC(6,1),
    hrv_avg        NUMERIC(6,1),
    rhr_best       NUMERIC(5,1),
    rhr_avg        NUMERIC(5,1),
    vo2max_best    NUMERIC(5,1),
    sleep_avg      NUMERIC(5,1),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT monthly_metrics_month_shape CHECK (month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$')
);
