# Data Entry Flows

Goal: fast manual logging with strong type safety, clean raw-vs-derived separation, and standardized benchmark comparability.

## Core constraints
- Manual input only.
- Raw data capture and derived metrics are separated.
- No phase score workflows.
- Readiness limited to:
  - `elite_hrv_readiness`
  - `garmin_overnight_hrv`

---

## 1) Flow: Log Session + Bench Sets

### Session header
- Required:
  - `phase_id`
  - `session_date`
  - `session_type`
- Optional:
  - `elite_hrv_readiness`
  - `garmin_overnight_hrv`
  - `notes`

### Bench set entry
- Add session exercise row (`exercise_id`, `exercise_order`).
- Add set rows with:
  - `set_number`
  - `reps`
  - `load_kg`
  - `is_top_set`
  - `is_working_set`

### Enforced rules
- `session_date` must be within phase window.
- `set_number` unique per session exercise.
- At most one `is_top_set=true` per session exercise.

---

## 2) Flow: Log Pull-up Benchmark

- `benchmark_type` fixed to `max_bodyweight_pullups`.
- Required details:
  - `reps`
  - `unit` = `reps`
  - `form_standard_version` (required)
- Optional: `session_id`, `notes`.

---

## 3) Flow: Log Run Aerobic Benchmark

- `benchmark_type` fixed to `run_aerobic_test`.
- Required details:
  - `target_hr`
  - `duration_min`
  - `avg_hr`
  - `protocol_compliant`
- Required result path (one of):
  1. `pace_min_per_km`, OR
  2. `distance_km` + `elapsed_sec` (pace derived downstream)

---

## 4) Flow: View Metrics

### Live-by-default metrics
- Use `/metrics/*` without `source` query to compute from raw tables.

### Snapshot metrics (optional)
- Use `source=snapshot` only when cached/snapshotted metrics are explicitly requested.
- Must display metadata:
  - `computed_at`
  - `aggregation_version`
  - `source`

### Separation rule
- Derived outputs are never written back through raw write endpoints.
