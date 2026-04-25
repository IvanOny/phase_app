# Architecture Consistency Review

## 1) Critical issues

1. **Raw vs derived boundary is contradictory**
   - `schema.sql` persists `phase_aggregations` as snapshot-derived data, while `REST_API_DESIGN.md` states computed data is read-only and computed at request time with no persisted aggregates.
   - This creates two competing sources of truth for the same metrics.

2. **Frontend domain does not match backend domain**
   - Frontend tab model uses Bench/Squat/Deadlift, but database `phase_type_enum` only supports `bench`, `pull_ups`, and `run`.
   - Frontend data model includes fields not represented in schema/API (e.g., `rpe`, soreness/stress/sleep readiness inputs, weekly km sessions), so the displayed state cannot be fully sourced from backend.

3. **Data-entry requirements are not representable in schema**
   - Run benchmark flow requires `protocol_compliant` and optional distance/time input path (`distance_km`, `elapsed_sec`) for pace derivation, but no corresponding columns exist.
   - Pull-up flow requires a standard version every time, but `benchmark_pullup_max_reps.form_standard_version` is nullable.

4. **Missing integrity constraints allow invalid states**
   - No enforced constraint that a session date lies within its phase date window.
   - No enforced benchmark subtype/type consistency (only comment mentions optional trigger).
   - No enforced "exactly one top set" (or at least at most one top set) per session exercise.

5. **Redundant/unclear uniqueness on `session_exercises`**
   - `UNIQUE (session_id, exercise_order)` already enforces position uniqueness.
   - Additional `UNIQUE (session_id, exercise_id, exercise_order)` is redundant and does not prevent duplicate exercise rows at different positions.

## 2) Recommended changes

1. **Choose one derived-data strategy and apply everywhere**
   - Preferred: **on-read computation + optional cache table**.
   - Keep `phase_aggregations` only as explicit cache/snapshot, and expose it as `/metrics/phases/{phaseId}/summary?source=live|snapshot`.
   - Document recomputation lifecycle and invalidation triggers.

2. **Unify the domain model across DB/API/frontend**
   - Either:
     - Add `squat` and `deadlift` to phase/session model, or
     - Change frontend tabs to match current supported `bench/pull_ups/run`.
   - Remove frontend-only fields unless backed by API, or add proper tables/endpoints for them.

3. **Add missing raw fields needed by the flows**
   - Add to `benchmark_run_aerobic_test`:
     - `protocol_compliant BOOLEAN NOT NULL DEFAULT TRUE`
     - `distance_km NUMERIC(7,3)`
     - `elapsed_sec INTEGER`
     - CHECK that either `pace_min_per_km` is provided or (`distance_km`,`elapsed_sec`) is provided, with deterministic storage rule.
   - Make `benchmark_pullup_max_reps.form_standard_version NOT NULL`.

4. **Strengthen integrity constraints**
   - Enforce session-in-phase-window via trigger (`sessions.session_date` between phase start/end).
   - Enforce benchmark detail subtype matches `benchmarks.benchmark_type` via constraint trigger.
   - Enforce one top set per `session_exercise_id` with partial unique index:
     - `UNIQUE (session_exercise_id) WHERE top_set_flag = TRUE`.

5. **Clarify naming and semantics**
   - Rename `top_set_flag` -> `is_top_set` and `benchmark_run_aerobic_test` -> `benchmark_run_aerobic` (or similarly concise).
   - Standardize API field names to one style (camelCase externally, snake_case internally).
   - Document canonical units and conversion behavior in API contract (kg, min/km, reps).

## 3) Final corrected version (canonical contract)

### Canonical principles
- **Raw tables are source of truth** (`phases`, `sessions`, `session_exercises`, `exercise_sets`, `benchmarks`, subtype tables).
- **Derived metrics are computed views/services**; optional persisted snapshots are cache-only and explicitly labeled.
- **Every UI field must map to raw API fields or documented derived selectors**.

### Corrected schema contract (high level)
- `phases(phase_type)` must match supported UI tabs exactly.
- `sessions(session_date)` constrained to phase date window.
- `exercise_sets` includes at most one `is_top_set=true` per session exercise.
- `benchmark_pullup_max_reps(form_standard_version NOT NULL)`.
- `benchmark_run_aerobic_test` includes protocol compliance + optional distance/time inputs.
- Benchmark subtype rows must match `benchmarks.benchmark_type`.

### Corrected API contract
- **Raw CRUD** remains on core entities.
- **Metrics endpoints** return live computed data by default.
- If snapshots are retained: add explicit source parameter and snapshot metadata (`computedAt`, `aggregationVersion`, `source`).
- Add validations aligned to DB constraints (single top set, protocol fields, phase window checks).

### Corrected frontend contract
- Tabs and widgets only for supported backend phase types.
- View models only include:
  - Raw fields returned by API, or
  - Derived fields from documented selectors (`e1rmKg`, `benchVolume`, `readinessColor`).
- Any additional readiness inputs (sleep/stress/soreness/RPE) require explicit backend model + endpoint before use as authoritative values.
