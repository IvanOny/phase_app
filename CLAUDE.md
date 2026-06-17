# Phase App — Claude Context

> **CRITICAL — Phase type bugs:** Whenever a bug is fixed that was caused by introducing a new phase type (missing config entry, missing null guard, DB constraint gap, etc.), **always append it to `docs/adding-a-new-phase-type.md`** so the checklist stays complete for the next phase type.

> **RULE — After every code change, always tell the user what to restart/refresh:**
> - Changed `api/index.py` or `phase_app/*.py` → **restart backend** (`flask --app api/index run --port 5001`)
> - Changed any `frontend/src/**` file → **refresh browser** (Vite hot-reloads, but a manual refresh ensures state is clean)
> - Both changed → restart backend first, then refresh browser

## What this app is

Phase-based training tracker. A phase is a fixed training block (bench / pull-ups / run) with a start and end date. Each phase contains sessions; each session contains exercises and sets. The app tracks volume, e1RM, and HRV readiness over time.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite, Recharts for charts |
| Backend | Python / Flask, deployed as a Vercel serverless function |
| Database | PostgreSQL on Supabase |
| Deployment | Frontend → Vercel (`phase-app-yf5x.vercel.app`), Backend → Vercel (`phase-app-ivory.vercel.app` / `/api/index.py`) |

## Repo layout

```
api/index.py          — Vercel serverless entry point (Flask app, DB connection, CORS)
phase_app/api.py      — Route dispatcher and handler methods (PhaseApi class)
phase_app/metrics.py  — Read-only metric queries (e1RM, volume, phase summary)
phase_app/db_pg.py    — get_connection() for Supabase
frontend/src/
  App.jsx             — Top-level state, data fetching, page routing
  api/client.js       — All fetch calls to the backend
  components/
    Charts/           — E1rmChart, VolumeChart
    Dashboard/        — PhaseHeader, PhaseNav, PhaseSummaryCard, MaintenancePanel
    Sessions/         — SessionsList, session expand/edit
    DataEntry/        — DataEntryPanel, ScreenshotImportForm
    Faq/              — FaqPage (accordion)
    Common/           — ConfirmDialog, shared UI
  hooks/
    useExpandable.js  — useExpandable, useTooltip, useIsTouchDevice
    useChartColors.js — reads CSS vars, reactive to theme changes
```

## Key architectural decisions

**Batch metrics** — `GET /v1/metrics/phases/:id/session-bench-metrics` returns bench e1RM + volume for all sessions in one DB round-trip. `App.jsx` calls this once per phase load. Do not go back to per-session requests.

**N+1 elimination** — `SessionsList` derives its session→exercise map from the `exerciseVolumes` prop (already fetched). Do not add `getSessionExercises` calls per session.

**Stale DB connection** — `api/index.py` pings with `SELECT 1` before reusing a cached `_conn` on warm Vercel instances. Supabase drops idle connections silently.

**Tooltip behavior** — `useIsTouchDevice` (`hover: hover` + `pointer: fine` media query) switches charts between hover-show (desktop) and tap-show (mobile). Tooltip divs use `pointer-events: none` on desktop.

**Tap-outside dismiss pattern** — used on every chart tooltip. When a tooltip opens, register a one-shot `pointerdown` capture listener on `document` that closes it; clean it up in the effect's return. On the trigger element (dot, bar, tile) add `onPointerDown={e => e.stopPropagation()}` so the tap that opens the tooltip doesn't immediately fire the dismiss listener. Applied in: `ClassificationPanel` (lift tiles), `LiftTrendChart` (dots), `VolumeChart` (bars).

## Worktrees

Claude sessions work inside `.claude/worktrees/<name>/`. The active session for the current batch of chart + session fixes is `eager-booth-1e4578` on branch `fix/batch-session-metrics`. A second session runs in `happy-wilson-30212b`.

To reference this session from another: point it at branch `fix/batch-session-metrics`, PR #38, or the worktree path above.

## Database schema (key tables)

```
phases          — phase_id, phase_type, start_date, end_date
sessions        — session_id, phase_id, session_date, session_type, elite_hrv_readiness
session_exercises — links sessions → exercises
exercises       — exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight
exercise_sets   — set_number, load_kg, reps, is_working_set, is_top_set
```

## Adding a new phase type

See `docs/adding-a-new-phase-type.md` for the full checklist.
Every change required when `powerlifting` was introduced is documented there,
including the DB constraints, backend validation, frontend config tables,
null-guard patterns, and dashboard routing.

**IMPORTANT:** When the user asks to add a new phase type, first ask all the questions
listed at the top of `docs/adding-a-new-phase-type.md` before writing any code.

**IMPORTANT:** Whenever a bug is fixed that is caused by introducing a new phase type
(e.g. a missing type in a config table, a missing null guard, a constraint error),
always append it to `docs/adding-a-new-phase-type.md` so the checklist stays complete.

## Running locally

```bash
# Backend (from repo root)
flask --app api/index run --port 5001

# Frontend (from frontend/)
npm run dev
```

Frontend dev server: `http://localhost:5173`
Backend dev server: `http://localhost:5001`

## env vars (backend Vercel project)

`DATABASE_URL` — Supabase connection string

