# Exercise Queue (Telegram bot feature)

A personal "movement snacks" scheduler bolted onto the existing burpee Telegram
bot. It lets a single admin user register small exercises (mobility drills, skill
work, prehab) and be served them either on a fixed cadence or opportunistically
from a queue. It is **separate from the phase-app training tracker** — different
tables, no shared UI, no web frontend. The only thing the two share is the repo
and the Vercel deployment.

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

## Setup checklist

1. Run `migrations/030_exercise_queue.sql` in Supabase.
2. Ensure `ADMIN_TG_ID` is set in the bot's Vercel project.
