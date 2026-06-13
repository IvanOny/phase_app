# Adding a New Phase Type — Reference Checklist

## Questions to ask before building

Before writing any code, ask the user these questions. Do not start implementing until all are answered.

1. **Phase name** — What is the `phase_type` slug? (lowercase, underscores, e.g. `olympic_lifting`)

2. **End date** — Is this phase open-ended (ends when a goal is hit) or does it require a fixed end date?

3. **Session types** — Which session types are relevant for this phase? Current full list:
   `squat`, `deadlift`, `mixed`, `heavy_bench`, `volume_bench`, `speed_bench`, `run`, `pull`, `rest`, `other`
   Which of these apply, and are any new ones needed?

4. **Primary metric** — What is the main thing being tracked? (e.g. e1RM, total kg, distance, reps, time)

5. **Dashboard layout** — Does this phase need its own dashboard, or can it reuse the standard one (e1RM chart + volume chart + sessions list)?

6. **Exercise flags** — Does this phase introduce new exercise classification flags? (e.g. `is_squat`, `is_deadlift`). If yes, new DB columns and migrations are needed.

7. **Classification or scoring** — Is there a target/goal system? (e.g. federation class, distance PR, time goal). If yes, what is the data source for thresholds?

8. **Bodyweight relevance** — Does bodyweight need to be logged per session? (affects scoring, weight categories, etc.)

9. **Phase color** — What color should the phase tab pill use in the nav? (hex or CSS var)

10. **FAQ content** — What should be explained to the user about this phase in the FAQ section?

---



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
| `frontend/src/components/DataEntry/LogSessionForm.jsx` | `SESSION_TYPES_BY_PHASE` | Add entry for new phase type with relevant session types |

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

---

## Bugs found after powerlifting was introduced (append future ones here)

**PhaseCalendar crash on null endDate**
`PhaseCalendar` used `normDate(phase.endDate)` (returns `''`) then passed it to `addDays()` → `new Date('T12:00:00')` → Invalid Date.
Fix: fall back to end of current month when `phase.endDate` is null. Also guard `inPhase` check to skip upper bound when `phase.endDate` is absent.

**DB trigger rejects sessions for open-ended phases (null end_date)**
`check_session_date_in_phase()` did `session_date <= end_date`. When `end_date IS NULL`, the comparison returns NULL (falsy) and the trigger raises. Fix: skip the end_date check when `end_date IS NULL`. Requires `CREATE OR REPLACE FUNCTION` migration.

**SessionsList shows wrong session type filter chips for new phase**
`SESSION_TYPES` was hardcoded to bench-specific types. Fix: define per-phase-type arrays (`SESSION_TYPES_PL`, etc.) and pass `sessionTypes` as a prop to `FilterBar`. Also update `allTypesSelected` and reset logic.

**PhaseNav layout overflow — too many type tabs**
Adding a new type increases the number of tabs in `PhaseNav`. Long labels (e.g. "POWERLIFTING") cause overflow.
Fix: filter `TYPE_ORDER` to only show types that have at least one existing phase (`visibleTypeOrder`). Active type is always included. Arrow navigation uses `visibleTypeOrder` not `TYPE_ORDER`.

**PhaseNav crash — missing type in TYPE_CONFIG**
`PhaseNav.jsx` reads `TYPE_CONFIG[selectedType].label` unconditionally.
If the new type is not in `TYPE_CONFIG`, this throws and blanks the entire app.
Fix: add the type to both `TYPE_CONFIG` and `TYPE_ORDER`. Already in checklist above.

**PhaseHeader NaN — null endDate passed to date arithmetic**
`daysRemaining(endDate)` did `new Date(null)` → `Invalid Date` → NaN in arithmetic → React warning and broken `phaseState`.
Fix: return `null` early if `endDate` is falsy; treat `null` daysLeft as `'current'` in `phaseState`.
Already in checklist above (null-guard section).

**App blank screen — unguarded Promise.all in loadPhaseData**
`getPhaseProgression` (new endpoint) returned 404 on the live Vercel instance before a redeploy.
The unguarded `Promise.all` rejected, state was never set, `loading` stayed false but no data rendered — blank screen with no error visible.
Fix: every call in `loadPhaseData`'s `Promise.all` must have `.catch(() => fallback)`. Already in checklist above.

**DB constraint — phase_type not in CHECK list**
`phases_phase_type_check` listed only existing types. INSERT rejected with 400.
Fix: migration to drop + recreate the constraint with the new type included. Already in checklist above.

**DB constraint — end_date NOT NULL for open-ended phase**
`phases_check` (or equivalent) enforced `end_date IS NOT NULL` globally.
Fix: migration to replace with a partial constraint allowing null only for the open-ended type. Already in checklist above.

**DB trigger fails with TEXT date columns — explicit casts required**
`check_session_date_in_phase()` declared `p_start DATE` and `p_end DATE` but the `phases` table stores `start_date` and `end_date` as TEXT. The trigger also compared `NEW.session_date` (TEXT) to a DATE variable.
Fix: use `start_date::date`, `end_date::date`, and `NEW.session_date::date` explicitly in the trigger. See migration `009_fix_session_date_trigger_text_casts.sql`.

**DB date arithmetic produces timestamp string, not date string**
Running `(start_date::date + INTERVAL '10 years')::text` in PostgreSQL returns `"2036-06-01 00:00:00"` (timestamp format), not `"2036-06-01"`. This breaks `normDate()` in PhaseCalendar (which splits on `'T'`) and `new Date(dateStr)` calls throughout the frontend.
Fix: always cast to DATE before text: `(start_date::date + INTERVAL '10 years')::date::text`. Or just set a literal string: `'2036-06-01'`.

**Backend create_phase sends NULL end_date for open-ended phases — breaks DB trigger**
Even after relaxing the constraint, inserting `end_date = NULL` causes the session date trigger to fail on the first session logged (can't compare TEXT session_date against a NULL DATE).
Fix: in `create_phase()`, auto-set `end_date = start_date + 10 years` when the phase type is open-ended and no end_date is supplied. See `api.py`. Also update existing rows in the DB with a one-time SQL statement.

**LogSessionForm shows all session types regardless of phase type**
The type dropdown used a single flat `SESSION_TYPES` constant for all phases. Powerlifting phases showed bench-specific types like `heavy_bench`, `volume_bench`, etc.
Fix: define `SESSION_TYPES_BY_PHASE` keyed by `phaseType`, derive `sessionTypes` from the selected phase, and reset the selected type when the phase changes. Also update the checklist entry for `LogSessionForm.jsx`.

**sessions_session_type_check constraint missing new phase session types**
The DB constraint only allowed bench/run/pull types. Inserting a `squat` or `deadlift` session for a powerlifting phase raised a 400.
Fix: drop and recreate the constraint to include the new types. See migration `010_add_powerlifting_session_types.sql`. Add this step to the checklist.

**NextStepTile shown on completed phases**
`NextStepTile` rendered whenever `progression` was truthy, with no check for whether the phase was still active.
Fix: compute `isCurrentPhase` from `selectedPhase.endDate` in `Dashboard.jsx` and gate the tile on it.

**PhaseCalendar renders full phase duration (up to 10 years)**
After setting a far-future `end_date`, `PhaseCalendar` computed a grid spanning the entire phase — thousands of cells, causing severe render slowdown.
Fix: cap the calendar display to end of next month regardless of `phase.endDate`.

---

## Quick checklist

```
[ ] SQL: add type to phases_phase_type_check
[ ] SQL: relax end_date constraint if open-ended
[ ] SQL: add new session types to sessions_session_type_check
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
