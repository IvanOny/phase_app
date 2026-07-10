from __future__ import annotations

import json
import os
import re as _re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone, timedelta

_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_API = f"https://api.telegram.org/bot{_TOKEN}"
_LOG_CHAT_ID = os.environ.get("LOG_CHAT_ID", "")


def _build_token(name: str, secret: str | None) -> str:
    slug = name.lower().replace(" ", "-")
    if secret:
        slug += "-" + secret.lower().replace(" ", "-")
    return f"бурчик-{slug}"


def _tg(method: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_API}/{method}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=8)
    except urllib.error.HTTPError as e:
        print(f"Telegram API error [{method}]: {e.code} {e.read().decode()}")
    except Exception as e:
        print(f"Telegram API error [{method}]: {e}")


def _log(text: str) -> None:
    if not _LOG_CHAT_ID:
        return
    ts = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
    try:
        _tg("sendMessage", {"chat_id": int(_LOG_CHAT_ID), "text": f"[{ts}]\n{text}"})
    except Exception:
        pass


def _send(chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    payload: dict = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _tg("sendMessage", payload)


def _forward(from_chat_id: int, message_id: int, to_chat_id: int) -> None:
    _tg("copyMessage", {
        "chat_id": to_chat_id,
        "from_chat_id": from_chat_id,
        "message_id": message_id,
    })


def _lookup_user(cur, tg_id: int) -> str | None:
    cur.execute(
        "SELECT participant_name FROM telegram_bot_users WHERE telegram_user_id = %s",
        (tg_id,),
    )
    row = cur.fetchone()
    return row["participant_name"] if row else None


_STATE_TIMEOUT_MINUTES = 10


def _get_state(cur, tg_id: int) -> str | None:
    cur.execute(
        "SELECT state, created_at FROM telegram_bot_state WHERE telegram_user_id = %s",
        (tg_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    if row["created_at"] and (datetime.now(timezone.utc) - row["created_at"]).total_seconds() > _STATE_TIMEOUT_MINUTES * 60:
        cur.execute("DELETE FROM telegram_bot_state WHERE telegram_user_id = %s", (tg_id,))
        return None
    return row["state"]


def _set_state(cur, tg_id: int, state: str) -> None:
    cur.execute(
        "INSERT INTO telegram_bot_state (telegram_user_id, state, created_at) VALUES (%s, %s, NOW()) "
        "ON CONFLICT (telegram_user_id) DO UPDATE SET state = EXCLUDED.state, created_at = NOW()",
        (tg_id, state),
    )


def _clear_state(cur, tg_id: int) -> None:
    cur.execute("DELETE FROM telegram_bot_state WHERE telegram_user_id = %s", (tg_id,))


def _greet(cur, tg_id: int, participant: str) -> str:
    """Returns 'Name, ' on first message of the day, '' afterwards."""
    cur.execute(
        "SELECT last_greeted FROM telegram_bot_users WHERE telegram_user_id = %s",
        (tg_id,),
    )
    row = cur.fetchone()
    today = str(date.today())
    if row and row["last_greeted"] and str(row["last_greeted"]) == today:
        return ""
    cur.execute(
        "UPDATE telegram_bot_users SET last_greeted = %s WHERE telegram_user_id = %s",
        (today, tg_id),
    )
    return f"{participant}, "


def _all_other_names(cur, tg_id: int) -> list[str]:
    cur.execute(
        "SELECT participant_name FROM telegram_bot_users WHERE telegram_user_id != %s ORDER BY participant_name",
        (tg_id,),
    )
    return [r["participant_name"] for r in cur.fetchall()]


# ── Share (send to) ──────────────────────────────────────────────────────────

def _get_share_set(cur, tg_id: int) -> set[str]:
    cur.execute(
        "SELECT notify_participant FROM telegram_bot_notify WHERE telegram_user_id = %s",
        (tg_id,),
    )
    return {r["notify_participant"] for r in cur.fetchall()}


def _get_share_chats(cur, tg_id: int) -> list[tuple[int, str]]:
    """Returns (chat_id, name) for users this sender wants to notify AND who accept from sender's name."""
    stored = _get_share_set(cur, tg_id)
    has_all = "__all__" in stored
    if has_all:
        cur.execute(
            "SELECT chat_id, participant_name FROM telegram_bot_users WHERE telegram_user_id != %s",
            (tg_id,),
        )
    else:
        cur.execute(
            "SELECT u.chat_id, u.participant_name "
            "FROM telegram_bot_notify n "
            "JOIN telegram_bot_users u ON u.participant_name = n.notify_participant "
            "WHERE n.telegram_user_id = %s",
            (tg_id,),
        )
    candidates = [(r["chat_id"], r["participant_name"]) for r in cur.fetchall()]
    sender_name = _lookup_user(cur, tg_id)
    result = []
    for chat_id, name in candidates:
        cur.execute("SELECT telegram_user_id FROM telegram_bot_users WHERE participant_name = %s", (name,))
        row = cur.fetchone()
        if not row:
            continue
        rid = row["telegram_user_id"]
        # Skip paused recipients
        cur.execute(
            "SELECT paused_until FROM telegram_bot_users WHERE telegram_user_id = %s",
            (rid,),
        )
        pause_row = cur.fetchone()
        if pause_row and pause_row["paused_until"] and pause_row["paused_until"] > datetime.now(timezone.utc):
            continue
        # Skip recipients who have muted this sender
        cur.execute(
            "SELECT 1 FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s AND muted_until > NOW()",
            (rid, sender_name),
        )
        if cur.fetchone():
            continue
        cur.execute(
            "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s LIMIT 1",
            (rid,),
        )
        has_receive_list = cur.fetchone() is not None
        if has_receive_list:
            cur.execute(
                "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s "
                "AND (receive_participant = %s OR receive_participant = '__all__')",
                (rid, sender_name),
            )
            if not cur.fetchone():
                continue
        result.append((chat_id, name))
    return result


def _share_keyboard(cur, tg_id: int) -> dict:
    stored = _get_share_set(cur, tg_id)
    has_all = "__all__" in stored
    others = _all_other_names(cur, tg_id)
    rows = []
    rows.append([{"text": "✓ Anyone" if has_all else "Anyone", "callback_data": "share:__all__"}])
    for p in others:
        label = f"✓ {p}" if (has_all or p in stored) else p
        rows.append([{"text": label, "callback_data": f"share:{p}"}])
    rows.append([{"text": "Done", "callback_data": "share:done"}])
    return {"inline_keyboard": rows}


# ── Follow (accept from) ─────────────────────────────────────────────────────

def _get_follow_set(cur, tg_id: int) -> set[str]:
    cur.execute(
        "SELECT receive_participant FROM telegram_bot_receive WHERE telegram_user_id = %s",
        (tg_id,),
    )
    return {r["receive_participant"] for r in cur.fetchall()}


_MAIN_KB = {
    "keyboard": [
        [{"text": "🤝 Sweat with"}, {"text": "📡 Radar"}],
        [{"text": "⏸️ Pause"}, {"text": "ℹ️ Info"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}


def _pause_keyboard(is_paused: bool) -> dict:
    rows = [
        [{"text": "1 day",   "callback_data": "pause:1d"}],
        [{"text": "1 week",  "callback_data": "pause:1w"}],
        [{"text": "1 month", "callback_data": "pause:1m"}],
    ]
    if is_paused:
        rows.append([{"text": "▶️ Resume now", "callback_data": "pause:resume"}])
    return {"inline_keyboard": rows}

_REPS_RE = _re.compile(r"^(\d+)\s*(.*)", _re.DOTALL)


def _parse_reps(text: str) -> tuple[int, str] | None:
    m = _REPS_RE.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip()


_RADAR_FREQS = ["daily", "weekly", "monthly", "once", "never"]
_RADAR_LABELS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly", "once": "Just once", "never": "Off"}
_RADAR_PERIOD = {"daily": "every day", "weekly": "every week", "monthly": "every month"}

def _radar_keyboard(current: str, radar_send: bool | None = None) -> dict:
    rows = []
    for freq in _RADAR_FREQS:
        label = ("✓ " if freq == current else "") + _RADAR_LABELS[freq]
        rows.append([{"text": label, "callback_data": f"radar:{freq}"}])
    if radar_send is not None:
        rows.append([
            {"text": ("✓ " if radar_send else "") + "📡 Share my videos: ON ✅", "callback_data": "radar_send_toggle:on"},
            {"text": ("✓ " if not radar_send else "") + "📡 Share my videos: OFF 🚫", "callback_data": "radar_send_toggle:off"},
        ])
    return {"inline_keyboard": rows}

_RADAR_SEND_KB = {"inline_keyboard": [
    [{"text": "✅ Yes, that's fine", "callback_data": "radar_send:yes"}],
    [{"text": "🚫 No, keep my videos in my crew", "callback_data": "radar_send:no"}],
]}

def _radar_due(freq: str, last_received) -> bool:
    if freq == "never":
        return False
    if last_received is None:
        return True
    now = datetime.now(timezone.utc)
    if freq == "daily":
        return last_received.date() < now.date()
    if freq == "weekly":
        return (now - last_received) >= timedelta(weeks=1)
    if freq == "monthly":
        return (now - last_received) >= timedelta(days=30)
    if freq == "once":
        return False  # already received once, disable handled at send time
    return False


def _sweat_manage_keyboard(name: str, muted_until=None) -> dict:
    rows = []
    if muted_until:
        until_str = muted_until.strftime("%b %d")
        rows.append([{"text": f"▶️ Unmute (muted until {until_str})", "callback_data": f"sweat_manage:unmute:{name}"}])
    rows.append([
        {"text": "🔕 Mute 1 day",   "callback_data": f"sweat_manage:mute_1d:{name}"},
        {"text": "🔕 Mute 1 week",  "callback_data": f"sweat_manage:mute_1w:{name}"},
        {"text": "🔕 Mute 1 month", "callback_data": f"sweat_manage:mute_1m:{name}"},
    ])
    rows.append([{"text": "🗑 Remove from sweat list", "callback_data": f"sweat_manage:remove:{name}"}])
    rows.append([{"text": "Cancel", "callback_data": "sweat_manage:cancel"}])
    return {"inline_keyboard": rows}


def _follow_keyboard(cur, tg_id: int) -> dict:
    stored = _get_follow_set(cur, tg_id)
    has_all = "__all__" in stored
    others = _all_other_names(cur, tg_id)
    rows = []
    rows.append([{"text": "✓ Anyone" if has_all else "Anyone", "callback_data": "follow:__all__"}])
    for p in others:
        label = f"✓ {p}" if (has_all or p in stored) else p
        rows.append([{"text": label, "callback_data": f"follow:{p}"}])
    rows.append([{"text": "Done", "callback_data": "follow:done"}])
    return {"inline_keyboard": rows}


# ── Entry logging + forwarding ───────────────────────────────────────────────

def _parse_reps_comment(text: str) -> tuple[int | None, str | None]:
    """Parse '[preamble] reps [, comment]'. Returns (reps, comment) or (None, None).
    Requires a comma to separate the comment; without comma only pure integers match."""
    if ',' in text:
        before, after = text.split(',', 1)
        comment = after.strip() or None
        m = _re.search(r'\d+', before)
        return (int(m.group()), comment) if m else (None, None)
    return (int(text), None) if text.isdigit() else (None, None)


def _log_entry(cur, participant: str, reps: int, comment: str | None = None) -> None:
    cur.execute(
        "INSERT INTO burpee_entries (participant, entry_date, reps, comment) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (participant, entry_date) DO UPDATE SET reps = EXCLUDED.reps, comment = EXCLUDED.comment",
        (participant, str(date.today()), reps, comment),
    )
    cur.execute(
        "UPDATE telegram_bot_users SET radar_score = radar_score + 1 WHERE participant_name = %s",
        (participant,),
    )


def _do_forward(cur, conn, tg_id: int, participant: str, from_chat_id: int, message_id: int | None, reps: int, comment: str | None = None) -> None:
    targets = _get_share_chats(cur, tg_id)
    conn.commit()
    for to_chat_id, name in targets:
        if message_id:
            _forward(from_chat_id, message_id, to_chat_id)
        crew_msg = f"{participant}: {reps} reps"
        if comment:
            crew_msg += f"\n{comment}"
        _send(to_chat_id, crew_msg)
    confirm = f"✓ {reps} reps" + (f" ({comment})" if comment else "")
    if targets:
        forwarded_to = ", ".join(n for _, n in targets)
        _send(from_chat_id, f"{confirm} → forwarded to {forwarded_to}", reply_markup=_MAIN_KB)
        _log(f"💪 Video logged\n👤 {participant}: {reps} reps\n📤 → {forwarded_to}")
    else:
        _send(from_chat_id, f"{confirm} logged", reply_markup=_MAIN_KB)
        _log(f"💪 Video logged\n👤 {participant}: {reps} reps\n📤 → nobody")

    # ── Radar: queue this video as a candidate (only if user opted in to sending) ──
    cur.execute("SELECT radar_send FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    if row and row["radar_send"]:
        cur.execute(
            "INSERT INTO radar_candidates "
            "(telegram_user_id, chat_id, message_id, participant_name, reps, candidate_date) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (telegram_user_id, candidate_date) DO UPDATE "
            "SET message_id = EXCLUDED.message_id, reps = EXCLUDED.reps, "
            "    chat_id = EXCLUDED.chat_id, processed = FALSE",
            (tg_id, from_chat_id, message_id, participant, reps, date.today()),
        )


_REPORT_CHAT_ID = os.environ.get("LOG_CHAT_ID", "")


def _compute_streak(entries_desc: list) -> tuple:
    """Returns (streak_days, last_date, last_reps). streak_days=0 means broken."""
    if not entries_desc:
        return 0, None, None
    today = date.today()
    last_date = entries_desc[0]["entry_date"]
    last_reps = entries_desc[0]["reps"]
    if isinstance(last_date, str):
        from datetime import datetime as _dt
        last_date = _dt.strptime(last_date, "%Y-%m-%d").date()
    if (today - last_date).days > 1:
        return 0, last_date, last_reps
    streak = 0
    expected = last_date
    for row in entries_desc:
        d = row["entry_date"]
        if isinstance(d, str):
            from datetime import datetime as _dt
            d = _dt.strptime(d, "%Y-%m-%d").date()
        if d == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        else:
            break
    return streak, last_date, last_reps


def send_daily_report(conn) -> None:
    """Called by the 17:00 UTC (19:00 UTC+2) cron. Sends a streak report to the REPORT_CHAT_ID channel."""
    if not _REPORT_CHAT_ID:
        return
    cur = conn.cursor()
    today = date.today()

    # Dedup guard — Vercel may retry the cron endpoint; only send once per day
    cur.execute(
        "INSERT INTO cron_log (job_name, run_date) VALUES ('daily_report', %s) "
        "ON CONFLICT DO NOTHING RETURNING job_name",
        (today,),
    )
    if not cur.fetchone():
        return  # already sent today
    conn.commit()

    cur.execute("SELECT participant_name FROM telegram_bot_users ORDER BY participant_name")
    users = [r["participant_name"] for r in cur.fetchall()]
    if not users:
        return

    cur.execute(
        "SELECT participant, entry_date, reps FROM burpee_entries "
        "WHERE participant = ANY(%s) ORDER BY participant, entry_date DESC",
        (users,),
    )
    entries_by_user: dict[str, list] = {}
    for row in cur.fetchall():
        entries_by_user.setdefault(row["participant"], []).append(row)

    user_stats = []
    for user in users:
        entries = entries_by_user.get(user, [])
        streak, last_date, last_reps = _compute_streak(entries)
        if streak > 0:
            line = (f"🔥 {user} — {streak}-day streak ({last_reps} reps today)"
                    if (today - last_date).days == 0
                    else f"🔥 {user} — {streak}-day streak")
        elif last_date:
            days_ago = (today - last_date).days
            day_word = "day" if days_ago == 1 else "days"
            line = f"❌ {user} — {days_ago} {day_word} without workout (last: {last_reps} reps on {last_date.strftime('%b %d')})"
        else:
            line = f"😴 {user} — no workouts yet"
        user_stats.append((streak, line))

    user_stats.sort(key=lambda x: x[0], reverse=True)
    lines = [f"📊 Burpee Report — {today.strftime('%B %d')}\n"] + [line for _, line in user_stats]

    _tg("sendMessage", {"chat_id": int(_REPORT_CHAT_ID), "text": "\n".join(lines)})
    _log(f"📊 Daily report sent to channel")


def _store_or_bind_video(cur, conn, tg_id: int, participant: str, chat_id: int, message_id: int) -> None:
    """Store a video as pending (ask for reps), or bind it to reps logged within the last hour."""
    cur.execute(
        "SELECT reps, comment FROM telegram_bot_pending "
        "WHERE telegram_user_id = %s AND message_id IS NULL AND reps IS NOT NULL "
        "AND created_at > NOW() - INTERVAL '1 hour'",
        (tg_id,),
    )
    pending_reps = cur.fetchone()
    if pending_reps:
        reps = pending_reps["reps"]
        comment = pending_reps["comment"]
        cur.execute("DELETE FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
        _do_forward(cur, conn, tg_id, participant, chat_id, message_id, reps, comment)
    else:
        cur.execute(
            "INSERT INTO telegram_bot_pending (telegram_user_id, chat_id, message_id, reps) "
            "VALUES (%s, %s, %s, NULL) ON CONFLICT (telegram_user_id) "
            "DO UPDATE SET message_id = EXCLUDED.message_id, chat_id = EXCLUDED.chat_id, "
            "    reps = NULL, created_at = NOW()",
            (tg_id, chat_id, message_id),
        )
        conn.commit()
        _send(chat_id, f"{_greet(cur, tg_id, participant)}how many reps?")


def process_radar_candidates(conn) -> None:
    """Called by the 19:00 UTC cron. Picks the best candidate per recipient and forwards."""
    cur = conn.cursor()
    today = date.today()

    cur.execute(
        "SELECT rc.id, rc.telegram_user_id, rc.chat_id, rc.message_id, "
        "       rc.participant_name, rc.reps, u.radar_score "
        "FROM radar_candidates rc "
        "JOIN telegram_bot_users u ON u.telegram_user_id = rc.telegram_user_id "
        "WHERE rc.candidate_date = %s AND rc.processed = FALSE AND u.radar_send = TRUE "
        "ORDER BY u.radar_score DESC",
        (today,),
    )
    candidates = cur.fetchall()

    if candidates:
        cur.execute(
            "SELECT telegram_user_id, chat_id, participant_name, radar_freq, radar_last_received, paused_until "
            "FROM telegram_bot_users WHERE radar_freq != 'never'",
        )
        recipients = cur.fetchall()

        for recipient in recipients:
            freq = recipient["radar_freq"]
            paused_until = recipient.get("paused_until")
            if paused_until and paused_until > datetime.now(timezone.utc):
                continue
            if not _radar_due(freq, recipient["radar_last_received"]):
                continue

            cur.execute(
                "SELECT notify_participant AS name FROM telegram_bot_notify "
                "WHERE telegram_user_id = %s AND notify_participant != '__all__' "
                "UNION "
                "SELECT receive_participant AS name FROM telegram_bot_receive "
                "WHERE telegram_user_id = %s AND receive_participant != '__all__'",
                (recipient["telegram_user_id"], recipient["telegram_user_id"]),
            )
            sweat_names = {r["name"] for r in cur.fetchall()} | {recipient["participant_name"]}

            cur.execute(
                "SELECT sender_participant FROM radar_history "
                "WHERE recipient_telegram_user_id = %s AND sent_at > NOW() - INTERVAL '7 days'",
                (recipient["telegram_user_id"],),
            )
            recent_senders = {r["sender_participant"] for r in cur.fetchall()}

            best = next(
                (c for c in candidates
                 if c["participant_name"] not in sweat_names
                 and c["participant_name"] not in recent_senders),
                None,
            )
            if not best:
                continue

            is_first = recipient["radar_last_received"] is None
            if is_first:
                if freq == "once":
                    explanation = (
                        f"📡 {best['participant_name']}: {best['reps']} reps\n"
                        "You're getting this because your radar is on — a burpee from outside your crew. "
                        "According to your radar settings you'll get 1 burpee bubble, just once. "
                        "Use /radar to adjust frequency."
                    )
                else:
                    period = _RADAR_PERIOD.get(freq, freq)
                    explanation = (
                        f"📡 {best['participant_name']}: {best['reps']} reps\n"
                        "You're getting this because your radar is on — a burpee from outside your crew. "
                        f"According to your radar settings you will get 1 random burpee bubble {period}. "
                        "Use /radar to adjust frequency."
                    )
            else:
                explanation = (
                    f"📡 {best['participant_name']}: {best['reps']} reps\n"
                    "Your Radar detected some burpee activity from someone outside your crew."
                )

            _send(recipient["chat_id"], explanation)
            if best["message_id"]:
                _forward(best["chat_id"], best["message_id"], recipient["chat_id"])

            new_freq = "never" if freq == "once" else freq
            cur.execute(
                "UPDATE telegram_bot_users SET radar_last_received = NOW(), radar_freq = %s "
                "WHERE telegram_user_id = %s",
                (new_freq, recipient["telegram_user_id"]),
            )
            cur.execute(
                "UPDATE telegram_bot_users SET radar_score = radar_score - 10 "
                "WHERE telegram_user_id = %s",
                (best["telegram_user_id"],),
            )
            cur.execute(
                "INSERT INTO radar_history (sender_participant, recipient_telegram_user_id) "
                "VALUES (%s, %s)",
                (best["participant_name"], recipient["telegram_user_id"]),
            )
            _log(
                f"📡 Radar forward (cron)\n"
                f"💪 {best['participant_name']}: {best['reps']} reps → {recipient['participant_name']} ({freq})\n"
                f"📊 sender score: {best['radar_score']} → {best['radar_score'] - 10}"
            )

    cur.execute("UPDATE radar_candidates SET processed = TRUE WHERE candidate_date = %s", (today,))
    conn.commit()


# ── Webhook handler ──────────────────────────────────────────────────────────

def handle_webhook(body: dict, conn) -> None:
    cur = conn.cursor()

    # ── Callback queries ─────────────────────────────────────────────────────
    if cq := body.get("callback_query"):
        tg_id = cq["from"]["id"]
        chat_id = cq["message"]["chat"]["id"]
        msg_id = cq["message"]["message_id"]
        data = cq["data"]
        participant = _lookup_user(cur, tg_id)
        if not participant:
            return

        # Share callbacks
        if data.startswith("share:"):
            target = data[len("share:"):]
            if target == "done":
                stored = _get_share_set(cur, tg_id)
                has_all = "__all__" in stored
                summary = "anyone" if has_all else (", ".join(sorted(stored - {"__all__"})) or "nobody")
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, f"{_greet(cur, tg_id, participant)}sharing to: {summary}\n\nNow send your burpee video 💪", reply_markup=_MAIN_KB)
                return
            if target == "__all__":
                stored = _get_share_set(cur, tg_id)
                if "__all__" in stored:
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s", (tg_id,))
                else:
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s", (tg_id,))
                    cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, '__all__') ON CONFLICT DO NOTHING", (tg_id,))
            else:
                stored = _get_share_set(cur, tg_id)
                if "__all__" in stored:
                    # Expand __all__ to explicit rows then remove toggled one
                    others = _all_other_names(cur, tg_id)
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s", (tg_id,))
                    for p in others:
                        if p != target:
                            cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, p))
                elif target in stored:
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s", (tg_id, target))
                else:
                    cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, target))
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _share_keyboard(cur, tg_id)})
            return

        # Follow callbacks
        if data.startswith("follow:"):
            target = data[len("follow:"):]
            if target == "done":
                stored = _get_follow_set(cur, tg_id)
                has_all = "__all__" in stored
                summary = "anyone" if has_all else (", ".join(sorted(stored - {"__all__"})) or "nobody")
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, f"{_greet(cur, tg_id, participant)}following: {summary}", reply_markup=_MAIN_KB)
                return
            if target == "__all__":
                stored = _get_follow_set(cur, tg_id)
                if "__all__" in stored:
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s", (tg_id,))
                else:
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s", (tg_id,))
                    cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, '__all__') ON CONFLICT DO NOTHING", (tg_id,))
            else:
                stored = _get_follow_set(cur, tg_id)
                if "__all__" in stored:
                    # Expand __all__ to explicit rows then remove toggled one
                    others = _all_other_names(cur, tg_id)
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s", (tg_id,))
                    for p in others:
                        if p != target:
                            cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, p))
                elif target in stored:
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s", (tg_id, target))
                else:
                    cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, target))
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _follow_keyboard(cur, tg_id)})
            return

        # Radar frequency callbacks
        if data.startswith("radar:"):
            freq = data[len("radar:"):]
            if freq not in _RADAR_FREQS:
                return
            setup_mode = _get_state(cur, tg_id) == "awaiting_radar_freq_setup"
            cur.execute(
                "SELECT radar_asked, radar_send FROM telegram_bot_users WHERE telegram_user_id = %s",
                (tg_id,),
            )
            row = cur.fetchone()
            needs_send_question = row and not row["radar_asked"]
            radar_send = row["radar_send"] if row else False
            cur.execute(
                "UPDATE telegram_bot_users SET radar_freq = %s WHERE telegram_user_id = %s",
                (freq, tg_id),
            )
            if setup_mode:
                _clear_state(cur, tg_id)
            conn.commit()
            # Show send toggle in keyboard only when the user has already been asked
            show_toggle = not setup_mode and not needs_send_question
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _radar_keyboard(freq, radar_send=radar_send if show_toggle else None)})
            if setup_mode or needs_send_question:
                # Next: ask about sending
                _send(chat_id,
                      "📡 Radar works both ways — you can not only receive random burpees, but your videos can appear in others' Radar as well. Is that okay?\n\nYou can change this setting later via 📡 Radar.",
                      reply_markup=_RADAR_SEND_KB)
            else:
                label = _RADAR_LABELS[freq]
                if freq == "never":
                    _send(chat_id, "📡 Radar off.", reply_markup=_MAIN_KB)
                else:
                    _send(chat_id, f"📡 Radar set to {label.lower()} — you'll receive a random burpee from outside your sweat list.", reply_markup=_MAIN_KB)
                _log(f"📡 Radar set\n👤 {participant} → {label}")
            return

        # Radar send toggle (ON/OFF buttons in the radar keyboard)
        if data.startswith("radar_send_toggle:"):
            answer = data[len("radar_send_toggle:"):]
            if answer not in ("on", "off"):
                return
            new_send = answer == "on"
            cur.execute(
                "SELECT radar_freq FROM telegram_bot_users WHERE telegram_user_id = %s",
                (tg_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            current_freq = row["radar_freq"] or "never"
            cur.execute(
                "UPDATE telegram_bot_users SET radar_send = %s WHERE telegram_user_id = %s",
                (new_send, tg_id),
            )
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _radar_keyboard(current_freq, radar_send=new_send)})
            _log(f"📡 Radar send toggled\n👤 {participant} → {'ON' if new_send else 'OFF'}")
            return

        # Radar send permission callbacks
        if data.startswith("radar_send:"):
            answer = data[len("radar_send:"):]
            radar_send = answer == "yes"
            cur.execute(
                "UPDATE telegram_bot_users SET radar_send = %s, radar_asked = TRUE WHERE telegram_user_id = %s",
                (radar_send, tg_id),
            )
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            if radar_send:
                _send(chat_id, "✅ Got it — your videos can be shared via Radar.", reply_markup=_MAIN_KB)
            else:
                _send(chat_id, "🔒 Got it — your videos stay within your crew.", reply_markup=_MAIN_KB)
            _log(f"📡 Radar send set\n👤 {participant} → {'yes' if radar_send else 'no'}")
            return

        # Pause callbacks
        if data.startswith("pause:"):
            duration = data[len("pause:"):]
            now = datetime.now(timezone.utc)
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            if duration == "resume":
                cur.execute("UPDATE telegram_bot_users SET paused_until = NULL WHERE telegram_user_id = %s", (tg_id,))
                conn.commit()
                _send(chat_id, "▶️ Notifications resumed.", reply_markup=_MAIN_KB)
                _log(f"▶️ Pause resumed\n👤 {participant}")
            else:
                if duration == "1d":
                    until = now + timedelta(days=1)
                    label = "1 day"
                elif duration == "1w":
                    until = now + timedelta(weeks=1)
                    label = "1 week"
                elif duration == "1m":
                    until = now + timedelta(days=30)
                    label = "30 days"
                else:
                    return
                cur.execute("UPDATE telegram_bot_users SET paused_until = %s WHERE telegram_user_id = %s", (until, tg_id))
                conn.commit()
                until_str = until.strftime("%b %d")
                _send(chat_id, f"⏸️ Paused until {until_str} — no sweat forwards or radar until then.", reply_markup=_MAIN_KB)
                _log(f"⏸️ Paused\n👤 {participant} → {label}")
            return

        # Sweat notify callbacks
        if data.startswith("sweat_notify:"):
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            parts = data.split(":", 2)
            if parts[1] == "yes" and len(parts) == 3:
                target_name = parts[2]
                cur.execute("SELECT chat_id, telegram_user_id FROM telegram_bot_users WHERE participant_name = %s", (target_name,))
                target_row = cur.fetchone()
                if target_row:
                    cur.execute(
                        "SELECT 1 FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s "
                        "UNION "
                        "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s",
                        (target_row["telegram_user_id"], participant, target_row["telegram_user_id"], participant),
                    )
                    already_connected = cur.fetchone() is not None
                    if already_connected:
                        _send(target_row["chat_id"], f"🤝 {participant} added you to their sweat list!")
                    else:
                        _send(target_row["chat_id"],
                            f"🤝 {participant} added you to their sweat list!\n\nAdd {participant} to your sweat list?",
                            reply_markup={"inline_keyboard": [[
                                {"text": "Yes", "callback_data": f"sweat_add_back:yes:{participant}"},
                                {"text": "No",  "callback_data": "sweat_add_back:no"},
                            ]]},
                        )
            return

        # Sweat manage callbacks (mute / unmute / remove)
        if data.startswith("sweat_manage:"):
            parts = data.split(":", 2)
            action = parts[1]
            name = parts[2] if len(parts) > 2 else ""
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            if action == "cancel":
                _send(chat_id, "Cancelled.", reply_markup=_MAIN_KB)
                return
            now = datetime.now(timezone.utc)
            if action == "unmute":
                cur.execute(
                    "DELETE FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s",
                    (tg_id, name),
                )
                conn.commit()
                _send(chat_id, f"▶️ {name} unmuted — you'll receive their updates again.", reply_markup=_MAIN_KB)
                _log(f"🔔 Sweat unmuted\n👤 {participant} unmuted {name}")
            elif action in ("mute_1d", "mute_1w", "mute_1m"):
                delta, label = {"mute_1d": (timedelta(days=1), "1 day"), "mute_1w": (timedelta(weeks=1), "1 week"), "mute_1m": (timedelta(days=30), "1 month")}[action]
                until = now + delta
                cur.execute(
                    "INSERT INTO sweat_mute (telegram_user_id, muted_participant, muted_until) "
                    "VALUES (%s, %s, %s) ON CONFLICT (telegram_user_id, muted_participant) DO UPDATE SET muted_until = EXCLUDED.muted_until",
                    (tg_id, name, until),
                )
                conn.commit()
                _send(chat_id, f"🔕 {name} muted until {until.strftime('%b %d')} — still in your sweat list.", reply_markup=_MAIN_KB)
                _log(f"🔕 Sweat muted\n👤 {participant} muted {name} for {label}")
            elif action == "remove":
                cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s", (tg_id, name))
                cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s", (tg_id, name))
                cur.execute("DELETE FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s", (tg_id, name))
                conn.commit()
                _send(chat_id, f"Removed {name} from your sweat list.", reply_markup=_MAIN_KB)
                _log(f"🤝 Sweat removed\n👤 {participant} ✗ {name}")
            return

        # Sweat add-back callbacks
        if data.startswith("sweat_add_back:"):
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            parts = data.split(":", 2)
            if parts[1] == "yes" and len(parts) == 3:
                adder_name = parts[2]
                cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, adder_name))
                cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, adder_name))
                conn.commit()
                _send(chat_id, f"✓ Added {adder_name} to your sweat list 🤝", reply_markup=_MAIN_KB)
                cur.execute("SELECT chat_id FROM telegram_bot_users WHERE participant_name = %s", (adder_name,))
                adder_row = cur.fetchone()
                if adder_row:
                    _send(adder_row["chat_id"], f"🤝 {participant} added you to their sweat list too!")
                _log(f"🤝 Sweat add-back\n👤 {participant} → {adder_name}")
            return

        return

    is_edit = "edited_message" in body
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return

    tg_id: int = msg["from"]["id"]
    chat_id: int = msg["chat"]["id"]
    text: str = msg.get("text", "").strip()

    # ── Replies to messages are social reactions — don't process as bot input ─
    if msg.get("reply_to_message"):
        return

    # ── Edited messages: only handle reps updates, skip everything else ──────
    if is_edit:
        _reps_e, _comment_e = _parse_reps_comment(text) if text else (None, None)
        if _reps_e is not None:
            participant_e = _lookup_user(cur, tg_id)
            if participant_e:
                if _comment_e is None:
                    cur.execute(
                        "SELECT comment FROM burpee_entries WHERE participant = %s AND entry_date = %s",
                        (participant_e, str(date.today())),
                    )
                    existing = cur.fetchone()
                    if existing:
                        _comment_e = existing["comment"]
                _log_entry(cur, participant_e, _reps_e, _comment_e)
                conn.commit()
                _log(f"✏️ Reps updated (edit)\n👤 {participant_e}: {_reps_e} reps")
                _send(chat_id, f"✓ updated to {_reps_e} reps", reply_markup=_MAIN_KB)
        return

    # ── /broadcast (admin only) ──────────────────────────────────────────────
    if text.startswith("/broadcast "):
        admin_id = int(os.environ.get("ADMIN_TG_ID", "0"))
        if tg_id != admin_id:
            return
        message = text[len("/broadcast "):].strip()
        if not message:
            _send(chat_id, "Usage: /broadcast <message>")
            return
        cur.execute("SELECT chat_id, participant_name FROM telegram_bot_users")
        rows = cur.fetchall()
        for row in rows:
            _send(row["chat_id"], message)
        _send(chat_id, f"✓ Sent to {len(rows)} users")
        _log(f"📢 Broadcast\n👤 admin (tg:{tg_id})\n💬 {message[:80]}")
        return

    # ── /info ────────────────────────────────────────────────────────────────
    if text.startswith("/info") or text.startswith("/help") or text == "ℹ️ Info":
        cur.execute("SELECT token, participant_name FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        token_val = row["token"] if row and row["token"] else None
        info_name = row["participant_name"] if row and row["participant_name"] else None
        link_line = "\nYour app link:\nhttps://phase-app-yf5x.vercel.app/?token=" + token_val + "\n" if token_val else "\n(register first with /start)\n"
        _log(f"ℹ️ Info viewed\n👤 {info_name or f'unregistered (tg:{tg_id})'}")
        _send(chat_id,
            "👋 Welcome to Бурчик Challenge!\n\n"
            "3 minutes of AMRAP burpees every day — tracked, shared, and competed.\n\n"
            "How it works:\n"
            "• Record the first minute of your 3-minute burpee session as a round video bubble and send it here\n"
            "• Then type your rep count. Optional: add a comment after a comma — it shows up in the app: 25, tough day\n"
            "• Your workout is logged and forwarded to your crew\n\n"
            f"{link_line}\n"
            "Available commands:\n\n"
            "/start — register your name\n"
            "/rename — change your name\n"
            "/secret — update your app link secret\n"
            "/sweat — find who you share and follow\n"
            "/radar — receive and send random burpees from outside your sweat list\n"
            "/pause — pause all notifications for 1 day, 1 week, or 1 month\n"
            "/info — show this list",
            reply_markup=_MAIN_KB,
        )
        return

    # ── /start ───────────────────────────────────────────────────────────────
    if text.startswith("/start"):
        existing = _lookup_user(cur, tg_id)
        if existing:
            cur.execute("SELECT token FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
            row = cur.fetchone()
            token_val = row["token"] if row and row["token"] else None
            app_url = f"https://phase-app-yf5x.vercel.app/?token={token_val}" if token_val else "(no link yet)"
            _send(chat_id, f"You're already registered as {existing}.\n\nYour app link:\n{app_url}", reply_markup=_MAIN_KB)
            return
        _set_state(cur, tg_id, "awaiting_name")
        conn.commit()
        _send(chat_id,
            "👋 Welcome to Бурчик Challenge!\n\n"
            "3 minutes of AMRAP burpees every day — tracked, shared, and competed.\n\n"
            "How it works:\n"
            "• Record the first minute of your 3-minute burpee session as a round video bubble and send it here\n"
            "• Then type your rep count. Optional: add a comment after a comma — it shows up in the app: 25, tough day\n"
            "• Your workout is logged and forwarded to your crew\n\n"
            "Use /sweat to find who you share and follow.\n\n"
            "First, what would you like to be called?"
        )
        return

    participant = _lookup_user(cur, tg_id)
    state = _get_state(cur, tg_id)

    # ── /rename ──────────────────────────────────────────────────────────────
    if text.startswith("/rename") or text == "✏️ Rename":
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        _set_state(cur, tg_id, "awaiting_rename")
        conn.commit()
        _send(chat_id, f"{_greet(cur, tg_id, participant)}what would you like to change your name to?")
        return

    # ── /secret ──────────────────────────────────────────────────────────────
    if text.startswith("/secret") or text == "🔑 Secret":
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        _set_state(cur, tg_id, "awaiting_secret_update")
        conn.commit()
        _send(chat_id, "Name a fictional character you love:")
        return

    # Any command or main keyboard button cancels a pending state
    _KB_BUTTONS = {"🤝 Sweat with", "📡 Radar", "⏸️ Pause", "ℹ️ Info"}
    if (text.startswith("/") or text in _KB_BUTTONS) and state:
        _clear_state(cur, tg_id)
        conn.commit()
        state = None

    # ── Awaiting name input (registration or rename) ─────────────────────────
    if state in ("awaiting_name", "awaiting_rename") and text:
        name = text.strip()
        if len(name) > 32 or not name.replace(" ", "").isalpha():
            _send(chat_id, "Please use letters only, up to 32 characters.")
            return
        cur.execute(
            "SELECT 1 FROM telegram_bot_users WHERE LOWER(participant_name) = LOWER(%s) AND telegram_user_id != %s",
            (name, tg_id),
        )
        if cur.fetchone():
            _send(chat_id, f'"{name}" is already taken. Please choose a different name.')
            return
        old_name = participant
        if state == "awaiting_rename":
            # Keep existing secret, just update name in token
            cur.execute("SELECT secret FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
            row = cur.fetchone()
            secret = row["secret"] if row and row["secret"] else None
            token = _build_token(name, secret)
            cur.execute(
                "INSERT INTO telegram_bot_users (telegram_user_id, participant_name, chat_id, token) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (telegram_user_id) "
                "DO UPDATE SET participant_name = EXCLUDED.participant_name, chat_id = EXCLUDED.chat_id, token = EXCLUDED.token",
                (tg_id, name, chat_id, token),
            )
            cur.execute(
                "INSERT INTO burpee_participants (name) VALUES (%s) ON CONFLICT DO NOTHING",
                (name,),
            )
            if old_name and old_name != name:
                cur.execute("UPDATE burpee_entries SET participant = %s WHERE participant = %s", (name, old_name))
                cur.execute("UPDATE telegram_bot_notify SET notify_participant = %s WHERE notify_participant = %s", (name, old_name))
                cur.execute("UPDATE telegram_bot_receive SET receive_participant = %s WHERE receive_participant = %s", (name, old_name))
                cur.execute("DELETE FROM burpee_participants WHERE name = %s", (old_name,))
            _clear_state(cur, tg_id)
            conn.commit()
            app_url = f"https://phase-app-yf5x.vercel.app/?token={token}"
            _log(f"✏️ Renamed\n👤 {old_name} → {name}\n🔑 {token}")
            _send(chat_id, f"Done! Your name is now {name}.\n\nUpdated app link:\n{app_url}", reply_markup=_MAIN_KB)
        else:
            # New registration — store name in state, ask for secret next
            _set_state(cur, tg_id, f"awaiting_secret:{name}")
            conn.commit()
            _send(chat_id, "Name a fictional character you love:")
        return

    # ── Awaiting secret (new registration) ───────────────────────────────────
    if state and state.startswith("awaiting_secret:") and text:
        name = state[len("awaiting_secret:"):]
        secret = text.strip()
        if len(secret) > 64 or not secret.replace(" ", "").replace("'", "").replace("-", "").isalpha():
            _send(chat_id, "Letters only please (up to 64 characters).")
            return
        token = _build_token(name, secret)
        cur.execute(
            "INSERT INTO telegram_bot_users (telegram_user_id, participant_name, chat_id, token, secret) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (telegram_user_id) "
            "DO UPDATE SET participant_name = EXCLUDED.participant_name, chat_id = EXCLUDED.chat_id, "
            "token = EXCLUDED.token, secret = EXCLUDED.secret",
            (tg_id, name, chat_id, token, secret),
        )
        cur.execute("INSERT INTO burpee_participants (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
        _clear_state(cur, tg_id)
        conn.commit()
        app_url = f"https://phase-app-yf5x.vercel.app/?token={token}"
        _log(f"📋 New registration\n👤 {name} (tg:{tg_id})\n🔑 {token}")
        _send(chat_id,
            f"Welcome, {name}! 👋 Your app link:\n{app_url}\n\n"
            "Next: add your crew via 🤝 Sweat with.\n"
            "They'll get every video you log — and you'll get theirs.",
            reply_markup=_MAIN_KB)
        # Kick off radar setup
        _set_state(cur, tg_id, "awaiting_radar_freq_setup")
        conn.commit()
        _send(chat_id,
            "📡 Radar works differently — it sends you one random burpee from someone outside your crew. How often?",
            reply_markup=_radar_keyboard("never"),
        )
        return

    # ── Awaiting secret update (existing user via /secret) ───────────────────
    if state == "awaiting_secret_update" and text:
        secret = text.strip()
        if len(secret) > 64 or not secret.replace(" ", "").replace("'", "").replace("-", "").isalpha():
            _send(chat_id, "Letters only please (up to 64 characters).")
            return
        token = _build_token(participant, secret)
        cur.execute(
            "UPDATE telegram_bot_users SET token = %s, secret = %s WHERE telegram_user_id = %s",
            (token, secret, tg_id),
        )
        _clear_state(cur, tg_id)
        conn.commit()
        app_url = f"https://phase-app-yf5x.vercel.app/?token={token}"
        _log(f"🔑 Secret updated\n👤 {participant}\n🔗 {token}")
        _send(chat_id, f"Done! Your new app link:\n{app_url}", reply_markup=_MAIN_KB)
        return

    # ── /radar ───────────────────────────────────────────────────────────────
    if text.startswith("/radar") or text == "📡 Radar":
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        cur.execute(
            "SELECT radar_freq, radar_send, radar_asked FROM telegram_bot_users WHERE telegram_user_id = %s",
            (tg_id,),
        )
        row = cur.fetchone()
        current = row["radar_freq"] if row and row["radar_freq"] else "daily"
        radar_send = row["radar_send"] if row else False
        radar_asked = row["radar_asked"] if row else False
        # Show send toggle only for users who have already answered the send question
        kb = _radar_keyboard(current, radar_send=radar_send if radar_asked else None)
        _send(chat_id,
            f"📡 Radar — receive random burpees & share yours with the world outside your crew.\n\n"
            f"Receive: {_RADAR_LABELS.get(current, 'Off')}\n\nHow often?",
            reply_markup=kb,
        )
        return

    # ── /pause ───────────────────────────────────────────────────────────────
    if text.startswith("/pause") or text == "⏸️ Pause":
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        _log(f"⏸️ Pause menu opened\n👤 {participant}")
        cur.execute("SELECT paused_until FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        now = datetime.now(timezone.utc)
        paused_until = row["paused_until"] if row else None
        is_paused = bool(paused_until and paused_until > now)
        if is_paused:
            until_str = paused_until.strftime("%b %d, %H:%M")
            _send(chat_id,
                f"⏸️ Paused until {until_str} UTC.\n\nExtend or resume:",
                reply_markup=_pause_keyboard(True),
            )
        else:
            _send(chat_id,
                "⏸️ Pause notifications — no sweat forwards or radar while paused.\n\nPause for:",
                reply_markup=_pause_keyboard(False),
            )
        return

    # ── /sweat ───────────────────────────────────────────────────────────────
    if text.startswith("/sweat") or text == "🤝 Sweat with":
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        cur.execute(
            "SELECT notify_participant AS name FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant != '__all__' "
            "UNION "
            "SELECT receive_participant AS name FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant != '__all__'",
            (tg_id, tg_id),
        )
        partners = sorted(r["name"] for r in cur.fetchall())
        if partners:
            cur.execute(
                "SELECT muted_participant FROM sweat_mute WHERE telegram_user_id = %s AND muted_until > NOW()",
                (tg_id,),
            )
            muted_set = {r["muted_participant"] for r in cur.fetchall()}
            partner_list = ", ".join(f"{p} 🔕" if p in muted_set else p for p in partners)
        else:
            partner_list = "nobody yet"
        _set_state(cur, tg_id, "awaiting_sweat_name")
        conn.commit()
        _send(chat_id,
            f"🤝 Your sweat crew gets every video you log — and you get theirs.\n"
            f"Radar is for strangers. Sweat is for your people.\n\n"
            f"Sweating with: {partner_list}\n\n"
            "Type a name to add, mute, or remove:"
        )
        return

    # ── Awaiting sweat partner name ───────────────────────────────────────────
    if state == "awaiting_sweat_name" and text and not text.isdigit():
        name = text.strip()
        cur.execute(
            "SELECT participant_name FROM telegram_bot_users WHERE LOWER(participant_name) = LOWER(%s) AND telegram_user_id != %s",
            (name, tg_id),
        )
        row = cur.fetchone()
        if not row:
            _log(f"🔍 Sweat name not found\n👤 {participant} searched: {name}")
            _send(chat_id, f'No user named "{name}" found. Try again or send /sweat to see current list.')
            return
        matched_name = row["participant_name"]
        cur.execute(
            "SELECT 1 FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s "
            "UNION "
            "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s",
            (tg_id, matched_name, tg_id, matched_name),
        )
        already = cur.fetchone()
        if already:
            cur.execute(
                "SELECT muted_until FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s AND muted_until > NOW()",
                (tg_id, matched_name),
            )
            mute_row = cur.fetchone()
            muted_until = mute_row["muted_until"] if mute_row else None
            _clear_state(cur, tg_id)
            conn.commit()
            status = f" (muted until {muted_until.strftime('%b %d')})" if muted_until else ""
            _send(chat_id,
                f"{matched_name} is in your sweat list{status}. What would you like to do?",
                reply_markup=_sweat_manage_keyboard(matched_name, muted_until),
            )
            return
        else:
            cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, matched_name))
            cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, matched_name))
            _log(f"🤝 Sweat added\n👤 {participant} → {matched_name}")
            _clear_state(cur, tg_id)
            conn.commit()
            _send(chat_id,
                f"Added {matched_name} to your sweat list 🤝\n\nNotify {matched_name}?",
                reply_markup={"inline_keyboard": [
                    [{"text": "Yes", "callback_data": f"sweat_notify:yes:{matched_name}"},
                     {"text": "No", "callback_data": "sweat_notify:no"}]
                ]},
            )
            return

    # ── Radar setup nudge (one-time for existing users) ─────────────────────
    _reps, _comment = _parse_reps_comment(text) if text else (None, None)
    if participant and not state and text and _reps is None:
        cur.execute("SELECT radar_asked FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        if row and not row["radar_asked"]:
            _set_state(cur, tg_id, "awaiting_radar_freq_setup")
            conn.commit()
            _send(chat_id,
                "📡 Before we continue — Radar can send you a random burpee from outside your crew. How often?",
                reply_markup=_radar_keyboard("never"),
            )
            return

    # ── Plain number (+ optional comment) → reps for pending video or bare log ─
    if _reps is not None and participant:
        reps, comment = _reps, _comment

        cur.execute(
            "SELECT message_id FROM telegram_bot_pending WHERE telegram_user_id = %s",
            (tg_id,),
        )
        pending = cur.fetchone()
        if pending and pending["message_id"] is not None:
            # Video was stored first, number just arrived
            _log_entry(cur, participant, reps, comment)
            cur.execute("DELETE FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
            _do_forward(cur, conn, tg_id, participant, chat_id, pending["message_id"], reps, comment)
        else:
            # No pending video — log now; store reps+comment so late video can bind within 1h
            _log_entry(cur, participant, reps, comment)
            cur.execute(
                "INSERT INTO telegram_bot_pending (telegram_user_id, chat_id, message_id, reps, comment) "
                "VALUES (%s, %s, NULL, %s, %s) ON CONFLICT (telegram_user_id) "
                "DO UPDATE SET message_id = NULL, reps = EXCLUDED.reps, comment = EXCLUDED.comment, "
                "    chat_id = EXCLUDED.chat_id, created_at = NOW()",
                (tg_id, chat_id, reps, comment),
            )
            conn.commit()
            _log(f"💪 Reps logged (no video)\n👤 {participant}: {reps} reps")
            _send(chat_id, f"✓ {reps} reps logged", reply_markup=_MAIN_KB)
        return

    has_video = "video" in msg
    has_video_note = "video_note" in msg
    has_photo = "photo" in msg

    if not (has_video or has_video_note or has_photo):
        if text:
            name_label = participant or f"unregistered (tg:{tg_id})"
            _log(f"❓ Unhandled message\n👤 {name_label}\n💬 {text[:200]}")
            _send(chat_id, "Tap ℹ️ Info to see what I can do.", reply_markup=_MAIN_KB)
        return

    if not participant:
        _send(chat_id, "Please register first — send /start")
        return

    # ── Video or photo with optional caption ─────────────────────────────────
    if has_video or has_photo:
        caption = msg.get("caption", "").strip()
        cap_reps, cap_comment = _parse_reps_comment(caption) if caption else (None, None)
        if cap_reps is not None:
            _log_entry(cur, participant, cap_reps, cap_comment)
            _do_forward(cur, conn, tg_id, participant, chat_id, msg["message_id"], cap_reps, cap_comment)
        else:
            _store_or_bind_video(cur, conn, tg_id, participant, chat_id, msg["message_id"])
        return

    # ── Round video bubble → ask for reps ────────────────────────────────────
    if has_video_note:
        _store_or_bind_video(cur, conn, tg_id, participant, chat_id, msg["message_id"])
