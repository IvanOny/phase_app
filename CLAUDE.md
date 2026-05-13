# Phase App — Claude Context

## What this app is

Phase-based training tracker. A phase is a fixed training block (bench / pull-ups / run) with a start and end date. Each phase contains sessions; each session contains exercises and sets. The app tracks volume, e1RM, and HRV readiness over time.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite, Recharts for charts |
| Backend | Python / Flask, deployed as a Vercel serverless function |
| Database | PostgreSQL on Supabase |
| Deployment | Frontend → Vercel (`phase-app-ivory.vercel.app`), Backend → Vercel (`/api/index.py`) |

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
