from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date

_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_API = f"https://api.telegram.org/bot{_TOKEN}"


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


def _all_other_names(cur, tg_id: int) -> list[str]:
    cur.execute(
        "SELECT participant_name FROM telegram_bot_users WHERE telegram_user_id != %s ORDER BY participant_name",
        (tg_id,),
    )
    return [r["participant_name"] for r in cur.fetchall()]


# ── Notify (send to) ─────────────────────────────────────────────────────────

def _get_notify_set(cur, tg_id: int) -> set[str]:
    cur.execute(
        "SELECT notify_participant FROM telegram_bot_notify WHERE telegram_user_id = %s",
        (tg_id,),
    )
    return {r["notify_participant"] for r in cur.fetchall()}


def _get_notify_chats(cur, tg_id: int) -> list[tuple[int, str]]:
    """Returns (chat_id, name) for users this sender wants to notify AND who accept from sender's name."""
    cur.execute(
        "SELECT u.chat_id, u.participant_name "
        "FROM telegram_bot_notify n "
        "JOIN telegram_bot_users u ON u.participant_name = n.notify_participant "
        "WHERE n.telegram_user_id = %s",
        (tg_id,),
    )
    candidates = [(r["chat_id"], r["participant_name"]) for r in cur.fetchall()]
    # Filter by receiver's receive list (if they've set one)
    cur.execute(
        "SELECT telegram_user_id FROM telegram_bot_users WHERE participant_name = ANY(%s)",
        ([name for _, name in candidates],),
    )
    receiver_ids = {r["telegram_user_id"] for r in cur.fetchall()}
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
                "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s",
                (rid, sender_name),
            )
            if not cur.fetchone():
                continue
        result.append((chat_id, name))
    return result


def _notify_keyboard(cur, tg_id: int) -> dict:
    selected = _get_notify_set(cur, tg_id)
    others = _all_other_names(cur, tg_id)
    all_selected = set(others) == selected and len(others) > 0
    rows = []
    anyone_label = "✓ Anyone" if all_selected else "Anyone"
    rows.append([{"text": anyone_label, "callback_data": "notify:__all__"}])
    for p in others:
        label = f"✓ {p}" if p in selected else p
        rows.append([{"text": label, "callback_data": f"notify:{p}"}])
    rows.append([{"text": "Done", "callback_data": "notify:done"}])
    return {"inline_keyboard": rows}


# ── Receive (accept from) ────────────────────────────────────────────────────

def _get_receive_set(cur, tg_id: int) -> set[str]:
    cur.execute(
        "SELECT receive_participant FROM telegram_bot_receive WHERE telegram_user_id = %s",
        (tg_id,),
    )
    return {r["receive_participant"] for r in cur.fetchall()}


def _receive_keyboard(cur, tg_id: int) -> dict:
    selected = _get_receive_set(cur, tg_id)
    others = _all_other_names(cur, tg_id)
    all_selected = set(others) == selected and len(others) > 0
    rows = []
    anyone_label = "✓ Anyone" if all_selected else "Anyone"
    rows.append([{"text": anyone_label, "callback_data": "receive:__all__"}])
    for p in others:
        label = f"✓ {p}" if p in selected else p
        rows.append([{"text": label, "callback_data": f"receive:{p}"}])
    rows.append([{"text": "Done", "callback_data": "receive:done"}])
    return {"inline_keyboard": rows}


# ── Entry logging + forwarding ───────────────────────────────────────────────

def _log_entry(cur, participant: str, reps: int) -> None:
    cur.execute(
        "INSERT INTO burpee_entries (participant, entry_date, reps) VALUES (%s, %s, %s) "
        "ON CONFLICT (participant, entry_date) DO UPDATE SET reps = EXCLUDED.reps",
        (participant, str(date.today()), reps),
    )


def _do_forward(cur, conn, tg_id: int, participant: str, from_chat_id: int, message_id: int | None, reps: int) -> None:
    targets = _get_notify_chats(cur, tg_id)
    conn.commit()
    for to_chat_id, name in targets:
        if message_id:
            _forward(from_chat_id, message_id, to_chat_id)
        _send(to_chat_id, f"{participant}: {reps} reps")
    if targets:
        forwarded_to = ", ".join(n for _, n in targets)
        _send(from_chat_id, f"✓ {participant}, logged {reps} reps → forwarded to {forwarded_to}")
    else:
        _send(from_chat_id, f"✓ {participant}, logged {reps} reps")


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

        # Notify callbacks
        if data.startswith("notify:"):
            target = data[len("notify:"):]
            if target == "done":
                selected = _get_notify_set(cur, tg_id)
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, f"{participant}, sending to: {', '.join(sorted(selected)) or 'nobody'}\n\nNow send your burpee video 💪")
                return
            others = _all_other_names(cur, tg_id)
            if target == "__all__":
                selected = _get_notify_set(cur, tg_id)
                if set(others) == selected:
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s", (tg_id,))
                else:
                    for p in others:
                        cur.execute(
                            "INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (tg_id, p),
                        )
            else:
                selected = _get_notify_set(cur, tg_id)
                if target in selected:
                    cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s", (tg_id, target))
                else:
                    cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, target))
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _notify_keyboard(cur, tg_id)})
            return

        # Receive callbacks
        if data.startswith("receive:"):
            target = data[len("receive:"):]
            if target == "done":
                selected = _get_receive_set(cur, tg_id)
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, f"{participant}, receiving from: {', '.join(sorted(selected)) or 'nobody'}")
                return
            others = _all_other_names(cur, tg_id)
            if target == "__all__":
                selected = _get_receive_set(cur, tg_id)
                if set(others) == selected:
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s", (tg_id,))
                else:
                    for p in others:
                        cur.execute(
                            "INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (tg_id, p),
                        )
            else:
                selected = _get_receive_set(cur, tg_id)
                if target in selected:
                    cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s", (tg_id, target))
                else:
                    cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, target))
            conn.commit()
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _receive_keyboard(cur, tg_id)})
            return

        return

    msg = body.get("message")
    if not msg:
        return

    tg_id: int = msg["from"]["id"]
    chat_id: int = msg["chat"]["id"]
    text: str = msg.get("text", "").strip()

    # ── /help ────────────────────────────────────────────────────────────────
    if text.startswith("/help"):
        _send(chat_id,
            "Available commands:\n\n"
            "/start — register your name\n"
            "/notify — choose who receives your videos\n"
            "/receive — choose whose videos you receive\n"
            "/help — show this list\n\n"
            "To log a workout:\n"
            "• Send a round video bubble → bot asks for reps\n"
            "• Send a video/photo with rep count as caption\n"
            "• Send just a number (e.g. 43) — logs without video"
        )
        return

    # ── /start ───────────────────────────────────────────────────────────────
    if text.startswith("/start"):
        _set_state(cur, tg_id, "awaiting_name")
        conn.commit()
        _send(chat_id, "What would you like to be called?")
        return

    participant = _lookup_user(cur, tg_id)
    state = _get_state(cur, tg_id)

    # ── Awaiting name input ──────────────────────────────────────────────────
    if state == "awaiting_name" and text:
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
        token = f"бурчик-{name.lower()}"
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
        _clear_state(cur, tg_id)
        conn.commit()
        app_url = f"https://phase-app-yf5x.vercel.app/?token={token}"
        _send(chat_id, f"Welcome, {name}! 👋\n\nYour personal app link:\n{app_url}\n\nUse /notify to choose who receives your videos.\nUse /receive to choose whose videos you receive.\n\nThen send your first burpee video 💪")
        return

    # ── /notify ──────────────────────────────────────────────────────────────
    if text.startswith("/notify"):
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        others = _all_other_names(cur, tg_id)
        if not others:
            _send(chat_id, f"{participant}, no other users are registered yet.")
            return
        _send(chat_id, f"{participant}, who should receive your videos? Tap to toggle, then Done.", reply_markup=_notify_keyboard(cur, tg_id))
        return

    # ── /receive ─────────────────────────────────────────────────────────────
    if text.startswith("/receive"):
        if not participant:
            _send(chat_id, "Please register first — send /start")
            return
        others = _all_other_names(cur, tg_id)
        if not others:
            _send(chat_id, f"{participant}, no other users are registered yet.")
            return
        _send(chat_id, f"{participant}, whose videos do you want to receive? Tap to toggle, then Done.", reply_markup=_receive_keyboard(cur, tg_id))
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
            _send(chat_id, f"✓ {participant}, logged {reps} reps")
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
            _send(chat_id, f"{participant}, add the number of reps as the caption (e.g. 43)")
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
        _send(chat_id, f"{participant}, how many reps?")
