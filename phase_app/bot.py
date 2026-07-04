from __future__ import annotations

import json
import os
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
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
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
    _tg("forwardMessage", {
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


def _get_state(cur, tg_id: int) -> str | None:
    cur.execute("SELECT state FROM telegram_bot_state WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    return row["state"] if row else None


def _set_state(cur, tg_id: int, state: str) -> None:
    cur.execute(
        "INSERT INTO telegram_bot_state (telegram_user_id, state) VALUES (%s, %s) "
        "ON CONFLICT (telegram_user_id) DO UPDATE SET state = EXCLUDED.state",
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
        [{"text": "✏️ Rename"}, {"text": "🔑 Secret"}],
        [{"text": "ℹ️ Info"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

_RADAR_FREQS = ["daily", "weekly", "monthly", "once", "never"]
_RADAR_LABELS = {"daily": "Daily", "weekly": "Weekly", "monthly": "Monthly", "once": "Just once", "never": "Off"}

def _radar_keyboard(current: str) -> dict:
    rows = []
    for freq in _RADAR_FREQS:
        label = ("✓ " if freq == current else "") + _RADAR_LABELS[freq]
        rows.append([{"text": label, "callback_data": f"radar:{freq}"}])
    return {"inline_keyboard": rows}

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

def _log_entry(cur, participant: str, reps: int) -> None:
    cur.execute(
        "INSERT INTO burpee_entries (participant, entry_date, reps) VALUES (%s, %s, %s) "
        "ON CONFLICT (participant, entry_date) DO UPDATE SET reps = EXCLUDED.reps",
        (participant, str(date.today()), reps),
    )


def _do_forward(cur, conn, tg_id: int, participant: str, from_chat_id: int, message_id: int | None, reps: int) -> None:
    targets = _get_share_chats(cur, tg_id)
    conn.commit()
    for to_chat_id, name in targets:
        if message_id:
            _forward(from_chat_id, message_id, to_chat_id)
        _send(to_chat_id, f"{participant}: {reps} reps")
    if targets:
        forwarded_to = ", ".join(n for _, n in targets)
        _send(from_chat_id, f"✓ {reps} reps → forwarded to {forwarded_to}", reply_markup=_MAIN_KB)
        _log(f"💪 Video logged\n👤 {participant}: {reps} reps\n📤 → {forwarded_to}")
    else:
        _send(from_chat_id, f"✓ {reps} reps logged", reply_markup=_MAIN_KB)
        _log(f"💪 Video logged\n👤 {participant}: {reps} reps\n📤 → nobody")

    # ── Radar: forward to eligible users outside sender's sweat list ──────────
    sweat_names = {n for _, n in targets} | {participant}
    cur.execute(
        "SELECT telegram_user_id, chat_id, participant_name, radar_freq, radar_last_received "
        "FROM telegram_bot_users "
        "WHERE radar_freq != 'never' AND telegram_user_id != %s",
        (tg_id,),
    )
    _PERIOD = {"daily": "every day", "weekly": "every week", "monthly": "every month"}
    for row in cur.fetchall():
        if row["participant_name"] in sweat_names:
            continue
        if not _radar_due(row["radar_freq"], row["radar_last_received"]):
            continue
        freq = row["radar_freq"]
        is_first = row["radar_last_received"] is None
        if is_first:
            if freq == "once":
                explanation = (
                    f"📡 {participant}: {reps} reps\n"
                    "You're getting this because your radar is on — a burpee from outside your crew. "
                    "According to your radar settings you'll get 1 burpee bubble, just once. "
                    "Use /radar to adjust frequency."
                )
            else:
                period = _PERIOD.get(freq, freq)
                explanation = (
                    f"📡 {participant}: {reps} reps\n"
                    "You're getting this because your radar is on — a burpee from outside your crew. "
                    f"According to your radar settings you will get 1 random burpee bubble {period}. "
                    "Use /radar to adjust frequency."
                )
        else:
            explanation = (
                f"📡 {participant}: {reps} reps\n"
                "Your Radar detected some burpee activity from someone outside your crew."
            )
        _send(row["chat_id"], explanation)
        if message_id:
            _forward(from_chat_id, message_id, row["chat_id"])
        _log(f"📡 Radar forward\n💪 {participant}: {reps} reps → {row['participant_name']} ({freq})")
        new_freq = "never" if freq == "once" else freq
        cur.execute(
            "UPDATE telegram_bot_users SET radar_last_received = NOW(), radar_freq = %s WHERE telegram_user_id = %s",
            (new_freq, row["telegram_user_id"]),
        )


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

        # Radar callbacks
        if data.startswith("radar:"):
            freq = data[len("radar:"):]
            if freq not in _RADAR_FREQS:
                return
            cur.execute(
                "UPDATE telegram_bot_users SET radar_freq = %s WHERE telegram_user_id = %s",
                (freq, tg_id),
            )
            conn.commit()
            label = _RADAR_LABELS[freq]
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _radar_keyboard(freq)})
            if freq == "never":
                _send(chat_id, "📡 Radar off.", reply_markup=_MAIN_KB)
            else:
                _send(chat_id, f"📡 Radar set to {label.lower()} — you'll receive a random burpee from outside your sweat list.", reply_markup=_MAIN_KB)
            _log(f"📡 Radar set\n👤 {participant} → {label}")
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

    msg = body.get("message")
    if not msg:
        return

    tg_id: int = msg["from"]["id"]
    chat_id: int = msg["chat"]["id"]
    text: str = msg.get("text", "").strip()

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
            "• Do your burpees and send a round video bubble to the burchykbot\n"
            "• Type the number of reps\n"
            "• Your workout is logged and forwarded to your crew\n\n"
            "Use /sweat to choose who you share and follow.\n"
            f"{link_line}\n"
            "Available commands:\n\n"
            "/start — register your name\n"
            "/rename — change your name\n"
            "/secret — update your app link secret\n"
            "/sweat — choose who you share and follow\n"
            "/radar — receive random burpees from outside your sweat list\n"
            "/info — show this list\n\n"
            "To log a workout:\n"
            "• Send a round video bubble to the burchykbot and type the number of reps",
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
            "• Do your burpees and send a round video bubble to the burchykbot\n"
            "• Type the number of reps\n"
            "• Your workout is logged and forwarded to your crew\n\n"
            "Use /sweat to choose who you share and follow.\n\n"
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
    _KB_BUTTONS = {"🤝 Sweat with", "📡 Radar", "✏️ Rename", "🔑 Secret", "ℹ️ Info"}
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
        _send(chat_id, f"Welcome, {name}! 👋\n\nYour personal app link:\n{app_url}\n\nUse /sweat to choose who you share and follow.\n\nThen send your first burpee video 💪", reply_markup=_MAIN_KB)
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
        cur.execute("SELECT radar_freq FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        current = row["radar_freq"] if row and row["radar_freq"] else "daily"
        _send(chat_id,
            f"📡 Radar — receive a random burpee video from outside your sweat list.\n\n"
            f"Current: {_RADAR_LABELS.get(current, 'Off')}\n\nHow often?",
            reply_markup=_radar_keyboard(current),
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
        partner_list = ", ".join(partners) if partners else "nobody yet"
        _set_state(cur, tg_id, "awaiting_sweat_name")
        conn.commit()
        _send(chat_id,
            f"{_greet(cur, tg_id, participant)}sweating with: {partner_list}\n\n"
            "Type the name of the person you want to sweat with (or remove):"
        )
        return

    # ── Awaiting sweat partner name ───────────────────────────────────────────
    if state == "awaiting_sweat_name" and text:
        name = text.strip()
        cur.execute(
            "SELECT participant_name FROM telegram_bot_users WHERE LOWER(participant_name) = LOWER(%s) AND telegram_user_id != %s",
            (name, tg_id),
        )
        row = cur.fetchone()
        if not row:
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
            cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s", (tg_id, matched_name))
            cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s", (tg_id, matched_name))
            msg = f"Removed {matched_name} from your sweat list."
            _log(f"🤝 Sweat removed\n👤 {participant} ✗ {matched_name}")
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
        _clear_state(cur, tg_id)
        conn.commit()
        _send(chat_id, msg, reply_markup=_MAIN_KB)
        return

    # ── Plain number → reps for pending video_note, or log without media ─────
    if text.isdigit() and participant:
        reps = int(text)
        cur.execute("SELECT message_id FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
        pending = cur.fetchone()
        if pending:
            _log_entry(cur, participant, reps)
            cur.execute("DELETE FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
            _do_forward(cur, conn, tg_id, participant, chat_id, pending["message_id"], reps)
        else:
            _log_entry(cur, participant, reps)
            conn.commit()
            _log(f"💪 Reps logged (no video)\n👤 {participant}: {reps} reps")
            _send(chat_id, f"✓ {reps} reps logged", reply_markup=_MAIN_KB)
        return

    has_video = "video" in msg
    has_video_note = "video_note" in msg
    has_photo = "photo" in msg

    if not (has_video or has_video_note or has_photo):
        return

    if not participant:
        _send(chat_id, "Please register first — send /start")
        return

    # ── Video or photo with caption ──────────────────────────────────────────
    if has_video or has_photo:
        caption = msg.get("caption", "").strip()
        if not caption.isdigit():
            _send(chat_id, f"{_greet(cur, tg_id, participant)}add the number of reps as the caption (e.g. 43)")
            return
        reps = int(caption)
        _log_entry(cur, participant, reps)
        _do_forward(cur, conn, tg_id, participant, chat_id, msg["message_id"], reps)
        return

    # ── Round video bubble → ask for reps ────────────────────────────────────
    if has_video_note:
        cur.execute(
            "INSERT INTO telegram_bot_pending (telegram_user_id, chat_id, message_id) "
            "VALUES (%s, %s, %s) ON CONFLICT (telegram_user_id) "
            "DO UPDATE SET message_id = EXCLUDED.message_id, chat_id = EXCLUDED.chat_id, created_at = NOW()",
            (tg_id, chat_id, msg["message_id"]),
        )
        conn.commit()
        _send(chat_id, f"{_greet(cur, tg_id, participant)}how many reps?")
