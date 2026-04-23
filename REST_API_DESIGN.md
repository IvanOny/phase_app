# Phase App REST API Design

Base path: `/v1`

Design principle:
- **Raw data endpoints** persist only source-of-truth records (`phases`, `sessions`, `exercises`, `benchmarks`, and benchmark detail rows).
- **Computed endpoints** are read-only and compute metrics at request time from raw tables (no precomputed storage required).

---

## 1) Endpoint list

## Health
- `GET /health`

## Raw data: Phases (CRUD)
- `POST /phases`
- `GET /phases`
- `GET /phases/{phaseId}`
- `PATCH /phases/{phaseId}`
- `DELETE /phases/{phaseId}`

## Raw data: Sessions (CRUD)
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{sessionId}`
- `PATCH /sessions/{sessionId}`
- `DELETE /sessions/{sessionId}`

## Raw data: Exercises (CRUD)
- `POST /exercises`
- `GET /exercises`
- `GET /exercises/{exerciseId}`
- `PATCH /exercises/{exerciseId}`
- `DELETE /exercises/{exerciseId}`

## Raw data: Benchmarks (CRUD)
- `POST /benchmarks`
- `GET /benchmarks`
- `GET /benchmarks/{benchmarkId}`
- `PATCH /benchmarks/{benchmarkId}`
- `DELETE /benchmarks/{benchmarkId}`

## Raw data: Session exercise structure and sets (needed to compute metrics)
- `POST /sessions/{sessionId}/exercises`
- `GET /sessions/{sessionId}/exercises`
- `PATCH /sessions/{sessionId}/exercises/{sessionExerciseId}`
- `DELETE /sessions/{sessionId}/exercises/{sessionExerciseId}`
- `POST /session-exercises/{sessionExerciseId}/sets`
- `GET /session-exercises/{sessionExerciseId}/sets`
- `PATCH /session-exercises/{sessionExerciseId}/sets/{exerciseSetId}`
- `DELETE /session-exercises/{sessionExerciseId}/sets/{exerciseSetId}`

## Computed data (read-only, no persisted aggregates)
- `GET /metrics/sessions/{sessionId}/bench-top-set-e1rm`
- `GET /metrics/sessions/{sessionId}/bench-volume`
- `GET /metrics/phases/{phaseId}/summary`
- `GET /metrics/phases/{phaseId}/benchmark-counts`
- `GET /metrics/sessions/{sessionId}/readiness-color`
- `GET /metrics/phases/{phaseId}/timeseries?metric=bench_e1rm|bench_volume|readiness`

---

## 2) Request/response examples

## 2.1 Create phase

### Request
`POST /v1/phases`
```json
{
  "phaseType": "bench",
  "startDate": "2026-01-01",
  "endDate": "2026-03-31",
  "name": "Q1 Bench Focus",
  "notes": "High specificity block"
}
```

### Response (201)
```json
{
  "phaseId": 42,
  "phaseType": "bench",
  "startDate": "2026-01-01",
  "endDate": "2026-03-31",
  "name": "Q1 Bench Focus",
  "notes": "High specificity block",
  "createdAt": "2026-04-23T12:00:00Z"
}
```

## 2.2 Create session

### Request
`POST /v1/sessions`
```json
{
  "phaseId": 42,
  "sessionDate": "2026-02-14",
  "sessionType": "heavy",
  "eliteHrvReadiness": 7.4,
  "garminOvernightHrv": 58.2,
  "notes": "Felt strong"
}
```

### Response (201)
```json
{
  "sessionId": 901,
  "phaseId": 42,
  "sessionDate": "2026-02-14",
  "sessionType": "heavy",
  "eliteHrvReadiness": 7.4,
  "garminOvernightHrv": 58.2,
  "notes": "Felt strong",
  "createdAt": "2026-04-23T12:01:00Z"
}
```

## 2.3 Create exercise

### Request
`POST /v1/exercises`
```json
{
  "exerciseName": "Barbell Bench Press",
  "isBarbellBenchPress": true,
  "isBodyweight": false
}
```

### Response (201)
```json
{
  "exerciseId": 12,
  "exerciseName": "Barbell Bench Press",
  "isBarbellBenchPress": true,
  "isBodyweight": false,
  "createdAt": "2026-04-23T12:02:00Z"
}
```

## 2.4 Create benchmark (polymorphic payload)

### Request: pull-up benchmark
`POST /v1/benchmarks`
```json
{
  "phaseId": 42,
  "sessionId": 901,
  "benchmarkDate": "2026-02-14",
  "benchmarkType": "max_bodyweight_pullups",
  "notes": "Strict form",
  "details": {
    "reps": 22,
    "unit": "reps",
    "formStandardVersion": "v1.0"
  }
}
```

### Response (201)
```json
{
  "benchmarkId": 3001,
  "phaseId": 42,
  "sessionId": 901,
  "benchmarkDate": "2026-02-14",
  "benchmarkType": "max_bodyweight_pullups",
  "notes": "Strict form",
  "details": {
    "reps": 22,
    "unit": "reps",
    "formStandardVersion": "v1.0"
  },
  "createdAt": "2026-04-23T12:03:00Z"
}
```

## 2.5 Add session exercise and sets (raw training execution)

### Request
`POST /v1/sessions/901/exercises`
```json
{
  "exerciseId": 12,
  "exerciseOrder": 1,
  "notes": "Comp grip"
}
```

### Response (201)
```json
{
  "sessionExerciseId": 777,
  "sessionId": 901,
  "exerciseId": 12,
  "exerciseOrder": 1,
  "notes": "Comp grip",
  "createdAt": "2026-04-23T12:05:00Z"
}
```

### Request
`POST /v1/session-exercises/777/sets`
```json
{
  "setNumber": 1,
  "reps": 5,
  "loadKg": 120.0,
  "topSetFlag": true,
  "isWorkingSet": true
}
```

### Response (201)
```json
{
  "exerciseSetId": 9901,
  "sessionExerciseId": 777,
  "setNumber": 1,
  "reps": 5,
  "loadKg": 120.0,
  "topSetFlag": true,
  "isWorkingSet": true,
  "createdAt": "2026-04-23T12:06:00Z"
}
```

## 2.6 Computed metric: bench top-set e1RM for a session

### Request
`GET /v1/metrics/sessions/901/bench-top-set-e1rm`

### Response (200)
```json
{
  "sessionId": 901,
  "phaseId": 42,
  "sessionDate": "2026-02-14",
  "topSet": {
    "exerciseSetId": 9901,
    "reps": 5,
    "loadKg": 120.0,
    "e1rmKg": 140.0,
    "formula": "epley"
  },
  "computedAt": "2026-04-23T12:10:00Z"
}
```

## 2.7 Computed metric: phase summary

### Request
`GET /v1/metrics/phases/42/summary`

### Response (200)
```json
{
  "phaseId": 42,
  "phaseType": "bench",
  "averages": {
    "benchTopsetE1rmKg": 138.52,
    "benchSessionVolumeKgReps": 4120.75,
    "pullupMaxReps": 20.5,
    "runPaceSecPerKm": 327.8
  },
  "counts": {
    "benchmarkPullups": 3,
    "benchmarkRun": 2,
    "benchmarkTotal": 5
  },
  "computedAt": "2026-04-23T12:11:00Z"
}
```

## 2.8 Computed metric: readiness color

### Request
`GET /v1/metrics/sessions/901/readiness-color`

### Response (200)
```json
{
  "sessionId": 901,
  "eliteHrvReadiness": 7.4,
  "readinessColor": "yellow",
  "thresholds": {
    "green": ">=7.5",
    "yellow": ">=5.0 and <7.5",
    "red": "<5.0",
    "gray": "missing"
  },
  "computedAt": "2026-04-23T12:12:00Z"
}
```

---

## 3) Basic validation rules

## 3.1 Common
- `Content-Type` must be `application/json` for write endpoints.
- IDs in path params are positive integers.
- Unknown enum values return `422 Unprocessable Entity`.
- Standard error shape:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "phaseType must be one of [bench, pull_ups, run]",
    "details": [{"field": "phaseType", "issue": "invalid_enum"}]
  }
}
```

## 3.2 Phases
- `phaseType` in: `bench | pull_ups | run`.
- `startDate` and `endDate` are valid ISO dates.
- `endDate >= startDate`.
- `(phaseType, startDate, endDate)` must be unique.

## 3.3 Sessions
- `phaseId` must reference an existing phase.
- `sessionType` in: `heavy | volume | run | pull | other`.
- Unique per `(phaseId, sessionDate, sessionType)`.
- `eliteHrvReadiness` either null or `0..10`.
- `garminOvernightHrv` either null or `>= 0`.

## 3.4 Exercises
- `exerciseName` required, non-empty, unique (case-insensitive normalization recommended).
- `isBarbellBenchPress` and `isBodyweight` are booleans.

## 3.5 Session exercises and sets
- Session exercise:
  - `sessionId` and `exerciseId` must exist.
  - `exerciseOrder > 0` and unique within a session.
- Set:
  - `setNumber > 0` and unique per `sessionExerciseId`.
  - `reps > 0`.
  - `loadKg >= 0`.
  - `topSetFlag` and `isWorkingSet` booleans.

## 3.6 Benchmarks
- `phaseId` required and must exist.
- `sessionId` optional but if provided must exist.
- `benchmarkType` in: `max_bodyweight_pullups | run_aerobic_test`.
- `details` must match type:
  - For `max_bodyweight_pullups`: `reps > 0`, `unit == "reps"`.
  - For `run_aerobic_test`: `targetHr > 0`, `durationMin > 0`, `avgHr > 0`, `paceSecPerKm > 0`.

## 3.7 Computed endpoints
- Read-only; only `GET` allowed.
- Accept filters/pagination but never persist returned values.
- If required raw inputs are absent (e.g., no top set), return `404` with domain code like `METRIC_NOT_AVAILABLE` rather than fabricating defaults.

---

## 4) Resource shape separation (raw vs computed)

To enforce clean separation:
- Raw resources (`/phases`, `/sessions`, `/exercises`, `/benchmarks`, `/session-exercises`, `/sets`) contain only persisted columns.
- Computed resources live only under `/metrics/*` and include `computedAt` and optional `formula` metadata.
- Raw `GET` endpoints must not inline derived aggregates by default.
- If a client needs both raw + computed, it calls both endpoint groups explicitly.
