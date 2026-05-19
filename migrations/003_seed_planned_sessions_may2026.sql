-- Seed planned sessions for May 19–31 2026.
-- Finds the phase that covers this date range automatically.
-- Safe to run: skips any date that already has a planned session of the same type.

WITH target_phase AS (
  SELECT phase_id FROM phases
  WHERE start_date::date <= '2026-05-19'
    AND end_date::date   >= '2026-05-31'
  ORDER BY start_date DESC
  LIMIT 1
),
new_sessions (session_date, session_type) AS (
  VALUES
    ('2026-05-19'::date, 'pull'),
    ('2026-05-20'::date, 'speed_bench'),
    ('2026-05-21'::date, 'run'),
    ('2026-05-22'::date, 'heavy_bench'),
    ('2026-05-23'::date, 'run'),
    ('2026-05-24'::date, 'pull'),
    ('2026-05-25'::date, 'run'),
    ('2026-05-26'::date, 'heavy_bench'),
    ('2026-05-27'::date, 'run'),
    ('2026-05-28'::date, 'volume_bench'),
    ('2026-05-29'::date, 'pull'),
    ('2026-05-30'::date, 'run'),
    ('2026-05-31'::date, 'run')
)
INSERT INTO sessions (phase_id, session_date, session_type, is_planned)
SELECT
  p.phase_id,
  ns.session_date,
  ns.session_type,
  true
FROM target_phase p
CROSS JOIN new_sessions ns
WHERE NOT EXISTS (
  SELECT 1 FROM sessions s
  WHERE s.phase_id    = p.phase_id
    AND s.session_date::date = ns.session_date::date
    AND s.session_type = ns.session_type
    AND s.is_planned   = true
);
