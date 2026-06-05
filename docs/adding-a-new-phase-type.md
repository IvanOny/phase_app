# Adding a New Phase Type — Reference Checklist

Use this whenever implementing a new phase type (e.g. `olympic_lifting`, `marathon`).
Every item here was discovered the hard way when adding `powerlifting` in Phase 2.

---

## 1. Database (run migrations against Supabase)

- Add the new type to the `phases_phase_type_check` constraint:
  ```sql
  ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_phase_type_check;
  ALTER TABLE phases ADD CONSTRAINT phases_phase_type_check
    CHECK (phase_type IN ('bench', 'pull_ups', 'run', 'powerlifting', 'NEW_TYPE'));
  ```
- If the new type has a nullable `end_date` (open-ended phase), relax `phases_check`:
  ```sql
  ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_check;
  ALTER TABLE phases ADD CONSTRAINT phases_end_date_required
    CHECK (end_date IS NOT NULL OR phase_type IN ('powerlifting', 'NEW_TYPE'));
  ```
- Add any phase-specific tables or columns (e.g. `bodyweight_log`, `confirmed_1rm`,
  `is_squat`/`is_deadlift` on exercises).

---

## 2. Backend — `phase_app/api.py`

- `create_phase()`: relax the `endDate` required check if the new type is open-ended.
- `_handle()` dispatcher: add routes for any new phase-specific endpoints.
- `list_exercises` / `create_exercise` / `update_exercise`: add new exercise flags if needed.
- Add handler methods for new routes.

---

## 3. Frontend — Static config tables (most commonly missed)

These are hardcoded lookup objects that must be updated in every new phase type:

| File | Object | Action |
|---|---|---|
| `frontend/src/components/Dashboard/PhaseNav.jsx` | `TYPE_CONFIG` | Add `{ label, color }` entry |
| `frontend/src/components/Dashboard/PhaseNav.jsx` | `TYPE_ORDER` | Add type to display order |
| `frontend/src/components/Dashboard/PhaseHeader.jsx` | `PHASE_LABELS` | Add human-readable name |
| `frontend/src/components/DataEntry/CreatePhaseForm.jsx` | `PHASE_TYPES` | Add to dropdown |
| `frontend/src/components/DataEntry/LogSessionForm.jsx` | `SESSION_TYPES` | Add any new session types |

---

## 4. Frontend — Null/optional field guards

If the new phase type relaxes a previously required field:

- `end_date` nullable → guard `PhaseHeader.jsx`:
  - `daysRemaining()` must return `null` for missing endDate (not NaN)
  - `phaseState` must treat `null` daysLeft as `'current'`
  - Progress bar and date display must skip rendering when endDate is absent
- Any new numeric field used in arithmetic → guard before calculation

---

## 5. Frontend — Dashboard routing

If the new phase type needs its own layout:

1. Create `frontend/src/components/<PhaseName>/` with a dashboard component.
2. In `Dashboard.jsx`, add an early-return before the standard render:
   ```jsx
   if (selectedPhase?.phaseType === 'new-type') {
     return <NewDashboard phases={phases} selectedPhase={selectedPhase} sessions={sessions} ... />;
   }
   ```
3. Pass all standard props: phases, sessions, exercises, exerciseVolumes, all auth props, all callbacks.

---

## 6. Frontend — API client (`frontend/src/api/client.js`)

- Add fetch functions for any new backend endpoints.
- Add `MOCK_MODE` fallbacks returning empty/null data.

---

## 7. Resilience — `App.jsx` `loadPhaseData`

Any call added to the `Promise.all` in `loadPhaseData` **must** have `.catch(() => fallback)`.
An unhandled rejection silently leaves the entire app blank — no error, no loading state.

```js
const [sessions, exerciseVolumes, runBenchmarks, progression] = await Promise.all([
  getSessionsByPhase(phaseId),
  getPhaseExerciseVolumes(phaseId),
  getRunBenchmarks(phaseId).catch(() => []),        // <-- required
  getPhaseProgression(phaseId).catch(() => []),     // <-- required
]);
```

---

## 8. Content

- `frontend/src/components/Faq/FaqPage.jsx`: add a category explaining the new phase,
  its session types, metrics, and any classification or scoring systems.
- `CLAUDE.md`: update architecture notes if the phase introduces new DB tables or patterns.

---

## Quick checklist

```
[ ] SQL: add type to phases_phase_type_check
[ ] SQL: relax end_date constraint if open-ended
[ ] SQL: new tables/columns if needed
[ ] api.py: create_phase validation
[ ] api.py: new routes + handlers
[ ] api.py: exercise flag support if needed
[ ] PhaseNav.jsx: TYPE_CONFIG + TYPE_ORDER
[ ] PhaseHeader.jsx: PHASE_LABELS + null-guard optional fields
[ ] CreatePhaseForm.jsx: PHASE_TYPES array
[ ] LogSessionForm.jsx: SESSION_TYPES array
[ ] Dashboard.jsx: routing branch (if custom layout needed)
[ ] New dashboard component (if custom layout needed)
[ ] client.js: new API functions with MOCK_MODE fallbacks
[ ] App.jsx: .catch() guards on any new loadPhaseData calls
[ ] FaqPage.jsx: documentation
```
