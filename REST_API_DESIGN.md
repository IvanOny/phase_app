# Phase App REST API Design

Base path: `/v1`

Design principle:
- Raw endpoints persist source-of-truth records.
- Metrics endpoints compute **live by default**.
- Snapshot metrics are optional and explicit via `source=snapshot`.

Naming convention:
- DB: `snake_case`
- API JSON: `camelCase`

---

## 1) Endpoint list

## Health
- `GET /health`

## Raw data endpoints
- `POST /phases`
- `GET /phases`
- `GET /phases/{phaseId}`
- `PATCH /phases/{phaseId}`
- `DELETE /phases/{phaseId}`

- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{sessionId}`
- `PATCH /sessions/{sessionId}`
- `DELETE /sessions/{sessionId}`

- `POST /exercises`
- `GET /exercises`
- `GET /exercises/{exerciseId}`

- `POST /sessions/{sessionId}/exercises`
- `GET /sessions/{sessionId}/exercises`
- `PATCH /sessions/{sessionId}/exercises/{sessionExerciseId}`
- `DELETE /sessions/{sessionId}/exercises/{sessionExerciseId}`

- `POST /session-exercises/{sessionExerciseId}/sets`
- `GET /session-exercises/{sessionExerciseId}/sets`
- `PATCH /session-exercises/{sessionExerciseId}/sets/{exerciseSetId}`
- `DELETE /session-exercises/{sessionExerciseId}/sets/{exerciseSetId}`

- `POST /benchmarks`
- `GET /benchmarks`
- `GET /benchmarks/{benchmarkId}`
- `PATCH /benchmarks/{benchmarkId}`
- `DELETE /benchmarks/{benchmarkId}`

## Computed endpoints (read-only)
- `GET /metrics/sessions/{sessionId}/bench-top-set-e1rm`
- `GET /metrics/sessions/{sessionId}/bench-volume`
- `GET /metrics/phases/{phaseId}/summary?source=live|snapshot`

Rules:
- `source` defaults to `live`.
- If `source=snapshot`, response must include snapshot metadata:
  - `computedAt`
  - `aggregationVersion`
  - `source`

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
  "createdAt": "2026-04-25T12:00:00Z"
}
```

## 2.2 Create session (readiness limited to HRV fields)

### Request
`POST /v1/sessions`
```json
{
  "phaseId": 42,
  "sessionDate": "2026-02-14",
  "sessionType": "heavy_bench",
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
  "sessionType": "heavy_bench",
  "eliteHrvReadiness": 7.4,
  "garminOvernightHrv": 58.2,
  "notes": "Felt strong",
  "createdAt": "2026-04-25T12:01:00Z"
}
```

## 2.3 Create run benchmark with protocol compliance + distance/time path

### Request
`POST /v1/benchmarks`
```json
{
  "phaseId": 42,
  "sessionId": 901,
  "benchmarkDate": "2026-02-14",
  "benchmarkType": "run_aerobic_test",
  "details": {
    "targetHr": 140,
    "durationMin": 40,
    "avgHr": 138,
    "distanceKm": 7.1,
    "elapsedSec": 2400,
    "protocolCompliant": true
  }
}
```

## 2.4 Create pull-up benchmark with required standard version

### Request
`POST /v1/benchmarks`
```json
{
  "phaseId": 42,
  "benchmarkDate": "2026-02-21",
  "benchmarkType": "max_bodyweight_pullups",
  "details": {
    "reps": 22,
    "unit": "reps",
    "formStandardVersion": "v1.0"
  }
}
```

## 2.5 Live phase summary (default)

### Request
`GET /v1/metrics/phases/42/summary`

### Response (200)
```json
{
  "phaseId": 42,
  "source": "live",
  "computedAt": "2026-04-25T12:11:00Z",
  "aggregationVersion": null,
  "metrics": {
    "benchmarkCountPullups": 3,
    "benchmarkCountRun": 2,
    "avgPullupMaxReps": 20.5,
    "avgRunPaceMinPerKm": 5.46
  }
}
```

## 2.6 Snapshot phase summary

### Request
`GET /v1/metrics/phases/42/summary?source=snapshot`

### Response (200)
```json
{
  "phaseId": 42,
  "source": "snapshot",
  "computedAt": "2026-04-24T23:59:59Z",
  "aggregationVersion": 7,
  "metrics": {
    "benchmarkCountPullups": 3,
    "benchmarkCountRun": 2,
    "avgPullupMaxReps": 20.5,
    "avgRunPaceMinPerKm": 5.46
  }
}
```

---

## 3) Validation rules

## 3.1 Phases
- `phaseType` in: `bench | pull_ups | run`.
- `endDate >= startDate`.

## 3.2 Sessions
- `sessionType` in: `heavy_bench | volume_bench | speed_bench | run | pull | other`.
- `sessionDate` must be inside linked phase window.
- Readiness only supports:
  - `eliteHrvReadiness` (`0..10` or null)
  - `garminOvernightHrv` (`>=0` or null)

## 3.3 Sets
- `isTopSet` (camelCase in API) maps to DB `is_top_set`.
- At most one `isTopSet=true` per `sessionExerciseId`.

## 3.4 Benchmarks
- Pull-up benchmark requires `formStandardVersion` (non-empty).
- Run benchmark requires either:
  - `paceMinPerKm`, OR
  - both `distanceKm` and `elapsedSec`.
- `protocolCompliant` required for run benchmark.
- Benchmark subtype payload must match `benchmarkType`.

## 3.5 Metrics
- Live by default.
- Snapshot only if explicitly requested.
- Responses include metadata:
  - `computedAt`, `aggregationVersion`, `source`.

---

## 4) Out-of-scope readiness
- No sleep/stress/soreness/RPE models or endpoints.
- Any readiness UI logic must use only:
  - `eliteHrvReadiness`
  - `garminOvernightHrv`
