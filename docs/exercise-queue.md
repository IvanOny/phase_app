# Movement Snacks (Telegram bot + web planner)

The user-facing name is **Movement Snacks**. Internally the code, DB tables, and
API routes use the older `exercise` / `exq` prefix (`exercise_items`, `/v1/exq/…`,
`exercise_bot.py`) — don't rename those, they're stable.

A personal movement-snacks scheduler bolted onto the existing burpee Telegram
bot. It lets a single admin user register small exercises (mobility drills, skill
work, prehab) and be served them either on a fixed cadence or opportunistically
from a queue — via the bot or the web planner. It is **separate from the
phase-app training tracker**; the two only share the repo and the Vercel deploy.

## Where it lives

| File | Role |
|---|---|
| `phase_app/exercise_bot.py` | The whole feature — command router, add/edit flows, serve query, daily overview |
| `phase_app/bot.py` | The burpee bot. Routes `ex:` callbacks and admin messages into `exercise_bot` before its own logic |
| `migrations/030_exercise_queue.sql` | All five tables (see below) |
| `api/index.py` | Folds `send_exercise_overview` into the 17:00 UTC cron (`/api/cron/radar`) |

## Gating

Single-user in v1. Every table is keyed by `user_id`, so multi-user is a later
flip, not a rewrite. Routing in `bot.py` only hands a message/callback to the
exercise feature when the sender's Telegram id equals the `ADMIN_TG_ID` env var
(the same admin id the burpee `/broadcast` uses — no separate env var).

English-only: the audience is one admin, so it skips the burpee bot's i18n table.

## Three scheduling tiers

- **Tier 2 — fixed** (`schedule_type='fixed'`): due every `repeat_interval_days`.
  Surfaced in the daily 19:00 overview when due.
- **Tier 2 — acquisition** (`schedule_type='acquisition'`): a temporary "learn a
  move" pin. Due every `acq_interval_days`; after `acq_target_sessions` completed
  sessions it **auto-demotes to `queue`** and rejoins the opportunistic pool.
- **Tier 3 — queue** (`schedule_type='queue'`): opportunistic. Served on demand by
  `next`, ordered by how overdue it is: `last_done_at ASC NULLS FIRST, created_at ASC`.

Due-ness is timezone-aware (per-user `timezone`, default `Europe/Berlin`).

## Commands

Sent as plain text (no leading slash needed; a slash is stripped if present).

| Command | Effect |
|---|---|
| `/add` | Start the guided add flow (inline keyboards for enum fields) |
| `next [filters]` | Serve the next queue item. Filters: `focus` / `location` (`home`/`barrack`/`random`) / `load` (`easy`/`upper`/`lower`/`systemic`). e.g. `next knee barrack` |
| `done [actual]` | Mark the served item done; optional actual-dose note |
| `skip` | Skip the served item for 1h. After 3 consecutive skips it offers to park it |
| `overview` | Queue in serve order |
| `list` | All exercises with schedule + status |
| `edit <name>` | Change one field (inline keyboard picks the field) |
| `pause` / `park` / `activate` `<name>` | Set status. Note: bare `pause` (no name) falls through to the burpee bot's mute |
| `remove <name>` | Delete (with confirm) |
| `stats <name>` / `history` | Logs — per-exercise count/last, or last 10 overall |
| `undo` | Revert the last `done` (restores `last_done_at`, rolls back an acquisition counter) |
| `exhelp` | Command list |

A **pending-serve guard** means repeated `next` re-sends the current item rather
than advancing past it until you `done` or `skip` it.

## Database tables (migration 030)

The item table is `exercise_items`, **not** `exercises` — the phase-app tracker
already owns an `exercises` table (`exercise_id`, `exercise_name`, …). Don't
confuse them.

- `exercise_users` — telegram id, chat id, timezone, overview time
- `exercise_items` — the exercises + all scheduling/queue state
- `exercise_pending_serves` — one served-but-unanswered item per user
- `exercise_history` — completion log (`done_at`, `dose_actual`, `source`)
- `exercise_bot_state` — conversational state for the add/edit flows (10-min timeout), separate from the burpee bot's `telegram_bot_state`

## Cron

`send_exercise_overview(conn)` runs inside `/api/cron/radar` (17:00 UTC =
19:00 Europe/Berlin, matching the default `overview_time`). It sends each user a
"Today's plan": Tier-2 items due today plus a snapshot of the queue's top 10.

## Web planner (calendar / log / stats)

Alongside the Telegram bot there's a web UI, served from the phase-app frontend
at `/?exq_token=<token>`. Get the link from the bot with **`exapp`**; it mints a
per-user token stored on `exercise_users.token`.

- **Calendar** (`ScheduleCalendar.jsx`) — week/month grid with drag-and-drop. A
  side rail lists active exercises; drag one onto a day to schedule it. Solid
  chips are committed occurrences; faint dashed chips are cadence *suggestions*.
  **A manual placement overrides the suggestion** — dragging beats every-N-days.
  Chips expose ✓ (done — resets the cadence anchor, advances acquisition) and ✕.
- **Log** — recent completions from `exercise_history`.
- **Stats** — per-exercise counts + totals.

### Drag behaviour (toggle in the calendar toolbar, remembered in localStorage)

- **Shift series** — the dropped day becomes the exercise's `anchor_date`
  (migration 032), so every future occurrence re-phases and follows, keeping the
  cadence.
- **Only this** — just this instance moves. The day it came from gets a
  `status='skipped'` tombstone row so the original ghost doesn't linger; future
  occurrences are untouched.

Tombstones are suppression-only — the API filters them out of `occurrences` but
still uses them to hide that day's suggestion.

### Scheduling model (`exercise_schedule`, migration 031)

One row per placed instance: `exercise_id, scheduled_date, origin (manual|auto),
status`. Cadence suggestions for `fixed`/`acquisition` items are projected
on the fly in `GET /v1/exq/schedule` (not materialized); a manual pin on a date
suppresses that day's suggestion for the same exercise. Completing an occurrence
sets `last_done_at = now`, so the rhythm continues from when it was actually done.

### API (`phase_app/exercise_api.py`, token-gated via `?token=`)

`GET /v1/exq/exercises` · `GET/POST /v1/exq/schedule` ·
`PATCH/DELETE /v1/exq/schedule/:id` · `POST /v1/exq/schedule/:id/done` ·
`GET /v1/exq/history` · `GET /v1/exq/stats`

Drag-and-drop is built on Pointer Events (`ScheduleCalendar.jsx`), so it works
with mouse, touch, and pen — draggables set `touch-action: none` and a floating
ghost follows the finger; the drop target is found via `elementFromPoint`.

## Setup checklist

1. Run migrations `030_exercise_queue.sql`, `031_exercise_schedule.sql`, and
   `032_exercise_anchor_date.sql` in Supabase.
2. Ensure `ADMIN_TG_ID` is set in the bot's Vercel project.
3. Send `exapp` to the bot to get your planner link.
