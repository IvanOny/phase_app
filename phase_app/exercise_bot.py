"""Exercise Queue feature — bolted onto the burpee Telegram bot.

Single-user in v1 (gated by ADMIN_TG_ID in the webhook router), but every
table is keyed by user_id so multi-user is a later flip, not a rewrite.

Two tiers:
  - Tier 2 (fixed / acquisition): due-based, shown in the daily 19:00 overview.
  - Tier 3 (queue): opportunistic, served on demand by `next`, ordered by how
    overdue it is (last_done_at ASC NULLS FIRST, created_at ASC).

English-only: the audience is a single admin user, so we skip the bot's i18n table.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

# Reuse the burpee bot's Telegram helpers. This module is imported lazily from
# handle_webhook, so phase_app.bot is fully initialized by the time this runs.
from phase_app.bot import _tg, _send, _log
from phase_app.exercise_due import first_due, interval_of

_STATE_TIMEOUT_MINUTES = 10

_LOCATIONS = ("home", "barrack", "random")
# The location that acts as a wildcard in the serve query (matches any filter).
_LOCATION_ANY = "random"
_LOAD_TAGS = ("easy", "upper", "lower", "systemic")
_SCHEDULES = ("queue", "fixed", "acquisition")

# Command words this feature owns (first token, leading slash stripped).
_EX_COMMANDS = {
    "add", "next", "done", "skip", "overview", "list", "edit", "tier",
    "pause", "park", "activate", "remove", "stats", "history", "undo", "exhelp",
    "exapp",
}

# Web UI base (calendar / log / stats), reads ?exq_token=.
_EXQ_APP_BASE = "https://phase-app-yf5x.vercel.app"


# ── User + state helpers ─────────────────────────────────────────────────────

def _get_user_id(cur, tg_id: int) -> int | None:
    cur.execute("SELECT id FROM exercise_users WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    return row["id"] if row else None


def _ensure_user(cur, conn, tg_id: int, chat_id: int) -> int:
    cur.execute(
        "INSERT INTO exercise_users (telegram_user_id, chat_id) VALUES (%s, %s) "
        "ON CONFLICT (telegram_user_id) DO UPDATE SET chat_id = EXCLUDED.chat_id "
        "RETURNING id",
        (tg_id, chat_id),
    )
    uid = cur.fetchone()["id"]
    conn.commit()
    return uid


def _get_state(cur, user_id: int) -> tuple[str | None, dict]:
    cur.execute(
        "SELECT state, data, created_at FROM exercise_bot_state WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if not row or not row["state"]:
        return None, {}
    if row["created_at"] and (datetime.now(timezone.utc) - row["created_at"]).total_seconds() > _STATE_TIMEOUT_MINUTES * 60:
        cur.execute("DELETE FROM exercise_bot_state WHERE user_id = %s", (user_id,))
        return None, {}
    data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"] or "{}")
    return row["state"], data


def _set_state(cur, conn, user_id: int, state: str, data: dict) -> None:
    cur.execute(
        "INSERT INTO exercise_bot_state (user_id, state, data, created_at) VALUES (%s, %s, %s, NOW()) "
        "ON CONFLICT (user_id) DO UPDATE SET state = EXCLUDED.state, data = EXCLUDED.data, created_at = NOW()",
        (user_id, state, json.dumps(data)),
    )
    conn.commit()


def _clear_state(cur, conn, user_id: int) -> None:
    cur.execute("DELETE FROM exercise_bot_state WHERE user_id = %s", (user_id,))
    conn.commit()


def _get_ex_by_name(cur, user_id: int, name: str):
    cur.execute(
        "SELECT * FROM exercise_items WHERE user_id = %s AND LOWER(name) = LOWER(%s)",
        (user_id, name),
    )
    return cur.fetchone()


# ── Timezone-aware due check ─────────────────────────────────────────────────

def _user_tz(cur, user_id: int):
    cur.execute("SELECT timezone FROM exercise_users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    tzname = (row["timezone"] if row else None) or "Europe/Berlin"
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(tzname)
    except Exception:
        return timezone.utc


def _next_due_date(ex, tz, as_of=None):
    """First occurrence due on or after `as_of` (default: today). See exercise_due."""
    ref = as_of or datetime.now(tz).date()
    last = ex["last_done_at"]
    last_date = last.astimezone(tz).date() if last else None
    # .get keeps this working if migration 032 hasn't been applied yet.
    anchor = ex.get("anchor_date") if hasattr(ex, "get") else None
    return first_due(interval_of(ex), last_date, anchor, ref)


# ── Serve query ──────────────────────────────────────────────────────────────

# How much more often a tier should come up. Serving is weighted-fair rather
# than random: an item accumulates "pressure" as it sits undone, at a rate set
# by its tier, and the most pressured item is served next.
#
# Why not weighted random: random repeats itself and can starve an item for
# weeks. This keeps the strict rotation the queue always had -- nothing is ever
# skipped over forever -- while making the rotation uneven on purpose.
#
# The ratio falls out of the arithmetic. If tier 1 builds pressure 3x as fast,
# it reaches the front 3x as often, so the weights *are* the frequency ratio.
_TIER_WEIGHT = {1: 3, 2: 2, 3: 1}


def _serve_next(cur, user_id: int, filters: dict):
    cur.execute(
        "SELECT * FROM exercise_items "
        "WHERE user_id = %s AND schedule_type = 'queue' AND status = 'active' "
        "  AND (skipped_until IS NULL OR skipped_until <= NOW()) "
        "  AND (%s IS NULL OR focus_area ILIKE '%%' || %s || '%%') "
        "  AND (%s IS NULL OR location = %s OR location = 'random') "
        "  AND (%s IS NULL OR load_tag = %s) "
        # Never-done items are backdated a year so they still come up first,
        # which is what NULLS FIRST used to do -- you added it because you
        # wanted to do it, not to have it wait its turn.
        "ORDER BY EXTRACT(EPOCH FROM (NOW() - COALESCE(last_done_at, "
        "                                              created_at - INTERVAL '365 days'))) "
        "         * CASE tier WHEN 1 THEN 3 WHEN 2 THEN 2 ELSE 1 END DESC, "
        "         created_at ASC "
        "LIMIT 1",
        (
            user_id,
            filters.get("focus"), filters.get("focus"),
            filters.get("location"), filters.get("location"),
            filters.get("load"), filters.get("load"),
        ),
    )
    return cur.fetchone()


def _parse_filters(tokens: list[str]) -> dict:
    f: dict = {"focus": None, "location": None, "load": None}
    for tok in tokens:
        t = tok.lower()
        if t in _LOCATIONS:
            f["location"] = t
        elif t in _LOAD_TAGS:
            f["load"] = t
        else:
            f["focus"] = t
    return f


# ── Rendering ────────────────────────────────────────────────────────────────

def _render_served(ex) -> str:
    lines = [f"▶ {ex['name']}"]
    if ex["description"]:
        lines.append(ex["description"])
    meta = []
    meta.append(f"📍{ex['location']}")
    if ex["equipment"]:
        meta.append(f"🎒{ex['equipment']}")
    if ex["load_tag"]:
        meta.append(ex["load_tag"])
    lines.append(" · ".join(meta))
    return "\n".join(lines)


def _done_skip_kb() -> dict:
    return {"inline_keyboard": [[
        {"text": "Done", "callback_data": "ex:done"},
        {"text": "Skip", "callback_data": "ex:skip"},
    ]]}


# ── Add-flow prompts ─────────────────────────────────────────────────────────

def _kb_schedule() -> dict:
    return {"inline_keyboard": [
        [{"text": "Queue (opportunistic)", "callback_data": "ex:add:sched:queue"}],
        [{"text": "Fixed (every N days)", "callback_data": "ex:add:sched:fixed"}],
        [{"text": "Acquisition (learn a move)", "callback_data": "ex:add:sched:acquisition"}],
        [{"text": "Cancel", "callback_data": "ex:add:cancel"}],
    ]}


def _kb_interval(prefix: str) -> dict:
    return {"inline_keyboard": [[
        {"text": "1", "callback_data": f"{prefix}:1"},
        {"text": "2", "callback_data": f"{prefix}:2"},
        {"text": "3", "callback_data": f"{prefix}:3"},
        {"text": "7", "callback_data": f"{prefix}:7"},
        {"text": "30", "callback_data": f"{prefix}:30"},
    ]]}


def _kb_target() -> dict:
    return {"inline_keyboard": [[
        {"text": "5", "callback_data": "ex:add:acqtarget:5"},
        {"text": "10", "callback_data": "ex:add:acqtarget:10"},
        {"text": "15", "callback_data": "ex:add:acqtarget:15"},
        {"text": "20", "callback_data": "ex:add:acqtarget:20"},
    ]]}


def _kb_location() -> dict:
    return {"inline_keyboard": [[
        {"text": loc, "callback_data": f"ex:add:loc:{loc}"} for loc in _LOCATIONS
    ]]}


def _kb_load() -> dict:
    return {"inline_keyboard": [
        [{"text": "easy", "callback_data": "ex:add:load:easy"},
         {"text": "upper", "callback_data": "ex:add:load:upper"}],
        [{"text": "lower", "callback_data": "ex:add:load:lower"},
         {"text": "systemic", "callback_data": "ex:add:load:systemic"}],
    ]}


def _kb_skip() -> dict:
    return {"inline_keyboard": [[{"text": "Skip", "callback_data": "ex:add:skip"}]]}


def _advance_to_focus(cur, conn, user_id: int, chat_id: int, data: dict) -> None:
    """Move the add flow to the focus step (the step formerly after dose)."""
    _set_state(cur, conn, user_id, "ex_add:focus", data)
    _send(chat_id, "Focus tags? (e.g. knee shoulder, or Skip)", reply_markup=_kb_skip())


def _add_confirm_text(d: dict) -> str:
    sched = d.get("schedule_type")
    if sched == "fixed":
        sched_str = f"fixed · every {d.get('repeat_interval_days')} days"
    elif sched == "acquisition":
        sched_str = f"acquisition · every {d.get('acq_interval_days')} days × {d.get('acq_target_sessions')} sessions"
    else:
        sched_str = "queue (opportunistic)"
    lines = [
        "Confirm new exercise:",
        f"• name: {d.get('name')}",
        f"• schedule: {sched_str}",
        f"• focus: {d.get('focus_area') or '—'}",
        f"• location: {d.get('location')}",
        f"• equipment: {d.get('equipment') or '—'}",
        f"• load: {d.get('load_tag') or '—'}",
    ]
    if d.get("description"):
        lines.insert(2, f"• description: {d.get('description')}")
    return "\n".join(lines)


def _kb_confirm() -> dict:
    return {"inline_keyboard": [[
        {"text": "✅ Save", "callback_data": "ex:add:save"},
        {"text": "Cancel", "callback_data": "ex:add:cancel"},
    ]]}


def _maybe_name_action(cur, conn, user_id: int | None, chat_id: int, parts: list[str]) -> bool:
    """Handle a bare '<exercise name> done' / '<name> skip' message.

    Returns True only when the name resolves to one of the user's exercises;
    otherwise False so the message can fall through to the burpee bot. This keeps
    us from hijacking unrelated chatter that merely happens to end in 'done'.
    """
    if user_id is None or len(parts) < 2:
        return False
    action = parts[-1].lower()
    if action not in ("done", "skip"):
        return False
    name = " ".join(parts[:-1]).strip()
    if not name:
        return False
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        return False
    _mark_today(cur, conn, user_id, chat_id, ex["id"], done=(action == "done"))
    return True


# ── Public: message router ───────────────────────────────────────────────────

def maybe_handle_exercise(cur, conn, tg_id: int, chat_id: int, text: str) -> bool:
    """Return True if this message belonged to the exercise feature and was handled.
    Return False to let the burpee logic process it."""
    if not text:
        return False

    user_id = _get_user_id(cur, tg_id)

    # 1) Active add/edit conversation takes priority.
    if user_id is not None:
        state, data = _get_state(cur, user_id)
        if state:
            return _handle_state_input(cur, conn, user_id, chat_id, state, data, text)

    # 2) Command dispatch.
    parts = text.split()
    word = parts[0].lstrip("/").lower()
    args = parts[1:]

    if word not in _EX_COMMANDS:
        # Natural-language "<exercise name> done" / "<name> skip" — log by name.
        # Only consumed when the name matches an existing exercise; otherwise the
        # message falls through to the burpee bot.
        return _maybe_name_action(cur, conn, user_id, chat_id, parts)

    # `pause` collides with the burpee /pause (mute). Exercise pause always has a
    # target name; bare pause falls through to burpee.
    if word == "pause" and not args:
        return False

    user_id = _ensure_user(cur, conn, tg_id, chat_id)

    if word == "exhelp":
        _cmd_help(chat_id)
    elif word == "add":
        _cmd_add_start(cur, conn, user_id, chat_id)
    elif word == "next":
        _cmd_next(cur, conn, user_id, chat_id, _parse_filters(args))
    elif word == "done":
        _cmd_done(cur, conn, user_id, chat_id, " ".join(args) or None)
    elif word == "skip":
        _cmd_skip(cur, conn, user_id, chat_id)
    elif word == "overview":
        _cmd_overview(cur, user_id, chat_id)
    elif word == "list":
        _cmd_list(cur, user_id, chat_id)
    elif word == "edit":
        _cmd_edit(cur, conn, user_id, chat_id, " ".join(args))
    elif word == "tier":
        _cmd_tier(cur, conn, user_id, chat_id, args)
    elif word in ("pause", "park", "activate"):
        _cmd_status(cur, conn, user_id, chat_id, word, " ".join(args))
    elif word == "remove":
        _cmd_remove(cur, conn, user_id, chat_id, " ".join(args))
    elif word == "stats":
        _cmd_stats(cur, user_id, chat_id, " ".join(args))
    elif word == "history":
        _cmd_history(cur, user_id, chat_id)
    elif word == "undo":
        _cmd_undo(cur, conn, user_id, chat_id)
    elif word == "exapp":
        _cmd_exapp(cur, conn, user_id, chat_id)
    return True


# ── Public: callback router ──────────────────────────────────────────────────

def handle_exercise_callback(cur, conn, tg_id: int, chat_id: int, msg_id: int, data: str) -> None:
    user_id = _ensure_user(cur, conn, tg_id, chat_id)
    body = data[len("ex:"):]  # strip namespace

    if body == "done":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _cmd_done(cur, conn, user_id, chat_id, None)
        return
    if body == "skip":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _cmd_skip(cur, conn, user_id, chat_id)
        return
    if body.startswith("tdone:") or body.startswith("tskip:"):
        # "tdone:<id>" (overview, acts on today) or "tdone:<id>:<YYYY-MM-DD>"
        # (daily report — the date keeps a stale button honest, and tells us to
        # redraw that report in place instead of sending a confirmation).
        parts = body.split(":")
        ex_id = int(parts[1])
        day = None
        if len(parts) > 2:
            try:
                day = date.fromisoformat(parts[2])
            except ValueError:
                day = None
        _mark_today(cur, conn, user_id, chat_id, ex_id,
                    done=parts[0] == "tdone", for_date=day, quiet=day is not None)
        if day is not None:
            text, kb, _ = _daily_report(cur, user_id, _user_tz(cur, user_id), day)
            _tg("editMessageText", {
                "chat_id": chat_id, "message_id": msg_id,
                "text": text, "reply_markup": kb or {},
            })
        return
    if body.startswith("park:"):
        name = body[len("park:"):]
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _cmd_status(cur, conn, user_id, chat_id, "park", name)
        return
    if body == "park_no":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _send(chat_id, "Kept it active.")
        return
    if body.startswith("rmconfirm:"):
        name = body[len("rmconfirm:"):]
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _do_remove(cur, conn, user_id, chat_id, name)
        return
    if body == "rmcancel":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _send(chat_id, "Cancelled.")
        return
    if body.startswith("add:"):
        _handle_add_callback(cur, conn, user_id, chat_id, msg_id, body[len("add:"):])
        return
    if body.startswith("edit:"):
        _handle_edit_callback(cur, conn, user_id, chat_id, msg_id, body[len("edit:"):])
        return


# ── Commands ─────────────────────────────────────────────────────────────────

def _cmd_exapp(cur, conn, user_id: int, chat_id: int) -> None:
    """Issue (once) a token and send the web-UI link for calendar / log / stats."""
    import secrets
    cur.execute("SELECT token FROM exercise_users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    token = row["token"] if row and row["token"] else None
    if not token:
        token = secrets.token_urlsafe(24)
        cur.execute("UPDATE exercise_users SET token = %s WHERE id = %s", (token, user_id))
        conn.commit()
    _send(chat_id, f"🍎 Your Movement Snacks planner:\n{_EXQ_APP_BASE}/?exq_token={token}")


def _cmd_help(chat_id: int) -> None:
    _send(chat_id,
        "🍎 Movement Snacks — commands:\n\n"
        "/add — register a new exercise\n"
        "exapp — open the web planner (calendar / log / stats)\n"
        "next [filters] — serve the next queue item (e.g. next knee barrack)\n"
        "done [actual] — mark the served item done\n"
        "<name> done — log an exercise by name (e.g. squats done)\n"
        "skip — skip the served item for 1h\n"
        "overview — today's plan with ✓/⏭ buttons (same as the 19:00 report)\n"
        "list — all exercises\n"
        "edit <name> — change a field\n"
        "tier <name> [1|2|3] — how often it comes up (1 = most often)\n"
        "pause/park/activate <name> — status\n"
        "remove <name> — delete\n"
        "stats <name> / history — logs\n"
        "undo — revert last done")


def _cmd_next(cur, conn, user_id: int, chat_id: int, filters: dict) -> None:
    # Re-send an already-pending item rather than advancing past it.
    cur.execute(
        "SELECT e.* FROM exercise_pending_serves p JOIN exercise_items e ON e.id = p.exercise_id "
        "WHERE p.user_id = %s",
        (user_id,),
    )
    pending = cur.fetchone()
    if pending:
        _send(chat_id, "Still pending:\n\n" + _render_served(pending), reply_markup=_done_skip_kb())
        return

    ex = _serve_next(cur, user_id, filters)
    if not ex:
        _send(chat_id, "Nothing in the queue fits that right now.")
        return
    cur.execute(
        "INSERT INTO exercise_pending_serves (user_id, exercise_id, served_at) VALUES (%s, %s, NOW()) "
        "ON CONFLICT (user_id) DO UPDATE SET exercise_id = EXCLUDED.exercise_id, served_at = NOW()",
        (user_id, ex["id"]),
    )
    conn.commit()
    _send(chat_id, _render_served(ex), reply_markup=_done_skip_kb())


def _cmd_done(cur, conn, user_id: int, chat_id: int, actual: str | None) -> None:
    cur.execute(
        "SELECT e.* FROM exercise_pending_serves p JOIN exercise_items e ON e.id = p.exercise_id "
        "WHERE p.user_id = %s",
        (user_id,),
    )
    ex = cur.fetchone()
    if not ex:
        _send(chat_id, "Nothing pending — use `next` first.")
        return

    source = "fixed" if ex["schedule_type"] != "queue" else "next"
    cur.execute(
        "UPDATE exercise_items SET last_done_at = NOW(), consecutive_skips = 0, skipped_until = NULL WHERE id = %s",
        (ex["id"],),
    )
    cur.execute(
        "INSERT INTO exercise_history (user_id, exercise_id, done_at, dose_actual, source) "
        "VALUES (%s, %s, NOW(), %s, %s)",
        (user_id, ex["id"], actual, source),
    )
    cur.execute("DELETE FROM exercise_pending_serves WHERE user_id = %s", (user_id,))

    msg = f"✓ {ex['name']} done"
    if actual:
        msg += f" ({actual})"

    # Acquisition lifecycle
    if ex["schedule_type"] == "acquisition":
        done_n = ex["acq_sessions_done"] + 1
        target = ex["acq_target_sessions"] or 0
        if done_n >= target:
            cur.execute(
                "UPDATE exercise_items SET schedule_type = 'queue', acq_sessions_done = 0, "
                "acq_target_sessions = NULL, acq_interval_days = NULL WHERE id = %s",
                (ex["id"],),
            )
            msg += f"\n🎓 Acquisition complete ({done_n}/{target}) — {ex['name']} rejoins the queue."
            _log(f"🎓 Acquisition complete\n🏋️ {ex['name']} → queue")
        else:
            cur.execute("UPDATE exercise_items SET acq_sessions_done = %s WHERE id = %s", (done_n, ex["id"]))
            msg += f"\n📈 Acquisition {done_n}/{target}"

    _drop_premature_auto(cur, user_id, ex["id"], _user_tz(cur, user_id))
    conn.commit()
    _send(chat_id, msg)
    _log(f"🏋️ Exercise done\n• {ex['name']}" + (f": {actual}" if actual else ""))


def _cmd_skip(cur, conn, user_id: int, chat_id: int) -> None:
    cur.execute(
        "SELECT e.* FROM exercise_pending_serves p JOIN exercise_items e ON e.id = p.exercise_id "
        "WHERE p.user_id = %s",
        (user_id,),
    )
    ex = cur.fetchone()
    if not ex:
        _send(chat_id, "Nothing pending — use `next` first.")
        return
    skips = ex["consecutive_skips"] + 1
    cur.execute(
        "UPDATE exercise_items SET skipped_until = NOW() + INTERVAL '1 hour', consecutive_skips = %s WHERE id = %s",
        (skips, ex["id"]),
    )
    cur.execute("DELETE FROM exercise_pending_serves WHERE user_id = %s", (user_id,))
    conn.commit()
    _log(f"⏭ Exercise skipped\n• {ex['name']} (skips: {skips})")
    if skips >= 3:
        _send(chat_id,
            f"⏭ Skipped {ex['name']} (for 1h).\n\nYou keep skipping {ex['name']} — park it?",
            reply_markup={"inline_keyboard": [[
                {"text": "Park it", "callback_data": f"ex:park:{ex['name']}"},
                {"text": "Keep active", "callback_data": "ex:park_no"},
            ]]})
    else:
        _send(chat_id, f"⏭ Skipped {ex['name']} for 1h.")


def _cmd_overview(cur, user_id: int, chat_id: int) -> None:
    """Same view as the evening daily report, on demand — today's items with
    ✓/⏭, tomorrow's preview and the queue. Shares _daily_report so both stay
    identical and both edit themselves in place as you tap."""
    tz = _user_tz(cur, user_id)
    today = datetime.now(tz).date()
    text, kb, has_content = _daily_report(cur, user_id, tz, today)
    if not has_content:
        _send(chat_id, "✅ Nothing left today.")
        return
    _send(chat_id, text, reply_markup=kb)


def _drop_premature_auto(cur, user_id: int, ex_id: int, tz) -> None:
    """After a completion, bin any auto-materialised future rows that the new
    rhythm makes too early. Manual placements are left alone — the user put
    those there deliberately."""
    cur.execute("SELECT * FROM exercise_items WHERE id = %s AND user_id = %s", (ex_id, user_id))
    ex = cur.fetchone()
    if not ex or ex["schedule_type"] not in ("fixed", "acquisition"):
        return
    today = datetime.now(tz).date()
    nxt = _next_due_date(ex, tz, today)
    if nxt is None:
        return
    cur.execute(
        "DELETE FROM exercise_schedule WHERE user_id = %s AND exercise_id = %s "
        "AND origin = 'auto' AND status = 'planned' "
        "AND scheduled_date > %s AND scheduled_date < %s",
        (user_id, ex_id, today, nxt),
    )


def _lock_in(cur, user_id: int, tz, day) -> None:
    """Turn `day`'s cadence suggestions into committed rows.

    Runs with the morning report: until it fires the day is still fluid (dashed)
    and can be rearranged freely; afterwards it's the day's actual programme.
    Rows are origin='auto' so they stay distinguishable from hand-placed ones,
    and they remain draggable — this is a commitment, not a lock.

    Also closes the books on days gone by: anything still 'planned' before `day`
    becomes 'skipped', so history is honest and old chips don't pile up.
    """
    cur.execute(
        "UPDATE exercise_schedule SET status = 'skipped' "
        "WHERE user_id = %s AND status = 'planned' AND scheduled_date < %s",
        (user_id, day),
    )

    cur.execute(
        "SELECT * FROM exercise_items WHERE user_id = %s AND status = 'active' "
        "AND schedule_type IN ('fixed', 'acquisition')",
        (user_id,),
    )
    for e in cur.fetchall():
        if _next_due_date(e, tz, day) == day:
            cur.execute(
                "INSERT INTO exercise_schedule (user_id, exercise_id, scheduled_date, origin, status) "
                "VALUES (%s, %s, %s, 'auto', 'planned') "
                "ON CONFLICT (exercise_id, scheduled_date) DO NOTHING",
                (user_id, e["id"], day),
            )


def _mark_today(cur, conn, user_id: int, chat_id: int, ex_id: int, done: bool,
                for_date=None, quiet: bool = False) -> None:
    """Mark a scheduled / cadence-due exercise done or skipped for a given day.

    Records it on the calendar (exercise_schedule) so the web planner and the
    bot agree, and so it stops being listed. `for_date` comes from the button's
    callback data, so pressing a button on yesterday's report still applies to
    the day that report was about.
    """
    cur.execute("SELECT * FROM exercise_items WHERE id = %s AND user_id = %s", (ex_id, user_id))
    ex = cur.fetchone()
    if not ex:
        if not quiet:
            _send(chat_id, "That exercise no longer exists.")
        return
    tz = _user_tz(cur, user_id)
    day = for_date or datetime.now(tz).date()
    cur.execute(
        "INSERT INTO exercise_schedule (user_id, exercise_id, scheduled_date, origin, status) "
        "VALUES (%s, %s, %s, 'manual', %s) "
        "ON CONFLICT (exercise_id, scheduled_date) DO UPDATE SET status = EXCLUDED.status",
        (user_id, ex_id, day, "done" if done else "skipped"),
    )

    if not done:
        # Skip forfeits this cycle: push the next occurrence a full interval out
        # rather than letting it reappear tomorrow.
        iv = interval_of(ex)
        if iv:
            nxt = day + timedelta(days=iv)
            cur.execute("UPDATE exercise_items SET anchor_date = %s WHERE id = %s", (nxt, ex_id))
            # Drop any already-materialised rows inside the new gap.
            cur.execute(
                "DELETE FROM exercise_schedule WHERE user_id = %s AND exercise_id = %s "
                "AND origin = 'auto' AND status = 'planned' "
                "AND scheduled_date > %s AND scheduled_date < %s",
                (user_id, ex_id, day, nxt),
            )
        conn.commit()
        if not quiet:
            when = f" — next in {iv}d" if iv else ""
            _send(chat_id, f"⏭ {ex['name']} — skipped{when}.")
        _log(f"⏭ Skipped\n• {ex['name']}")
        return

    cur.execute(
        "UPDATE exercise_items SET last_done_at = NOW(), consecutive_skips = 0, skipped_until = NULL "
        "WHERE id = %s",
        (ex_id,),
    )
    cur.execute(
        "INSERT INTO exercise_history (user_id, exercise_id, done_at, source) VALUES (%s, %s, NOW(), 'overview')",
        (user_id, ex_id),
    )
    msg = f"✓ {ex['name']} done"
    if ex["schedule_type"] == "acquisition":
        done_n = (ex["acq_sessions_done"] or 0) + 1
        target = ex["acq_target_sessions"] or 0
        if done_n >= target:
            cur.execute(
                "UPDATE exercise_items SET schedule_type = 'queue', acq_sessions_done = 0, "
                "acq_target_sessions = NULL, acq_interval_days = NULL WHERE id = %s",
                (ex_id,),
            )
            msg += f"\n🎓 Acquisition complete ({done_n}/{target}) — {ex['name']} rejoins the queue."
        else:
            cur.execute("UPDATE exercise_items SET acq_sessions_done = %s WHERE id = %s", (done_n, ex_id))
            msg += f"\n📈 Acquisition {done_n}/{target}"
    _drop_premature_auto(cur, user_id, ex_id, tz)
    conn.commit()
    if not quiet:
        _send(chat_id, msg)
    _log(f"🏋️ Exercise done\n• {ex['name']}")


def _cmd_list(cur, user_id: int, chat_id: int) -> None:
    cur.execute(
        "SELECT name, schedule_type, repeat_interval_days, acq_interval_days, "
        "       acq_sessions_done, acq_target_sessions, status "
        "FROM exercise_items WHERE user_id = %s ORDER BY schedule_type, name",
        (user_id,),
    )
    rows = cur.fetchall()
    if not rows:
        _send(chat_id, "No exercises yet. Use /add.")
        return
    lines = ["🗂 All exercises:"]
    for r in rows:
        if r["schedule_type"] == "fixed":
            sched = f"fixed/{r['repeat_interval_days']}d"
        elif r["schedule_type"] == "acquisition":
            sched = f"acq {r['acq_sessions_done']}/{r['acq_target_sessions']}·{r['acq_interval_days']}d"
        else:
            sched = "queue"
        flag = "" if r["status"] == "active" else f" [{r['status']}]"
        lines.append(f"• {r['name']} — {sched}{flag}")
    _send(chat_id, "\n".join(lines))


def _cmd_status(cur, conn, user_id: int, chat_id: int, action: str, name: str) -> None:
    if not name:
        _send(chat_id, f"Usage: {action} <name>")
        return
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        _send(chat_id, f'No exercise named "{name}".')
        return
    new_status = {"pause": "paused", "park": "parked", "activate": "active"}[action]
    cur.execute("UPDATE exercise_items SET status = %s WHERE id = %s", (new_status, ex["id"]))
    conn.commit()
    _send(chat_id, f"{ex['name']} → {new_status}.")
    _log(f"🏋️ Exercise {new_status}\n• {ex['name']}")


def _cmd_remove(cur, conn, user_id: int, chat_id: int, name: str) -> None:
    if not name:
        _send(chat_id, "Usage: remove <name>")
        return
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        _send(chat_id, f'No exercise named "{name}".')
        return
    _send(chat_id, f"Delete {ex['name']}? This can't be undone.",
        reply_markup={"inline_keyboard": [[
            {"text": "🗑 Delete", "callback_data": f"ex:rmconfirm:{ex['name']}"},
            {"text": "Cancel", "callback_data": "ex:rmcancel"},
        ]]})


def _do_remove(cur, conn, user_id: int, chat_id: int, name: str) -> None:
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        _send(chat_id, f'No exercise named "{name}".')
        return
    cur.execute("DELETE FROM exercise_items WHERE id = %s", (ex["id"],))
    conn.commit()
    _send(chat_id, f"Removed {ex['name']}.")
    _log(f"🗑 Exercise removed\n• {ex['name']}")


def _cmd_stats(cur, user_id: int, chat_id: int, name: str) -> None:
    if not name:
        _send(chat_id, "Usage: stats <name>")
        return
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        _send(chat_id, f'No exercise named "{name}".')
        return
    cur.execute(
        "SELECT COUNT(*) AS n, MAX(done_at) AS last FROM exercise_history WHERE exercise_id = %s",
        (ex["id"],),
    )
    row = cur.fetchone()
    n = row["n"] or 0
    last = row["last"].strftime("%b %d, %Y") if row["last"] else "never"
    _send(chat_id, f"📊 {ex['name']}\n• times done: {n}\n• last: {last}")


def _cmd_history(cur, user_id: int, chat_id: int) -> None:
    cur.execute(
        "SELECT h.done_at, h.dose_actual, e.name FROM exercise_history h "
        "LEFT JOIN exercise_items e ON e.id = h.exercise_id "
        "WHERE h.user_id = %s ORDER BY h.done_at DESC LIMIT 10",
        (user_id,),
    )
    rows = cur.fetchall()
    if not rows:
        _send(chat_id, "No history yet.")
        return
    lines = ["🕘 Recent (last 10):"]
    for r in rows:
        when = r["done_at"].strftime("%b %d")
        actual = f" — {r['dose_actual']}" if r["dose_actual"] else ""
        lines.append(f"• {when}: {r['name'] or '(removed)'}{actual}")
    _send(chat_id, "\n".join(lines))


def _cmd_undo(cur, conn, user_id: int, chat_id: int) -> None:
    cur.execute(
        "SELECT id, exercise_id FROM exercise_history WHERE user_id = %s ORDER BY done_at DESC LIMIT 1",
        (user_id,),
    )
    last = cur.fetchone()
    if not last:
        _send(chat_id, "Nothing to undo.")
        return
    ex_id = last["exercise_id"]
    # Restore last_done_at to the prior history row for this exercise (or NULL).
    prior_done = None
    if ex_id is not None:
        cur.execute(
            "SELECT done_at FROM exercise_history WHERE exercise_id = %s AND id != %s "
            "ORDER BY done_at DESC LIMIT 1",
            (ex_id, last["id"]),
        )
        prior = cur.fetchone()
        prior_done = prior["done_at"] if prior else None
        cur.execute("UPDATE exercise_items SET last_done_at = %s WHERE id = %s", (prior_done, ex_id))
        # If currently mid-acquisition, roll the counter back by one.
        cur.execute(
            "UPDATE exercise_items SET acq_sessions_done = GREATEST(acq_sessions_done - 1, 0) "
            "WHERE id = %s AND schedule_type = 'acquisition'",
            (ex_id,),
        )
    cur.execute("DELETE FROM exercise_history WHERE id = %s", (last["id"],))
    conn.commit()
    _send(chat_id, "↩️ Reverted the last done.")


# ── Add flow ─────────────────────────────────────────────────────────────────

def _cmd_add_start(cur, conn, user_id: int, chat_id: int) -> None:
    _set_state(cur, conn, user_id, "ex_add:name", {})
    _send(chat_id, "New exercise — what's its name?")


def _ask_tier(cur, conn, user_id: int, chat_id: int, data: dict) -> None:
    """Last step of the add flow. Three questions total: name, description, tier."""
    _set_state(cur, conn, user_id, "ex_add:tier", data)
    _send(chat_id, "How often should it come up?", reply_markup={"inline_keyboard": [
        [{"text": "Tier 1 — most often", "callback_data": "ex:add:tier:1"}],
        [{"text": "Tier 2 — regular", "callback_data": "ex:add:tier:2"}],
        [{"text": "Tier 3 — occasional", "callback_data": "ex:add:tier:3"}],
    ]})


def _handle_state_input(cur, conn, user_id: int, chat_id: int, state: str, data: dict, text: str) -> bool:
    if text.lower() in ("cancel", "/cancel"):
        _clear_state(cur, conn, user_id)
        _send(chat_id, "Cancelled.")
        return True

    # ── Add flow text steps ──
    if state == "ex_add:name":
        if _get_ex_by_name(cur, user_id, text):
            _send(chat_id, f'"{text}" already exists — use `edit {text}` instead.')
            return True
        data["name"] = text
        _set_state(cur, conn, user_id, "ex_add:description", data)
        _send(chat_id, "Description? (or tap Skip)", reply_markup=_kb_skip())
        return True

    if state == "ex_add:description":
        data["description"] = text
        _ask_tier(cur, conn, user_id, chat_id, data)
        return True

    if state == "ex_add:interval":
        if not text.isdigit() or int(text) < 1:
            _send(chat_id, "Send a whole number of days (e.g. 2).")
            return True
        data["repeat_interval_days"] = int(text)
        _advance_to_focus(cur, conn, user_id, chat_id, data)
        return True

    if state == "ex_add:acq_interval":
        if not text.isdigit() or int(text) < 1:
            _send(chat_id, "Send a whole number of days.")
            return True
        data["acq_interval_days"] = int(text)
        _set_state(cur, conn, user_id, "ex_add:acq_target", data)
        _send(chat_id, "How many sessions to complete acquisition?", reply_markup=_kb_target())
        return True

    if state == "ex_add:acq_target":
        if not text.isdigit() or int(text) < 1:
            _send(chat_id, "Send a whole number of sessions.")
            return True
        data["acq_target_sessions"] = int(text)
        _advance_to_focus(cur, conn, user_id, chat_id, data)
        return True

    if state == "ex_add:focus":
        data["focus_area"] = text
        _set_state(cur, conn, user_id, "ex_add:location", data)
        _send(chat_id, "Where can you do it?", reply_markup=_kb_location())
        return True

    if state == "ex_add:equipment":
        data["equipment"] = text
        _set_state(cur, conn, user_id, "ex_add:load", data)
        _send(chat_id, "Load tag?", reply_markup=_kb_load())
        return True

    # ── Keyboard-only add steps: accept a typed enum value, else re-prompt.
    #    Critically, do NOT fall through to the catch-all clear — that would wipe
    #    the whole in-progress add flow just because the user typed instead of tapped.
    if state == "ex_add:schedule":
        val = text.strip().lower()
        if val in _SCHEDULES:
            _apply_schedule_choice(cur, conn, user_id, chat_id, data, val)
        else:
            _send(chat_id, "Please pick a schedule using the buttons.", reply_markup=_kb_schedule())
        return True

    if state == "ex_add:location":
        val = text.strip().lower()
        if val in _LOCATIONS:
            data["location"] = val
            _set_state(cur, conn, user_id, "ex_add:equipment", data)
            _send(chat_id, "Equipment? (e.g. band, or Skip)", reply_markup=_kb_skip())
        else:
            _send(chat_id, "Please tap a location: anywhere / outdoors / gym.", reply_markup=_kb_location())
        return True

    if state == "ex_add:load":
        val = text.strip().lower()
        if val in _LOAD_TAGS:
            data["load_tag"] = val
            _set_state(cur, conn, user_id, "ex_add:confirm", data)
            _send(chat_id, _add_confirm_text(data), reply_markup=_kb_confirm())
        else:
            _send(chat_id, "Please tap a load tag: easy / upper / lower / systemic.", reply_markup=_kb_load())
        return True

    if state == "ex_add:confirm":
        _send(chat_id, "Tap Save or Cancel below.", reply_markup=_kb_confirm())
        return True

    # ── Edit flow text step ──
    if state.startswith("ex_edit_val:"):
        _, field, ex_id = state.split(":", 2)
        return _apply_edit_value(cur, conn, user_id, chat_id, int(ex_id), field, text)

    # Mid-add unknown state — re-prompt without wiping progress. Only genuinely
    # orphaned states (not part of an active flow) get cleared.
    if state.startswith("ex_add:"):
        _send(chat_id, "Use the buttons above, or send `cancel` to abandon this exercise.")
        return True
    _clear_state(cur, conn, user_id)
    return False


def _apply_schedule_choice(cur, conn, user_id: int, chat_id: int, data: dict, choice: str) -> None:
    """Advance the add flow after a schedule type is chosen (tapped or typed)."""
    data["schedule_type"] = choice
    if choice == "fixed":
        _set_state(cur, conn, user_id, "ex_add:interval", data)
        _send(chat_id, "Repeat every how many days? (tap or type)", reply_markup=_kb_interval("ex:add:interval"))
    elif choice == "acquisition":
        _set_state(cur, conn, user_id, "ex_add:acq_interval", data)
        _send(chat_id, "Acquisition cadence — every how many days?", reply_markup=_kb_interval("ex:add:acqint"))
    else:
        _advance_to_focus(cur, conn, user_id, chat_id, data)


def _handle_add_callback(cur, conn, user_id: int, chat_id: int, msg_id: int, sub: str) -> None:
    state, data = _get_state(cur, user_id)

    if sub == "cancel":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _clear_state(cur, conn, user_id)
        _send(chat_id, "Cancelled.")
        return

    if sub == "skip":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if state == "ex_add:description":
            data["description"] = None
            _ask_tier(cur, conn, user_id, chat_id, data)
        elif state == "ex_add:focus":
            data["focus_area"] = None
            _set_state(cur, conn, user_id, "ex_add:location", data)
            _send(chat_id, "Where can you do it?", reply_markup=_kb_location())
        elif state == "ex_add:equipment":
            data["equipment"] = None
            _set_state(cur, conn, user_id, "ex_add:load", data)
            _send(chat_id, "Load tag?", reply_markup=_kb_load())
        return

    if sub.startswith("tier:"):
        data["tier"] = int(sub[len("tier:"):])
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _save_new_exercise(cur, conn, user_id, chat_id, data)
        return

    if sub.startswith("sched:"):
        choice = sub[len("sched:"):]
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _apply_schedule_choice(cur, conn, user_id, chat_id, data, choice)
        return

    if sub.startswith("interval:"):
        data["repeat_interval_days"] = int(sub[len("interval:"):])
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _advance_to_focus(cur, conn, user_id, chat_id, data)
        return

    if sub.startswith("acqint:"):
        data["acq_interval_days"] = int(sub[len("acqint:"):])
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _set_state(cur, conn, user_id, "ex_add:acq_target", data)
        _send(chat_id, "How many sessions to complete acquisition?", reply_markup=_kb_target())
        return

    if sub.startswith("acqtarget:"):
        data["acq_target_sessions"] = int(sub[len("acqtarget:"):])
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _advance_to_focus(cur, conn, user_id, chat_id, data)
        return

    if sub.startswith("loc:"):
        data["location"] = sub[len("loc:"):]
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _set_state(cur, conn, user_id, "ex_add:equipment", data)
        _send(chat_id, "Equipment? (e.g. band, or Skip)", reply_markup=_kb_skip())
        return

    if sub.startswith("load:"):
        data["load_tag"] = sub[len("load:"):]
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _set_state(cur, conn, user_id, "ex_add:confirm", data)
        _send(chat_id, _add_confirm_text(data), reply_markup=_kb_confirm())
        return

    if sub == "save":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _save_new_exercise(cur, conn, user_id, chat_id, data)
        return


def _save_new_exercise(cur, conn, user_id: int, chat_id: int, d: dict) -> None:
    # Guard against a corrupted flow reaching Save without a name. There is no
    # schedule to validate any more -- everything is a queue item.
    if not d.get("name"):
        _clear_state(cur, conn, user_id)
        _send(chat_id, "Something went wrong with that entry — please /add it again.")
        return
    cur.execute(
        "INSERT INTO exercise_items (user_id, name, description, tier, schedule_type, location) "
        "VALUES (%s, %s, %s, %s, 'queue', %s) "
        "ON CONFLICT (user_id, name) DO NOTHING RETURNING id",
        (user_id, d.get("name"), d.get("description"), int(d.get("tier") or 2), _LOCATION_ANY),
    )
    saved = cur.fetchone()
    _clear_state(cur, conn, user_id)
    if not saved:
        _send(chat_id, f'"{d.get("name")}" already exists.')
        return
    conn.commit()
    _send(chat_id, f"✅ Saved {d.get('name')} — tier {int(d.get('tier') or 2)}.")
    _log(f"🏋️ Exercise added\n• {d.get('name')} (tier {int(d.get('tier') or 2)})")


# ── Edit flow ────────────────────────────────────────────────────────────────

_EDITABLE_TEXT = ("name", "description", "focus_area", "equipment")


def _cmd_edit(cur, conn, user_id: int, chat_id: int, name: str) -> None:
    if not name:
        _send(chat_id, "Usage: edit <name>")
        return
    ex = _get_ex_by_name(cur, user_id, name)
    if not ex:
        _send(chat_id, f'No exercise named "{name}".')
        return
    exid = ex["id"]
    # Three fields, matching the web form. The old descriptive fields still hold
    # data on existing items, but nothing offers them for editing any more.
    rows = [
        [{"text": "Name", "callback_data": f"ex:edit:field:name:{exid}"},
         {"text": "Description", "callback_data": f"ex:edit:field:description:{exid}"}],
        [{"text": f"Tier (now {ex['tier']})", "callback_data": f"ex:edit:pick:tier:{exid}"}],
        [{"text": "Cancel", "callback_data": "ex:edit:cancel"}],
    ]
    _send(chat_id, f"Editing {ex['name']} — which field?", reply_markup={"inline_keyboard": rows})


def _cmd_tier(cur, conn, user_id: int, chat_id: int, args: list[str]) -> None:
    """`tier <name> <1|2|3>` — set it outright; `tier <name>` — pick from buttons.

    The tier is the one thing likely to be adjusted from the phone, mid-day,
    while noticing something comes up too rarely. Walking the edit menu for that
    is three taps too many.
    """
    if not args:
        _send(chat_id, "Usage: tier <name> [1|2|3]")
        return
    level = None
    if args[-1] in ("1", "2", "3"):
        level, args = args[-1], args[:-1]
    name = " ".join(args).strip()
    ex = _get_ex_by_name(cur, user_id, name) if name else None
    if not ex:
        _send(chat_id, f'No exercise named "{name}".' if name else "Usage: tier <name> [1|2|3]")
        return
    if level is None:
        _send(chat_id, f"{ex['name']} is tier {ex['tier']}. Set it to:",
              reply_markup={"inline_keyboard": [
                  [{"text": lbl, "callback_data": f"ex:edit:setval:tier:{ex['id']}:{n}"}]
                  for n, lbl in (("1", "1 — most often"), ("2", "2 — regular"),
                                 ("3", "3 — occasional"))]})
        return
    cur.execute("UPDATE exercise_items SET tier = %s WHERE id = %s AND user_id = %s",
                (int(level), ex["id"], user_id))
    conn.commit()
    _send(chat_id, f"✓ {ex['name']} is now tier {level}.")


def _handle_edit_callback(cur, conn, user_id: int, chat_id: int, msg_id: int, sub: str) -> None:
    if sub == "cancel":
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _clear_state(cur, conn, user_id)
        _send(chat_id, "Cancelled.")
        return

    if sub.startswith("field:"):
        _, field, ex_id = sub.split(":", 2)
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _set_state(cur, conn, user_id, f"ex_edit_val:{field}:{ex_id}", {})
        _send(chat_id, f"Send the new {field}:")
        return

    if sub.startswith("pick:"):
        _, field, ex_id = sub.split(":", 2)
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if field == "tier":
            opts = ["1", "2", "3"]
            labels = {"1": "1 — most often", "2": "2 — regular", "3": "3 — occasional"}
        else:
            opts = _LOCATIONS if field == "location" else _LOAD_TAGS
            labels = {}
        rows = [[{"text": labels.get(o, o),
                  "callback_data": f"ex:edit:setval:{field}:{ex_id}:{o}"}] for o in opts]
        _send(chat_id, f"Pick {field}:", reply_markup={"inline_keyboard": rows})
        return

    if sub.startswith("setval:"):
        _, field, ex_id, value = sub.split(":", 3)
        _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _apply_edit_value(cur, conn, user_id, chat_id, int(ex_id), field, value)
        return


def _apply_edit_value(cur, conn, user_id: int, chat_id: int, ex_id: int, field: str, value: str) -> bool:
    if field == "name":
        existing = _get_ex_by_name(cur, user_id, value)
        if existing and existing["id"] != ex_id:
            _send(chat_id, f'"{value}" is already taken.')
            return True
        newval: object = value
    else:
        newval = value

    cur.execute(
        f"UPDATE exercise_items SET {field} = %s WHERE id = %s AND user_id = %s",
        (newval, ex_id, user_id),
    )
    conn.commit()
    _clear_state(cur, conn, user_id)
    _send(chat_id, f"✓ Updated {field}.")
    return True


# ── Daily report (cron + self-editing buttons) ───────────────────────────────

def _collect_day(cur, user_id: int, tz, day):
    """Everything on `day`: committed calendar rows plus cadence-due items that
    have no row yet. Each entry carries its status so the report can show
    progress (✓ / ⏭ / pending)."""
    cur.execute(
        "SELECT s.exercise_id AS id, s.status, e.name FROM exercise_schedule s "
        "JOIN exercise_items e ON e.id = s.exercise_id "
        "WHERE s.user_id = %s AND s.scheduled_date = %s",
        (user_id, day),
    )
    items = {r["id"]: {"id": r["id"], "name": r["name"], "status": r["status"]} for r in cur.fetchall()}

    cur.execute(
        "SELECT * FROM exercise_items WHERE user_id = %s AND status = 'active' "
        "AND schedule_type IN ('fixed', 'acquisition')",
        (user_id,),
    )
    for e in cur.fetchall():
        if e["id"] in items:
            continue  # a committed row wins over its own suggestion
        if _next_due_date(e, tz, day) == day:
            items[e["id"]] = {"id": e["id"], "name": e["name"], "status": "planned"}
    return sorted(items.values(), key=lambda x: x["name"].lower())


def _queue_items(cur, user_id: int, handled_ids: set):
    cur.execute(
        "SELECT id, name, load_tag FROM exercise_items "
        "WHERE user_id = %s AND schedule_type = 'queue' AND status = 'active' "
        "  AND (skipped_until IS NULL OR skipped_until <= NOW()) "
        "ORDER BY last_done_at ASC NULLS FIRST, created_at ASC LIMIT 10",
        (user_id,),
    )
    return [r for r in cur.fetchall() if r["id"] not in handled_ids]


def _daily_report(cur, user_id: int, tz, day):
    """(text, keyboard, has_content) for the daily report. Rebuilt after every
    button press so the message edits itself in place."""
    today_items = _collect_day(cur, user_id, tz, day)
    tomorrow_items = _collect_day(cur, user_id, tz, day + timedelta(days=1))
    handled = {i["id"] for i in today_items if i["status"] in ("done", "skipped")}
    queue = _queue_items(cur, user_id, handled)

    done_n = sum(1 for i in today_items if i["status"] == "done")
    pending = [i for i in today_items if i["status"] == "planned"]

    lines = [f"🗓 Daily report — {day.strftime('%a %d %b')}", ""]
    if today_items:
        lines.append(f"✅ TODAY — {done_n}/{len(today_items)} done")
        for i in today_items:
            mark = {"done": "✓", "skipped": "⏭"}.get(i["status"], "•")
            lines.append(f"{mark} {i['name']}")
        lines.append("")
    if tomorrow_items:
        lines.append("📌 TOMORROW")
        lines.append(" · ".join(i["name"] for i in tomorrow_items))
        lines.append("")
    if queue:
        lines.append(f"📋 QUEUE ({len(queue)})")
        lines.append(" · ".join(f"{q['name']}" for q in queue))
    if today_items and not pending:
        lines.append("")
        lines.append("🎉 All clear for today.")

    rows = []
    for i in pending:                                    # ✓ / ⏭ per pending item
        rows.append([
            {"text": f"✓ {i['name']}", "callback_data": f"ex:tdone:{i['id']}:{day}"},
            {"text": "⏭", "callback_data": f"ex:tskip:{i['id']}:{day}"},
        ])
    row = []
    for q in queue:                                      # ✓ only, two per row
        row.append({"text": f"✓ {q['name']}", "callback_data": f"ex:tdone:{q['id']}:{day}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    has_content = bool(today_items or tomorrow_items or queue)
    return "\n".join(lines), ({"inline_keyboard": rows} if rows else None), has_content


def send_exercise_overview(conn) -> None:
    """Morning daily report: today's plan with ✓/⏭, tomorrow previewed, queue to tick off.
    Wired into the shared daily cron at 06:00 UTC = 08:00 Europe/Berlin."""
    cur = conn.cursor()
    cur.execute("SELECT id, telegram_user_id, chat_id FROM exercise_users")
    for u in cur.fetchall():
        user_id = u["id"]
        chat_id = u["chat_id"] or u["telegram_user_id"]
        tz = _user_tz(cur, user_id)
        # Lock today in first: up to now it was fluid, from here it's committed.
        today = datetime.now(tz).date()
        _lock_in(cur, user_id, tz, today)
        text, kb, has_content = _daily_report(cur, user_id, tz, today)
        if not has_content:
            continue
        _send(chat_id, text, reply_markup=kb)
    conn.commit()
