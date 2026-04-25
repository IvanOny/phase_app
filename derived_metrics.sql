-- Derived metrics queries (live-first)
-- Raw data remains source-of-truth.
-- Snapshot cache is optional via phase_aggregations.

-- =========================================================
-- A) Session top-set e1RM (LIVE)
-- =========================================================
WITH top_sets AS (
    SELECT
        s.phase_id,
        s.session_id,
        s.session_date,
        es.exercise_set_id,
        es.reps,
        es.load_kg,
        (es.load_kg * (1 + es.reps::numeric / 30.0))::numeric(10,2) AS e1rm,
        ROW_NUMBER() OVER (
            PARTITION BY s.session_id
            ORDER BY es.load_kg DESC, es.reps DESC, es.exercise_set_id DESC
        ) AS rn
    FROM sessions s
    JOIN session_exercises se ON se.session_id = s.session_id
    JOIN exercises e ON e.exercise_id = se.exercise_id
    JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
    WHERE e.is_barbell_bench_press = TRUE
      AND es.is_top_set = TRUE
      AND s.session_id = :session_id
)
SELECT
    session_id,
    phase_id,
    session_date,
    exercise_set_id AS top_set_exercise_set_id,
    reps AS top_set_reps,
    load_kg AS top_set_load_kg,
    e1rm AS top_set_e1rm_kg,
    now() AS computed_at,
    NULL::INTEGER AS aggregation_version,
    'live'::TEXT AS source
FROM top_sets
WHERE rn = 1;

-- =========================================================
-- B) Session bench volume (LIVE)
-- =========================================================
SELECT
    s.session_id,
    s.phase_id,
    s.session_date,
    COALESCE(SUM(es.load_kg * es.reps), 0)::numeric(12,2) AS bench_volume_kg_reps,
    now() AS computed_at,
    NULL::INTEGER AS aggregation_version,
    'live'::TEXT AS source
FROM sessions s
JOIN session_exercises se ON se.session_id = s.session_id
JOIN exercises e ON e.exercise_id = se.exercise_id
JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
WHERE e.is_barbell_bench_press = TRUE
  AND es.is_working_set = TRUE
  AND s.session_id = :session_id
GROUP BY s.session_id, s.phase_id, s.session_date;

-- =========================================================
-- C) Phase summary (LIVE default)
-- =========================================================
WITH pullup_benchmarks AS (
    SELECT b.phase_id, p.reps::numeric AS pullup_reps
    FROM benchmarks b
    JOIN benchmark_pullup_max_reps p ON p.benchmark_id = b.benchmark_id
    WHERE b.benchmark_type = 'max_bodyweight_pullups'
),
run_benchmarks AS (
    SELECT
        b.phase_id,
        COALESCE(
            r.pace_min_per_km,
            ((r.elapsed_sec::numeric / 60.0) / NULLIF(r.distance_km, 0))
        )::numeric AS run_pace_min_per_km
    FROM benchmarks b
    JOIN benchmark_run_aerobic_test r ON r.benchmark_id = b.benchmark_id
    WHERE b.benchmark_type = 'run_aerobic_test'
),
live_summary AS (
    SELECT
        ph.phase_id,
        COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'max_bodyweight_pullups'), 0) AS benchmark_count_pullups,
        COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'run_aerobic_test'), 0) AS benchmark_count_run,
        AVG(pb.pullup_reps)::numeric(8,2) AS avg_pullup_max_reps,
        AVG(rb.run_pace_min_per_km)::numeric(8,2) AS avg_run_pace_min_per_km
    FROM phases ph
    LEFT JOIN benchmarks b ON b.phase_id = ph.phase_id
    LEFT JOIN pullup_benchmarks pb ON pb.phase_id = ph.phase_id
    LEFT JOIN run_benchmarks rb ON rb.phase_id = ph.phase_id
    WHERE ph.phase_id = :phase_id
    GROUP BY ph.phase_id
)
SELECT
    ls.phase_id,
    ls.benchmark_count_pullups,
    ls.benchmark_count_run,
    ls.avg_pullup_max_reps,
    ls.avg_run_pace_min_per_km,
    now() AS computed_at,
    NULL::INTEGER AS aggregation_version,
    'live'::TEXT AS source
FROM live_summary ls;

-- =========================================================
-- D) Phase summary from SNAPSHOT cache (optional)
-- =========================================================
-- Use when API request includes source=snapshot.
SELECT
    pa.phase_id,
    pa.benchmark_count_pullups,
    pa.benchmark_count_run,
    pa.avg_pullup_max_reps,
    pa.avg_run_pace_min_per_km,
    pa.computed_at,
    pa.aggregation_version,
    pa.source
FROM phase_aggregations pa
WHERE pa.phase_id = :phase_id
ORDER BY pa.aggregation_version DESC
LIMIT 1;
