-- PostgreSQL schema for phase-based training app
-- Raw tables are source-of-truth.
-- phase_aggregations is an optional snapshot/cache table only.

-- Controlled vocabularies
CREATE TYPE phase_type_enum AS ENUM ('bench', 'pull_ups', 'run');
CREATE TYPE session_type_enum AS ENUM ('heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other');
CREATE TYPE benchmark_type_enum AS ENUM ('max_bodyweight_pullups', 'run_aerobic_test');

-- 1) Phases
CREATE TABLE phases (
    phase_id BIGSERIAL PRIMARY KEY,
    phase_type phase_type_enum NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    name TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_phase_dates CHECK (end_date >= start_date)
);

CREATE UNIQUE INDEX uq_phases_type_date_window
    ON phases (phase_type, start_date, end_date);

-- 2) Sessions
CREATE TABLE sessions (
    session_id BIGSERIAL PRIMARY KEY,
    phase_id BIGINT NOT NULL REFERENCES phases(phase_id) ON DELETE RESTRICT,
    session_date DATE NOT NULL,
    session_type session_type_enum NOT NULL,
    elite_hrv_readiness NUMERIC(4,2),
    garmin_overnight_hrv NUMERIC(6,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_elite_hrv_readiness_range
        CHECK (elite_hrv_readiness IS NULL OR (elite_hrv_readiness >= 0 AND elite_hrv_readiness <= 10)),
    CONSTRAINT chk_garmin_overnight_hrv_nonnegative
        CHECK (garmin_overnight_hrv IS NULL OR garmin_overnight_hrv >= 0),
    CONSTRAINT uq_sessions_phase_date_type UNIQUE (phase_id, session_date, session_type)
);

CREATE INDEX idx_sessions_phase_date
    ON sessions (phase_id, session_date);

-- Enforce session_date inside phase window.
CREATE OR REPLACE FUNCTION trg_validate_session_date_in_phase()
RETURNS trigger AS $$
DECLARE
    v_start DATE;
    v_end DATE;
BEGIN
    SELECT start_date, end_date INTO v_start, v_end
    FROM phases
    WHERE phase_id = NEW.phase_id;

    IF v_start IS NULL THEN
        RAISE EXCEPTION 'phase_id % does not exist', NEW.phase_id;
    END IF;

    IF NEW.session_date < v_start OR NEW.session_date > v_end THEN
        RAISE EXCEPTION 'session_date % must be within phase window [% - %]', NEW.session_date, v_start, v_end;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_session_date_in_phase
BEFORE INSERT OR UPDATE OF phase_id, session_date ON sessions
FOR EACH ROW
EXECUTE FUNCTION trg_validate_session_date_in_phase();

-- 3) Exercise catalog
CREATE TABLE exercises (
    exercise_id BIGSERIAL PRIMARY KEY,
    exercise_name TEXT NOT NULL UNIQUE,
    is_barbell_bench_press BOOLEAN NOT NULL DEFAULT FALSE,
    is_bodyweight BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4) Session exercise entries
CREATE TABLE session_exercises (
    session_exercise_id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    exercise_id BIGINT NOT NULL REFERENCES exercises(exercise_id) ON DELETE RESTRICT,
    exercise_order SMALLINT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_exercise_order_positive CHECK (exercise_order > 0),
    CONSTRAINT uq_session_exercise_order UNIQUE (session_id, exercise_order)
);

CREATE INDEX idx_session_exercises_session
    ON session_exercises (session_id);

-- 5) Set-level execution data (raw)
CREATE TABLE exercise_sets (
    exercise_set_id BIGSERIAL PRIMARY KEY,
    session_exercise_id BIGINT NOT NULL REFERENCES session_exercises(session_exercise_id) ON DELETE CASCADE,
    set_number SMALLINT NOT NULL,
    reps SMALLINT NOT NULL,
    load_kg NUMERIC(7,2) NOT NULL,
    is_top_set BOOLEAN NOT NULL DEFAULT FALSE,
    is_working_set BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_set_number_positive CHECK (set_number > 0),
    CONSTRAINT chk_reps_positive CHECK (reps > 0),
    CONSTRAINT chk_load_nonnegative CHECK (load_kg >= 0),
    CONSTRAINT uq_set_number_per_exercise UNIQUE (session_exercise_id, set_number)
);

CREATE INDEX idx_exercise_sets_session_exercise
    ON exercise_sets (session_exercise_id);

CREATE UNIQUE INDEX uq_exercise_sets_one_top_set
    ON exercise_sets (session_exercise_id)
    WHERE is_top_set = TRUE;

-- 6) Benchmarks (header)
CREATE TABLE benchmarks (
    benchmark_id BIGSERIAL PRIMARY KEY,
    phase_id BIGINT NOT NULL REFERENCES phases(phase_id) ON DELETE RESTRICT,
    session_id BIGINT REFERENCES sessions(session_id) ON DELETE SET NULL,
    benchmark_date DATE NOT NULL,
    benchmark_type benchmark_type_enum NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_benchmarks_phase_date
    ON benchmarks (phase_id, benchmark_date);

CREATE INDEX idx_benchmarks_type
    ON benchmarks (benchmark_type);

-- 7) Pull-up benchmark details
CREATE TABLE benchmark_pullup_max_reps (
    benchmark_id BIGINT PRIMARY KEY REFERENCES benchmarks(benchmark_id) ON DELETE CASCADE,
    reps SMALLINT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'reps',
    form_standard_version TEXT NOT NULL,
    CONSTRAINT chk_pullup_reps_positive CHECK (reps > 0),
    CONSTRAINT chk_pullup_unit_reps CHECK (unit = 'reps')
);

-- 8) Run aerobic benchmark details
CREATE TABLE benchmark_run_aerobic_test (
    benchmark_id BIGINT PRIMARY KEY REFERENCES benchmarks(benchmark_id) ON DELETE CASCADE,
    target_hr SMALLINT NOT NULL DEFAULT 140,
    duration_min SMALLINT NOT NULL DEFAULT 40,
    avg_hr NUMERIC(5,2) NOT NULL,
    pace_min_per_km NUMERIC(7,2),
    distance_km NUMERIC(8,3),
    elapsed_sec INTEGER,
    protocol_compliant BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_target_hr_positive CHECK (target_hr > 0),
    CONSTRAINT chk_duration_min_positive CHECK (duration_min > 0),
    CONSTRAINT chk_avg_hr_positive CHECK (avg_hr > 0),
    CONSTRAINT chk_pace_positive CHECK (pace_min_per_km IS NULL OR pace_min_per_km > 0),
    CONSTRAINT chk_distance_positive CHECK (distance_km IS NULL OR distance_km > 0),
    CONSTRAINT chk_elapsed_positive CHECK (elapsed_sec IS NULL OR elapsed_sec > 0),
    CONSTRAINT chk_run_result_path CHECK (
        pace_min_per_km IS NOT NULL
        OR (distance_km IS NOT NULL AND elapsed_sec IS NOT NULL)
    )
);

-- 9) Phase aggregations cache (derived snapshots only; NOT source-of-truth)
CREATE TABLE phase_aggregations (
    phase_aggregation_id BIGSERIAL PRIMARY KEY,
    phase_id BIGINT NOT NULL REFERENCES phases(phase_id) ON DELETE CASCADE,
    aggregation_version INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'snapshot',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    strength_trend_points INTEGER,
    workload_trend_points INTEGER,
    benchmark_count_pullups INTEGER,
    benchmark_count_run INTEGER,
    avg_pullup_max_reps NUMERIC(6,2),
    avg_run_pace_min_per_km NUMERIC(8,2),
    prev_phase_pullup_delta NUMERIC(8,2),
    prev_phase_run_pace_delta_sec_per_km NUMERIC(8,2),
    notes TEXT,
    CONSTRAINT chk_phase_agg_source CHECK (source IN ('snapshot')),
    CONSTRAINT chk_counts_nonnegative CHECK (
        (benchmark_count_pullups IS NULL OR benchmark_count_pullups >= 0)
        AND (benchmark_count_run IS NULL OR benchmark_count_run >= 0)
    ),
    CONSTRAINT uq_phase_aggregation_version UNIQUE (phase_id, aggregation_version)
);

CREATE INDEX idx_phase_aggregations_phase
    ON phase_aggregations (phase_id, computed_at DESC);

-- 10) Benchmark subtype/type integrity trigger
CREATE OR REPLACE FUNCTION trg_validate_benchmark_subtype_match()
RETURNS trigger AS $$
DECLARE
    v_type benchmark_type_enum;
BEGIN
    SELECT benchmark_type INTO v_type
    FROM benchmarks
    WHERE benchmark_id = NEW.benchmark_id;

    IF v_type IS NULL THEN
        RAISE EXCEPTION 'benchmark_id % does not exist', NEW.benchmark_id;
    END IF;

    IF TG_TABLE_NAME = 'benchmark_pullup_max_reps' AND v_type <> 'max_bodyweight_pullups' THEN
        RAISE EXCEPTION 'benchmark_id % has type %, expected max_bodyweight_pullups', NEW.benchmark_id, v_type;
    END IF;

    IF TG_TABLE_NAME = 'benchmark_run_aerobic_test' AND v_type <> 'run_aerobic_test' THEN
        RAISE EXCEPTION 'benchmark_id % has type %, expected run_aerobic_test', NEW.benchmark_id, v_type;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_pullup_subtype_match
BEFORE INSERT OR UPDATE ON benchmark_pullup_max_reps
FOR EACH ROW
EXECUTE FUNCTION trg_validate_benchmark_subtype_match();

CREATE TRIGGER validate_run_subtype_match
BEFORE INSERT OR UPDATE ON benchmark_run_aerobic_test
FOR EACH ROW
EXECUTE FUNCTION trg_validate_benchmark_subtype_match();
