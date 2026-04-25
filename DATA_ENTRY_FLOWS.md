# Data Entry Flows

Goal: make logging fast, avoid duplicate typing, and keep benchmark records standardized enough for comparison.

## Design principles (applies to all flows)

- **Single quick-entry surface**: one screen/modal per flow with sensible defaults.
- **Prefill aggressively**: date defaults to today, phase/session inferred from context, recent values suggested.
- **Progressive disclosure**: show only required fields first; optional detail expands on demand.
- **Typed templates**: benchmark type determines fields and validation rules; no free-form schema.
- **Immutable standards, editable notes**: standards are selected from controlled options; notes remain flexible.
- **Save as draft + complete later**: preserve partial entry to minimize interruptions.

---

## 1) Flow: Log a Bench Session (Top Set + Backoff)

### Entry point
1. User taps **Log Bench Session** from phase dashboard (bench phase context already known).
2. System preselects:
   - `phase_id` from current phase context.
   - `session_date` = today.
   - `session_type` = last bench session type (usually `heavy` or `volume`).

### Step-by-step flow
1. **Session header (minimal required)**
   - Confirm `session_date`.
   - Confirm `session_type`.
   - Optional readiness fields collapsed by default.
   - Tap **Continue**.
2. **Top set capture (required block)**
   - Exercise auto-selected to canonical barbell bench press.
   - Enter only `top_set_load_kg` and `top_set_reps`.
   - `top_set_flag` auto-set to true.
   - Live preview shows computed e1RM (read-only) for immediate feedback.
3. **Backoff capture (fast repeat block)**
   - User selects one backoff mode:
     - **Same reps, drop load** (common)
     - **Same load, change reps**
     - **Custom per set**
   - User enters either:
     - set count + load/reps template, or
     - individual sets (only if custom).
   - System auto-numbers sets and marks `is_working_set=true`.
4. **Review + save**
   - Compact summary card: top set + backoff total volume.
   - User taps **Save Session**.
   - System writes session, session exercise, and set rows in one transaction.

### Anti-friction + anti-redundancy rules
- Do not ask for exercise name for this flow; it is fixed to bench.
- Backoff sets can be generated from one template input.
- Reuse previous session defaults (plate increments, common reps).
- If user came from an existing session, skip header step and append data inline.

### Standardization rules
- Exactly one set must have `top_set_flag=true`.
- Top set must be working set and must include valid `load_kg` and `reps`.
- Bench flow always maps to the canonical bench exercise ID (`is_barbell_bench_press=true`).
- All loads in kg (UI can convert from lb, but stored as kg).

---

## 2) Flow: Log a Pull-up Benchmark

### Entry point
1. User taps **Log Benchmark** and picks **Max Bodyweight Pull-ups**.
2. System preloads benchmark template with strict pull-up standard version.

### Step-by-step flow
1. **Benchmark header (required)**
   - `phase_id` inferred from active phase (editable if needed).
   - `benchmark_date` default today.
   - Optional link to `session_id` if benchmark occurred during a logged session.
2. **Result entry (required)**
   - Enter `reps` only.
   - `unit` auto-fixed to `reps` (hidden or read-only).
3. **Standard confirmation (required)**
   - Select `form_standard_version` (default latest, e.g., `v1.0`).
   - Optional checkbox: “Paused dead hang + full chin-over-bar achieved each rep.”
4. **Review + save**
   - Summary: date, reps, standard version.
   - Tap **Save Benchmark**.

### Anti-friction + anti-redundancy rules
- Single primary input (`reps`) for outcome.
- Reuse last used standard version unless user changes it.
- Session link is optional and suggested automatically if a same-day session exists.

### Standardization rules
- `benchmark_type` fixed to `max_bodyweight_pullups`.
- `unit` must always be `reps`.
- `reps > 0`.
- Store a standard version on every benchmark to preserve comparability over time.

---

## 3) Flow: Log a Run Benchmark

### Entry point
1. User taps **Log Benchmark** and picks **Run Aerobic Test**.
2. System opens the aerobic run template (target HR + duration controlled).

### Step-by-step flow
1. **Benchmark header (required)**
   - `phase_id` inferred.
   - `benchmark_date` default today.
   - Optional `session_id` association.
2. **Protocol setup (required, prefilled)**
   - `target_hr` default 140.
   - `duration_min` default 40.
   - User can edit only if a non-standard protocol was intentionally used.
3. **Result capture (required)**
   - Enter `avg_hr`.
   - Enter either:
     - `pace_sec_per_km`, or
     - distance + elapsed time (system converts to pace).
4. **Protocol compliance check (required)**
   - Quick toggle: “Protocol completed continuously without interruptions.”
   - If false, save allowed but flagged as `non_standard` for filtering.
5. **Review + save**
   - Summary card includes protocol + resulting pace.
   - Tap **Save Benchmark**.

### Anti-friction + anti-redundancy rules
- Defaults encode standard protocol; most entries only require avg HR + pace.
- Accept watch-native inputs (distance/time) and auto-convert.
- Same-day session linking suggested automatically.

### Standardization rules
- `benchmark_type` fixed to `run_aerobic_test`.
- Required numeric constraints: `target_hr > 0`, `duration_min > 0`, `avg_hr > 0`, `pace_sec_per_km > 0`.
- Keep protocol metadata (target HR, duration) with every record to separate standard vs custom tests.

---

## Field definitions

## Shared/session-level fields

| Field | Type | Required | Auto/Preset | Validation | Notes |
|---|---|---:|---|---|---|
| `phase_id` | integer | Yes | Inferred from active phase | Must exist | Editable only when cross-phase logging is enabled |
| `session_id` | integer | No | Suggested from same-day session | Must exist if provided | Links benchmark to a workout context |
| `session_date` | date (ISO) | Yes (session flow) | Defaults to today | Valid date | Stored as source-of-truth session date |
| `session_type` | enum | Yes (session flow) | Last used in phase | `heavy \| volume \| run \| pull \| other` | Bench flow usually `heavy`/`volume` |
| `notes` | text | No | Blank | Any text | Optional user context |

## Bench session fields

| Field | Type | Required | Auto/Preset | Validation | Notes |
|---|---|---:|---|---|---|
| `exercise_id` | integer | Yes | Canonical bench exercise | Must reference bench exercise | Hidden in quick flow |
| `top_set_load_kg` | decimal | Yes | Last top-set load suggestion | `>= 0` | Can support lb input with conversion |
| `top_set_reps` | integer | Yes | Last used reps suggestion | `> 0` | Drives e1RM preview |
| `top_set_flag` | boolean | Yes | True for selected top set | Exactly one true in session exercise | Enforced at save |
| `backoff_set_count` | integer | Conditional | Suggested from recent pattern | `> 0` when template mode used | Generates repeated sets |
| `backoff_load_kg` | decimal | Conditional | Derived from top set or prior pattern | `>= 0` | Required in template modes |
| `backoff_reps` | integer | Conditional | Derived from top set or prior pattern | `> 0` | Required in template modes |
| `is_working_set` | boolean | Yes | True by default | Boolean | Warmups can be added outside quick flow |

## Pull-up benchmark fields

| Field | Type | Required | Auto/Preset | Validation | Notes |
|---|---|---:|---|---|---|
| `benchmark_date` | date (ISO) | Yes | Today | Valid date | |
| `benchmark_type` | enum | Yes | `max_bodyweight_pullups` | Fixed value | Hidden/read-only |
| `reps` | integer | Yes | Empty | `> 0` | Primary outcome field |
| `unit` | text | Yes | `reps` | Must equal `reps` | Hidden/read-only |
| `form_standard_version` | text | Yes | Latest standard | Non-empty | Critical for comparability |
| `notes` | text | No | Blank | Any text | Capture anomalies |

## Run benchmark fields

| Field | Type | Required | Auto/Preset | Validation | Notes |
|---|---|---:|---|---|---|
| `benchmark_date` | date (ISO) | Yes | Today | Valid date | |
| `benchmark_type` | enum | Yes | `run_aerobic_test` | Fixed value | Hidden/read-only |
| `target_hr` | integer | Yes | 140 | `> 0` | Standard protocol anchor |
| `duration_min` | integer | Yes | 40 | `> 0` | Standard protocol anchor |
| `avg_hr` | decimal | Yes | Empty | `> 0` | From wearable/manual entry |
| `pace_sec_per_km` | decimal | Yes* | Derived or entered | `> 0` | *Required final stored metric |
| `distance_km` | decimal | Optional input path | Empty | `> 0` if provided | Used to compute pace |
| `elapsed_sec` | integer | Optional input path | Empty | `> 0` if provided | Used to compute pace |
| `protocol_compliant` | boolean | Yes | True | Boolean | False flags as non-standard |
| `notes` | text | No | Blank | Any text | Explain conditions/environment |

---

## Recommended UX safeguards

- **Duplicate detection**: warn if same benchmark type already logged on same date in same phase.
- **Unit-locking**: hide units when fixed by standard (`reps`, sec/km).
- **Validation timing**: inline validation while typing; hard-stop only on save.
- **Smart confirmation**: if value deviates greatly from recent history, ask for confirm (not block).
- **Standard filterability**: all analytics views should allow filtering to `protocol_compliant=true` and matching standard version.
