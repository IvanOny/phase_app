# Phase-Based Training Dashboard Frontend Structure

## Scope
Supported phase tabs must align with backend `phase_type` values:
1. Bench (`bench`)
2. Pull-ups (`pull_ups`)
3. Run (`run`)

Derived metrics are read-only and fetched from `/metrics/*`.
Raw create/update operations use non-metrics endpoints.

---

## 1) Component Hierarchy

```text
TrainingDashboardPage
└── PhaseTabsContainer
    ├── PhaseTabNav
    │   ├── PhaseTabButton (Bench)
    │   ├── PhaseTabButton (Pull-ups)
    │   └── PhaseTabButton (Run)
    └── PhaseTabPanel (active tab)
        ├── BenchPhaseTab
        ├── PullUpsPhaseTab
        └── RunPhaseTab
```

For bench tab (example detail):

```text
BenchPhaseTabContainer
└── BenchPhaseTabView
    ├── BenchPhaseHeader
    │   ├── PhaseMeta
    │   └── ReadinessChip
    ├── HeavyBenchStrengthWidget
    └── BenchVolumeWidget
```

---

## 2) Data Mapping (Domain -> UI)

```ts
type PhaseType = 'bench' | 'pull_ups' | 'run';

type ReadinessInputs = {
  eliteHrvReadiness?: number;      // 0..10
  garminOvernightHrv?: number;     // >= 0
};

interface SessionRaw {
  sessionId: number;
  phaseId: number;
  sessionDate: string;
  sessionType: 'heavy_bench' | 'volume_bench' | 'speed_bench' | 'run' | 'pull' | 'other';
  eliteHrvReadiness?: number;
  garminOvernightHrv?: number;
  notes?: string;
}

interface BenchSummaryMetric {
  sessionId: number;
  source: 'live' | 'snapshot';
  computedAt: string;
  aggregationVersion: number | null;
  topSetE1rmKg?: number;
  benchVolumeKgReps?: number;
}
```

Unsupported readiness fields (must not exist in model/contracts):
- sleep hours
- stress
- soreness
- RPE-based readiness scores

---

## 3) Readiness UI Contract (limited)

Readiness display can only use session HRV fields:
- `eliteHrvReadiness`
- `garminOvernightHrv`

No additional readiness schemas/endpoints are allowed in current contract.

---

## 4) Data Flow

```text
Raw API (/phases, /sessions, /sets, /benchmarks)
  -> state store
  -> selectors
  -> Metrics API (/metrics/*, source default=live)
  -> widget props
```

Rules:
1. Default metrics requests omit `source` and therefore use live computation.
2. Snapshot requests are explicit (`source=snapshot`) and must surface metadata:
   - `computedAt`
   - `aggregationVersion`
   - `source`
3. Raw and derived payloads must not be mixed in write endpoints.

---

## 5) Acceptance checks for frontend alignment

- Tabs exactly match `bench | pull_ups | run`.
- `isTopSet` in API payload maps to DB `is_top_set` (no `topSetFlag`).
- No UI fields for sleep/stress/soreness/RPE readiness.
- Metrics cards show whether data source is `live` or `snapshot` and include metadata.
