# Phase-Based Training Dashboard Frontend Structure

## Scope
This structure focuses on a single **Bench** phase tab with three widgets:
1. Heavy Bench Strength (e1RM trend)
2. Bench Volume
3. Maintenance (pull-ups + run)

It intentionally avoids styling details and focuses on component structure, data mapping, and data flow.

---

## 1) Component Hierarchy

```text
TrainingDashboardPage
└── PhaseTabsContainer
    ├── PhaseTabNav
    │   ├── PhaseTabButton (Bench)
    │   ├── PhaseTabButton (Squat)
    │   └── PhaseTabButton (Deadlift)
    └── PhaseTabPanel (active: Bench)
        └── BenchPhaseTab
            ├── BenchPhaseHeader
            │   ├── PhaseMeta (name, dates, week index)
            │   └── ReadinessChip (overall readiness color + label)
            ├── BenchWidgetsGrid
            │   ├── HeavyBenchStrengthWidget
            │   │   ├── WidgetHeader
            │   │   ├── E1RMTrendChart
            │   │   └── StrengthSummary
            │   ├── BenchVolumeWidget
            │   │   ├── WidgetHeader
            │   │   ├── WeeklyVolumeChart
            │   │   └── VolumeSummary
            │   └── MaintenanceWidget
            │       ├── WidgetHeader
            │       ├── PullUpsPanel
            │       │   ├── PullUpsCompletionBar
            │       │   └── PullUpsSummary
            │       ├── RunPanel
            │       │   ├── RunCompletionBar
            │       │   └── RunSummary
            │       └── MaintenanceSummary
            └── BenchPhaseFooter
                └── LastUpdatedStamp
```

### Container/Presentation split (recommended)

```text
BenchPhaseTabContainer
└── BenchPhaseTabView
    ├── HeavyBenchStrengthWidgetContainer -> HeavyBenchStrengthWidgetView
    ├── BenchVolumeWidgetContainer -> BenchVolumeWidgetView
    └── MaintenanceWidgetContainer -> MaintenanceWidgetView
```

- `*Container` components:
  - Fetch/select state
  - Map API/domain data to view model
  - Compute readiness status
- `*View` components:
  - Pure rendering from props
  - No data access side effects

---

## 2) Data Mapping (Domain -> UI)

## Bench tab source model (example)

```ts
interface BenchPhaseData {
  phase: {
    id: string;
    name: 'Bench';
    startDate: string;
    endDate: string;
    currentWeek: number;
    totalWeeks: number;
  };
  heavyBench: {
    sessions: Array<{
      date: string;
      topSetKg: number;
      reps: number;
      rpe?: number;
      e1rmKg: number;
    }>;
    baselineE1rmKg: number;
    targetE1rmKg?: number;
  };
  volume: {
    weekly: Array<{
      weekIndex: number;
      totalReps: number;
      totalSets: number;
      avgIntensityPct: number;
      tonnageKg: number;
    }>;
    targetRepRange: { min: number; max: number };
  };
  maintenance: {
    pullUps: {
      weeklyTargetReps: number;
      completedReps: number;
      sessions: Array<{ date: string; reps: number }>;
    };
    run: {
      weeklyTargetKm: number;
      completedKm: number;
      sessions: Array<{ date: string; distanceKm: number; paceSecPerKm?: number }>;
    };
  };
  readinessInputs: {
    soreness: number; // 1-5
    sleepHours: number;
    stress: number; // 1-5
    restingHrDelta?: number;
    sessionRpeAvg7d?: number;
  };
  updatedAt: string;
}
```

## Widget prop mapping

### A) Heavy Bench Strength (e1RM trend)
- **Chart series**: `heavyBench.sessions[].e1rmKg`
- **X-axis**: `heavyBench.sessions[].date`
- **Current e1RM**: last session `e1rmKg`
- **Trend delta**: last 7-14 day slope or `current - baselineE1rmKg`
- **Goal progress** (if target exists): `(current - baseline) / (target - baseline)`

### B) Bench Volume
- **Chart series**: `volume.weekly[].totalReps` (or tonnage)
- **X-axis**: `volume.weekly[].weekIndex`
- **Target band**: `volume.targetRepRange.min/max`
- **Current week value**: latest `totalReps`
- **Volume status**:
  - below target
  - in range
  - above target

### C) Maintenance (pull-ups + run)
- **Pull-ups completion %**: `completedReps / weeklyTargetReps`
- **Run completion %**: `completedKm / weeklyTargetKm`
- **Maintenance combined score** (example):
  - `0.5 * clamp(pullUpsCompletion,0,1) + 0.5 * clamp(runCompletion,0,1)`
- **Widget summary**: show each modality status + combined status

---

## 3) Readiness Color Logic

Readiness should be computed once in a shared selector/hook and consumed by header + widgets.

## Shared readiness enum

```ts
type ReadinessColor = 'green' | 'yellow' | 'red';
```

## Example scoring model

```ts
interface ReadinessScore {
  score: number; // 0-100
  color: ReadinessColor;
  reasons: string[];
}
```

### Score inputs (example weighting)
- Sleep adequacy (30%)
- Soreness (25%)
- Stress (20%)
- Resting HR delta (15%)
- Recent session strain / avg RPE (10%)

### Thresholds
- **Green**: `score >= 75`
- **Yellow**: `50 <= score < 75`
- **Red**: `score < 50`

### Widget-specific readiness usage
- **Heavy Bench Strength widget**:
  - Use `color` as intensity guidance indicator (e.g., proceed / moderate / reduce)
- **Bench Volume widget**:
  - In yellow/red, cap recommended volume increase
- **Maintenance widget**:
  - In red, preserve low-impact maintenance targets (e.g., easy run instead of hard effort)

Note: Keep color logic centralized to avoid inconsistent thresholds across widgets.

---

## 4) Data Flow

## High-level flow

```text
API / local cache
  -> dashboardService.getPhaseData('bench')
  -> state store (React Query / Redux / Zustand)
  -> selectors/hooks
     - useBenchPhaseData()
     - useBenchReadiness()
     - useHeavyBenchVM()
     - useBenchVolumeVM()
     - useMaintenanceVM()
  -> BenchPhaseTabContainer
  -> BenchPhaseTabView + Widget Views
```

## Detailed flow by layer

1. **Fetch layer**
   - Request bench phase data from API.
   - Normalize response shape if needed.

2. **State layer**
   - Cache raw phase payload by `phaseId` + date range.
   - Expose loading/error/stale states.

3. **Selector/ViewModel layer**
   - Compute derived values:
     - e1RM trend
     - weekly volume status
     - maintenance completion
     - readiness score + color
   - Return simple UI-focused props.

4. **Presentation layer**
   - Render header + 3 widgets from view models.
   - Trigger no business logic besides UI events.

5. **Interaction layer (optional)**
   - Date range change, week filter, metric toggle events
   - Events update state -> selectors recompute -> widgets rerender

---

## 5) Suggested ViewModel shapes

```ts
interface HeavyBenchStrengthVM {
  title: string;
  points: Array<{ x: string; y: number }>;
  currentE1rmKg: number;
  deltaVsBaselineKg: number;
  readinessColor: ReadinessColor;
  readinessHint: string;
}

interface BenchVolumeVM {
  title: string;
  weeklyBars: Array<{ week: number; reps: number }>;
  targetMin: number;
  targetMax: number;
  latestReps: number;
  status: 'below' | 'in_range' | 'above';
  readinessColor: ReadinessColor;
}

interface MaintenanceVM {
  title: string;
  pullUpsCompletionPct: number;
  runCompletionPct: number;
  combinedScorePct: number;
  status: 'on_track' | 'watch' | 'behind';
  readinessColor: ReadinessColor;
}
```

These VMs make widgets easy to test and keep raw schema changes isolated.
