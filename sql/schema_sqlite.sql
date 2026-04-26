PRAGMA foreign_keys = ON;

CREATE TABLE phases (
    phase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_type TEXT NOT NULL CHECK (phase_type IN ('bench', 'pull_ups', 'run')),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    name TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (end_date >= start_date),
    UNIQUE (phase_type, start_date, end_date)
);

CREATE TABLE sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id INTEGER NOT NULL REFERENCES phases(phase_id) ON DELETE RESTRICT,
    session_date TEXT NOT NULL,
    session_type TEXT NOT NULL CHECK (session_type IN ('heavy_bench', 'volume_bench', 'speed_bench', 'run', 'pull', 'other')),
    elite_hrv_readiness REAL,
    garmin_overnight_hrv REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (elite_hrv_readiness IS NULL OR (elite_hrv_readiness >= 0 AND elite_hrv_readiness <= 10)),
    CHECK (garmin_overnight_hrv IS NULL OR garmin_overnight_hrv >= 0),
    UNIQUE (phase_id, session_date, session_type)
);

CREATE TRIGGER validate_session_date_in_phase
BEFORE INSERT ON sessions
FOR EACH ROW
BEGIN
    SELECT CASE WHEN (
        NEW.session_date < (SELECT start_date FROM phases WHERE phase_id = NEW.phase_id)
        OR NEW.session_date > (SELECT end_date FROM phases WHERE phase_id = NEW.phase_id)
    ) THEN RAISE(ABORT, 'session_date must be within phase window') END;
END;

CREATE TABLE exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_name TEXT NOT NULL UNIQUE,
    is_barbell_bench_press INTEGER NOT NULL DEFAULT 0,
    is_bodyweight INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE session_exercises (
    session_exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(exercise_id) ON DELETE RESTRICT,
    exercise_order INTEGER NOT NULL CHECK (exercise_order > 0),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (session_id, exercise_order)
);

CREATE TABLE exercise_sets (
    exercise_set_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_exercise_id INTEGER NOT NULL REFERENCES session_exercises(session_exercise_id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL CHECK (set_number > 0),
    reps INTEGER NOT NULL CHECK (reps > 0),
    load_kg REAL NOT NULL CHECK (load_kg >= 0),
    is_top_set INTEGER NOT NULL DEFAULT 0,
    is_working_set INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (session_exercise_id, set_number)
);

CREATE UNIQUE INDEX uq_exercise_sets_one_top_set
ON exercise_sets(session_exercise_id)
WHERE is_top_set = 1;

CREATE TABLE benchmarks (
    benchmark_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id INTEGER NOT NULL REFERENCES phases(phase_id) ON DELETE RESTRICT,
    session_id INTEGER REFERENCES sessions(session_id) ON DELETE SET NULL,
    benchmark_date TEXT NOT NULL,
    benchmark_type TEXT NOT NULL CHECK (benchmark_type IN ('max_bodyweight_pullups', 'run_aerobic_test')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE benchmark_pullup_max_reps (
    benchmark_id INTEGER PRIMARY KEY REFERENCES benchmarks(benchmark_id) ON DELETE CASCADE,
    reps INTEGER NOT NULL CHECK (reps > 0),
    unit TEXT NOT NULL DEFAULT 'reps' CHECK (unit = 'reps'),
    form_standard_version TEXT NOT NULL
);

CREATE TABLE benchmark_run_aerobic_test (
    benchmark_id INTEGER PRIMARY KEY REFERENCES benchmarks(benchmark_id) ON DELETE CASCADE,
    target_hr INTEGER NOT NULL DEFAULT 140 CHECK (target_hr > 0),
    duration_min INTEGER NOT NULL DEFAULT 40 CHECK (duration_min > 0),
    avg_hr REAL NOT NULL CHECK (avg_hr > 0),
    pace_min_per_km REAL CHECK (pace_min_per_km IS NULL OR pace_min_per_km > 0),
    distance_km REAL CHECK (distance_km IS NULL OR distance_km > 0),
    elapsed_sec INTEGER CHECK (elapsed_sec IS NULL OR elapsed_sec > 0),
    protocol_compliant INTEGER NOT NULL DEFAULT 1,
    CHECK (pace_min_per_km IS NOT NULL OR (distance_km IS NOT NULL AND elapsed_sec IS NOT NULL))
);

CREATE TABLE phase_aggregations (
    phase_aggregation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id INTEGER NOT NULL REFERENCES phases(phase_id) ON DELETE CASCADE,
    aggregation_version INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'snapshot' CHECK (source IN ('snapshot')),
    computed_at TEXT NOT NULL DEFAULT (datetime('now')),
    benchmark_count_pullups INTEGER,
    benchmark_count_run INTEGER,
    avg_pullup_max_reps REAL,
    avg_run_pace_min_per_km REAL,
    UNIQUE (phase_id, aggregation_version)
);
