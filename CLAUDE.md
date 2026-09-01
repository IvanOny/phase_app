# Phase App — Claude Context

> **CRITICAL — Phase type bugs:** Whenever a bug is fixed that was caused by introducing a new phase type (missing config entry, missing null guard, DB constraint gap, etc.), **always append it to `docs/adding-a-new-phase-type.md`** so the checklist stays complete for the next phase type.

> **RULE — After every code change, immediately stage and commit with a descriptive message. Never push to remote unless the user explicitly says "push".**

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
phase_app/move_bot.py — Move: the whole Telegram bot (webhook, state machine, radar, crew)
phase_app/bot.py      — Burpee bot
phase_app/exercise_bot.py — Exercise bot
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

Claude sessions work inside `.claude/worktrees/<name>/`. To hand work between two
sessions, reference the branch — not the worktree path, which is per-session.

## Database schema (key tables)

```
phases          — phase_id, phase_type, start_date, end_date
sessions        — session_id, phase_id, session_date, session_type, elite_hrv_readiness
session_exercises — links sessions → exercises
exercises       — exercise_id, exercise_name, is_barbell_bench_press, is_bodyweight
exercise_sets   — set_number, load_kg, reps, is_working_set, is_top_set
```

Move's own tables (all `move_*`):

```
move_users      — telegram_user_id, participant_name, lang, invite_code
move_entries    — one row per move: media, entry_date, radar_ok
move_forwards   — which copy of a move went to whom (message ids, for edits)
move_crew       — mutual, both sides confirm      move_receive   — radar opt-in
move_reactions  — ⚡                              move_reports   — → warnings → suspensions
move_radar_block / move_radar_history            — never show / cooldown
move_state      — per-user step, 10-minute timeout
move_log_summary / move_transient                — the daily log line, the morning sweep
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

## This machine (Windows)

Facts that have each cost a debugging round already. They are here rather than in
a session summary because this file is reloaded every session and summaries are not.

**Python** is not on `PATH`. Bare `python` / `python3` / `py` open the Windows Store
stub, which exits without running anything. Call the interpreter by full path:

```bash
"C:/Users/nebel/AppData/Local/Programs/Python/Python313/python.exe" script.py
```

`pip.exe` is blocked by an application control policy. Use `python -m pip` instead.

**git identity** lives only in this repo's `.git/config` (`IvanOny <nebel911@gmail.com>`).
There is no `~/.gitconfig` and no system-level identity. If a commit ever fails with
"Author identity unknown", the fix is to restore that local config — never to invent a
name, and never to set a global one.

**Supabase's direct host** (`db.<ref>.supabase.co`) is IPv6-only, and this network has
no IPv6, so it fails with "could not translate host name". Use the Session pooler
string for anything run locally. `scripts/run_migration.py` prints this hint on failure.

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

`MOVE_BOT_TOKEN` — Move bot token
`MOVE_LOG_CHAT_ID` / `LOG_CHAT_ID` — where Move's activity and ⚠️ reports are posted
`MOVE_TRACE_CHAT_ID` — every incoming Move update, one line each. Unset falls back
to the log chat (where it buries the ⚠️ reports); `off` disables tracing.
`MOVE_BETA_IDS` — telegram ids that see changes before everyone else (comma-separated).
Currently unused: everything it gated has shipped to all users.
`POOL_COOLDOWN_DAYS` — days before radar may show you the same stranger again (default 7)
`RADAR_FRESH_DAYS` — how far back radar looks for a move to show (default 33)

## Running a migration

```bash
"C:/Users/nebel/AppData/Local/Programs/Python/Python313/python.exe" scripts/run_migration.py 042
```

Takes one or more files — a path, a filename, or just the number (`042`) — each in its
own transaction. `--dry-run` prints the SQL instead of applying it. There is no
migration ledger — migrations are written to be re-runnable. Locally this needs the
Session pooler `DATABASE_URL`, not the direct host — see "This machine" above.

## Move

Every daily job — nudges, the ⚡ report, radar, the sweep — hangs off a single cron
trigger (`/api/cron/move`, 06:00 UTC = 08:00 Berlin), because Vercel Hobby caps the
number of cron jobs. Each job carries its own `cron_log` guard, so re-running the
trigger is harmless.

Move's trace collapses into one message per person per day (`move_log_summary`),
edited as the day goes on. ⚠️ reports, crashes and moderation still send their own
messages so they aren't buried.

Bot messages that are scaffolding — menus, prompts, confirmations, the ⚙️ buttons
under a move — are recorded in `move_transient` and deleted the next morning by
the `move_sweep` job. Moves, comments and the ⚡ report stay. Answered prompts are
deleted immediately.
