-- Deduplication guard for cron jobs (prevents Vercel retries from double-firing)
CREATE TABLE IF NOT EXISTS cron_log (
    job_name TEXT NOT NULL,
    run_date DATE NOT NULL,
    PRIMARY KEY (job_name, run_date)
);
