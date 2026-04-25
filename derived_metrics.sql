-- Derived metrics for phase-based training app
-- Assumptions:
-- 1) e1RM uses Epley: e1RM = load_kg * (1 + reps/30.0)
-- 2) "Top set" is rows where top_set_flag = TRUE
-- 3) Bench volume uses working sets only and only barbell bench exercise rows

-- =========================================================
-- A) e1RM calculation from top set (session-level)
-- =========================================================
WITH top_sets AS (
    SELECT
        s.phase_id,
        s.session_id,
        s.session_date,
        es.exercise_set_id,
        es.reps,
        es.load_kg,
        -- Epley formula
        (es.load_kg * (1 + es.reps::numeric / 30.0))::numeric(10,2) AS e1rm,
        ROW_NUMBER() OVER (
            PARTITION BY s.session_id
            ORDER BY es.load_kg DESC, es.reps DESC, es.exercise_set_id DESC
        ) AS rn
    FROM sessions s
    JOIN session_exercises se
      ON se.session_id = s.session_id
    JOIN exercises e
      ON e.exercise_id = se.exercise_id
    JOIN exercise_sets es
      ON es.session_exercise_id = se.session_exercise_id
    WHERE e.is_barbell_bench_press = TRUE
      AND es.top_set_flag = TRUE
)
SELECT
    phase_id,
    session_id,
    session_date,
    reps AS top_set_reps,
    load_kg AS top_set_load_kg,
    e1rm AS top_set_e1rm_kg
FROM top_sets
WHERE rn = 1;

-- Notes / edge handling:
-- - If multiple top sets exist in one session, rn=1 keeps the heaviest/highest-rep tie-broken by latest id.
-- - If no top set exists, session has no e1RM row.

-- =========================================================
-- B) Bench volume calculation
-- =========================================================
-- Session-level bench volume: sum(load_kg * reps) for barbell bench working sets.
SELECT
    s.phase_id,
    s.session_id,
    s.session_date,
    s.session_type,
    COALESCE(SUM(es.load_kg * es.reps), 0)::numeric(12,2) AS bench_volume_kg_reps
FROM sessions s
JOIN session_exercises se
  ON se.session_id = s.session_id
JOIN exercises e
  ON e.exercise_id = se.exercise_id
JOIN exercise_sets es
  ON es.session_exercise_id = se.session_exercise_id
WHERE e.is_barbell_bench_press = TRUE
  AND es.is_working_set = TRUE
  AND s.session_type IN ('heavy_bench', 'volume_bench', 'speed_bench')
GROUP BY s.phase_id, s.session_id, s.session_date, s.session_type
ORDER BY s.session_date;

-- =========================================================
-- C) Phase average calculations
-- =========================================================
-- Includes:
-- - avg bench top-set e1RM
-- - avg bench session volume
-- - avg pull-up benchmark reps
-- - avg run benchmark pace (min/km)
WITH bench_topset_e1rm_by_session AS (
    SELECT
        s.phase_id,
        s.session_id,
        MAX((es.load_kg * (1 + es.reps::numeric / 30.0))) AS top_set_e1rm
    FROM sessions s
    JOIN session_exercises se ON se.session_id = s.session_id
    JOIN exercises e ON e.exercise_id = se.exercise_id
    JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
    WHERE e.is_barbell_bench_press = TRUE
      AND es.top_set_flag = TRUE
    GROUP BY s.phase_id, s.session_id
),
bench_volume_by_session AS (
    SELECT
        s.phase_id,
        s.session_id,
        SUM(es.load_kg * es.reps) AS bench_volume
    FROM sessions s
    JOIN session_exercises se ON se.session_id = s.session_id
    JOIN exercises e ON e.exercise_id = se.exercise_id
    JOIN exercise_sets es ON es.session_exercise_id = se.session_exercise_id
    WHERE e.is_barbell_bench_press = TRUE
      AND es.is_working_set = TRUE
    GROUP BY s.phase_id, s.session_id
),
pullup_benchmarks AS (
    SELECT b.phase_id, p.reps::numeric AS pullup_reps
    FROM benchmarks b
    JOIN benchmark_pullup_max_reps p
      ON p.benchmark_id = b.benchmark_id
    WHERE b.benchmark_type = 'max_bodyweight_pullups'
),
run_benchmarks AS (
    SELECT b.phase_id, r.pace_min_per_km::numeric AS run_pace_min_per_km
    FROM benchmarks b
    JOIN benchmark_run_aerobic_test r
      ON r.benchmark_id = b.benchmark_id
    WHERE b.benchmark_type = 'run_aerobic_test'
)
SELECT
    ph.phase_id,
    ph.phase_type,
    AVG(bte.top_set_e1rm)::numeric(10,2) AS avg_bench_topset_e1rm,
    AVG(bv.bench_volume)::numeric(12,2) AS avg_bench_session_volume,
    AVG(pb.pullup_reps)::numeric(8,2) AS avg_pullup_max_reps,
    AVG(rb.run_pace_min_per_km)::numeric(8,2) AS avg_run_pace_min_per_km
FROM phases ph
LEFT JOIN bench_topset_e1rm_by_session bte ON bte.phase_id = ph.phase_id
LEFT JOIN bench_volume_by_session bv ON bv.phase_id = ph.phase_id
LEFT JOIN pullup_benchmarks pb ON pb.phase_id = ph.phase_id
LEFT JOIN run_benchmarks rb ON rb.phase_id = ph.phase_id
GROUP BY ph.phase_id, ph.phase_type
ORDER BY ph.phase_id;

-- =========================================================
-- D) benchmark_count_in_phase
-- =========================================================
SELECT
    ph.phase_id,
    COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'max_bodyweight_pullups'), 0) AS benchmark_count_pullups,
    COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'run_aerobic_test'), 0) AS benchmark_count_run,
    COALESCE(COUNT(b.benchmark_id), 0) AS benchmark_count_in_phase
FROM phases ph
LEFT JOIN benchmarks b
  ON b.phase_id = ph.phase_id
GROUP BY ph.phase_id
ORDER BY ph.phase_id;

-- =========================================================
-- E) readiness color classification
-- =========================================================
-- Scale uses sessions.elite_hrv_readiness (0-10).
-- Suggested thresholds:
--   green  = >= 7.0
--   yellow = >= 5.0 and < 7.0
--   red    = < 5.0
--   gray   = missing
SELECT
    s.session_id,
    s.phase_id,
    s.session_date,
    s.elite_hrv_readiness,
    CASE
        WHEN s.elite_hrv_readiness IS NULL THEN 'gray'
        WHEN s.elite_hrv_readiness >= 7.0 THEN 'green'
        WHEN s.elite_hrv_readiness >= 5.0 THEN 'yellow'
        ELSE 'red'
    END AS readiness_color
FROM sessions s
ORDER BY s.session_date;

-- =========================================================
-- F) Example: write-back into phase_aggregations (version 1 snapshot)
-- =========================================================
-- You can run this as part of a batch job after each phase closes.
WITH phase_metrics AS (
    SELECT
        ph.phase_id,
        COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'max_bodyweight_pullups'), 0) AS benchmark_count_pullups,
        COALESCE(COUNT(*) FILTER (WHERE b.benchmark_type = 'run_aerobic_test'), 0) AS benchmark_count_run,
        AVG(pu.reps::numeric) AS avg_pullup_max_reps,
        AVG(rt.pace_min_per_km::numeric) AS avg_run_pace_min_per_km
    FROM phases ph
    LEFT JOIN benchmarks b ON b.phase_id = ph.phase_id
    LEFT JOIN benchmark_pullup_max_reps pu ON pu.benchmark_id = b.benchmark_id
    LEFT JOIN benchmark_run_aerobic_test rt ON rt.benchmark_id = b.benchmark_id
    GROUP BY ph.phase_id
)
INSERT INTO phase_aggregations (
    phase_id,
    aggregation_version,
    benchmark_count_pullups,
    benchmark_count_run,
    avg_pullup_max_reps,
    avg_run_pace_min_per_km,
    notes
)
SELECT
    phase_id,
    1,
    benchmark_count_pullups,
    benchmark_count_run,
    avg_pullup_max_reps,
    avg_run_pace_min_per_km,
    CASE
        WHEN benchmark_count_pullups < 2 OR benchmark_count_run < 2
            THEN 'Low benchmark count; interpret averages cautiously'
        ELSE 'Sufficient benchmark count'
    END
FROM phase_metrics;
