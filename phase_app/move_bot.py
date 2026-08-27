"""Move — "the move of the day" Telegram bot.

    We breathe every day.
    We move every day.

Same skeleton as the burpee bot, but the unit of logging is a MOVE, not a rep
count: everyone does their own activity, so there is nothing to compare. What
counts is showing up (streaks) and ⚡ from your crew.

Deliberate differences from phase_app.bot:
  - Own token (MOVE_BOT_TOKEN) and its own _api helper that RETURNS the API
    response — we need copyMessage's message_id to thread late comments and to
    refresh the ⚡ counter.
  - One-step logging: send media, it's your move. It goes out immediately; a
    comment sent within _COMMENT_WINDOW_MINUTES is delivered as a reply under
    the forwarded copy, so it reads as one post.
  - No web-app token / no /secret.
  - Milestones are streak-based, not volume-based.
"""
from __future__ import annotations

import json
import os
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

_TOKEN = os.environ.get("MOVE_BOT_TOKEN", "")
_API = f"https://api.telegram.org/bot{_TOKEN}"
# Activity goes to the same log channel as the burpee bot (Бурчик лог).
# MOVE_LOG_CHAT_ID only exists to split them later if that's ever wanted.
_LOG_CHAT_ID = os.environ.get("MOVE_LOG_CHAT_ID", "") or os.environ.get("LOG_CHAT_ID", "")
# Every incoming update, one line each. Set MOVE_TRACE_CHAT_ID to send this
# firehose somewhere of its own — in the same chat as the ⚠️ reports it buries
# them, and those are the messages that carry moderator buttons. Empty and with
# no separate chat, tracing goes to the log chat; set it to "off" to stop.
_TRACE_CHAT_ID = os.environ.get("MOVE_TRACE_CHAT_ID", "")

_STATE_TIMEOUT_MINUTES = 10
_COMMENT_WINDOW_MINUTES = 10          # a text this soon after a move is its comment
_UNDO_WINDOW_SECONDS = 10             # how long a move can still be taken back
# Same stranger can't reappear within a week. Env-tunable: while the pool is
# small a hard 7 days runs everyone dry, so it can be dialled down and raised
# again as the pool grows, without a code change.
_RADAR_REPEAT_DAYS = int(os.environ.get("POOL_COOLDOWN_DAYS", "7"))
_RADAR_PULL_MIN_POOL = 20             # "show me someone now" unlocks at this pool size
_RADAR_FRESH_DAYS = 2                 # how far back radar looks for a move to show
_MILESTONES = (7, 14, 30, 50, 100, 200, 365)
# Moderation. Reports are unverified, so the automatic half stays reversible:
# a warning is cheap, and a suspension is a pause a moderator can lift.
_REPORTS_PER_WARNING = 2              # distinct reporters on one entry
_WARNINGS_PER_SUSPENSION = 3          # active warnings before radar sharing stops
_WARNING_TTL_DAYS = 90                # after which a warning no longer counts
_MEDIA_KEYS = ("video_note", "video", "photo", "animation")


# ── Telegram plumbing ────────────────────────────────────────────────────────

def _api_call(method: str, payload: dict) -> dict | None:
    """Call the Bot API and return the parsed `result`, or None on failure."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_API}/{method}", data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode())
            return body.get("result") if body.get("ok") else None
    except urllib.error.HTTPError as e:
        print(f"Move API error [{method}]: {e.code} {e.read().decode()}")
    except Exception as e:
        print(f"Move API error [{method}]: {e}")
    return None


def _send(chat_id: int, text: str, reply_markup: dict | None = None,
          reply_to: int | None = None) -> dict | None:
    payload: dict = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to:
        payload["reply_to_message_id"] = reply_to
        payload["allow_sending_without_reply"] = True
    return _api_call("sendMessage", payload)


def _copy(from_chat_id: int, message_id: int, to_chat_id: int,
          reply_markup: dict | None = None) -> dict | None:
    payload: dict = {"chat_id": to_chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _api_call("copyMessage", payload)


def _edit(chat_id: int, message_id: int, text: str,
          reply_markup: dict | None = None) -> dict | None:
    payload: dict = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return _api_call("editMessageText", payload)


def _redraw(chat_id: int, message_id: int, text: str, reply_markup: dict) -> None:
    """Re-render a settings message in place so it can never show stale state.

    A menu that reports "Now: sharing ✅" has to be rewritten when that stops
    being true — otherwise the user is looking at two contradictory answers and
    the older, wrong one is the more prominent.
    """
    _edit(chat_id, message_id, text, reply_markup)


def _answer(callback_id: str, text: str = "") -> None:
    _api_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


_BOT_USERNAME: str | None = None


def _bot_username() -> str:
    """Cached getMe, so invite links can be built without another env var."""
    global _BOT_USERNAME
    if _BOT_USERNAME is None:
        me = _api_call("getMe", {}) or {}
        _BOT_USERNAME = me.get("username") or os.environ.get("MOVE_BOT_USERNAME", "")
    return _BOT_USERNAME


def _log(text: str, reply_markup: dict | None = None) -> None:
    if not _LOG_CHAT_ID:
        return
    ts = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
    payload = {"chat_id": int(_LOG_CHAT_ID), "text": f"[{ts}]\n{text}"}
    if reply_markup:
        # Moderation messages carry their actions, so acting doesn't need typing.
        payload["reply_markup"] = reply_markup
    try:
        _api_call("sendMessage", payload)
    except Exception:
        pass


_TRACE_MAX = 300                      # a pasted wall of text shouldn't fill the chat


def _trace(cur, body: dict) -> None:
    """One line per incoming update: who, and what they sent or tapped.

    The other _log calls record outcomes — a move logged, a crew link made. This
    records input, including the things that produce no outcome at all: menus
    opened, names that matched nobody, buttons pressed twice. Those are invisible
    otherwise, and they're where the confusion shows.

    Only incoming updates. The bot's own replies aren't updates, so they aren't
    here; what the bot said in response is what the code says it says.
    """
    target = _TRACE_CHAT_ID or _LOG_CHAT_ID
    if not target or _TRACE_CHAT_ID.lower() == "off":
        return

    cq = body.get("callback_query")
    msg = cq.get("message") if cq else body.get("message")
    src = (cq or body.get("message") or {}).get("from") or {}
    tg_id = src.get("id")
    if not tg_id:
        return
    u = _user(cur, tg_id)
    who = (u["participant_name"] if u and u["participant_name"] else None) \
        or src.get("first_name") or "?"

    if cq:
        what = f"⌨ {cq.get('data') or '?'}"
    else:
        m = body.get("message") or {}
        media = next((k for k in _MEDIA_KEYS if k in m), None)
        if media:
            what = f"📹 {media}" + (f" + «{m['caption'][:_TRACE_MAX]}»" if m.get("caption") else "")
        elif m.get("text"):
            what = f"«{m['text'][:_TRACE_MAX]}»"
        else:
            # Stickers, locations, contacts — the bot ignores them, but a user
            # sending one and getting nothing back is exactly what's worth seeing.
            what = "· " + ", ".join(k for k in m if k not in ("message_id", "from", "chat", "date"))
    try:
        _api_call("sendMessage", {
            "chat_id": int(target),
            "text": f"👤 {who} ({tg_id})\n{what}",
            "disable_notification": True,      # a firehose must not buzz the phone
        })
    except Exception:
        pass


def _admin_ids() -> set[int]:
    """Who may act on a report. MOVE_ADMIN_IDS, or the burpee bot's ADMIN_TG_ID."""
    raw = os.environ.get("MOVE_ADMIN_IDS", "") or os.environ.get("ADMIN_TG_ID", "")
    out = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


# ── i18n ─────────────────────────────────────────────────────────────────────

_SUPPORTED_LANGS = ("en", "uk", "de")


def _norm_lang(raw: str | None) -> str:
    if not raw:
        return "en"
    code = raw.split("-")[0].lower()
    return code if code in _SUPPORTED_LANGS else "en"


def _t(key: str, lang: str = "en", **fmt) -> str:
    entry = _STRINGS.get(key, {})
    template = entry.get(lang) or entry.get("en") or key
    return template.format(**fmt) if fmt else template


def _plural_form(n: int, lang: str) -> str:
    """Which plural form a numeral takes: 'one' / 'few' / 'many'.

    Ukrainian needs three (1 блискавка, 2-4 блискавки, 5+ блискавок), with the
    usual 11-14 exception. English and German only distinguish one vs many.
    """
    if lang != "uk":
        return "one" if n == 1 else "many"
    if n % 10 == 1 and n % 100 != 11:
        return "one"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "few"
    return "many"


def _tgen(key: str, lang: str, gender: str | None, **fmt) -> str:
    """Like _t, but prefers a gendered variant where one exists.

    Ukrainian past-tense verbs agree with the subject ("рухався" / "рухалася"),
    so describing a woman with the masculine form is simply wrong. Falls back to
    the base key, which is phrased to work without knowing the gender.
    """
    if gender in ("m", "f"):
        gkey = f"{key}_{gender}"
        if gkey in _STRINGS and _STRINGS[gkey].get(lang):
            return _t(gkey, lang, **fmt)
    return _t(key, lang, **fmt)


_STRINGS: dict[str, dict[str, str]] = {
    # ── keyboard ──
    "btn_move":  {"en": "🤝 Move with", "uk": "🤝 Рух разом", "de": "🤝 Bewegen mit"},
    "btn_radar": {"en": "📡 Radar", "uk": "📡 Радар", "de": "📡 Radar"},
    "btn_pause": {"en": "⏸️ Pause", "uk": "⏸️ Пауза", "de": "⏸️ Pause"},
    "btn_info":  {"en": "ℹ️ Info", "uk": "ℹ️ Інфо", "de": "ℹ️ Info"},
    "kb_done":   {"en": "Done", "uk": "Готово", "de": "Fertig"},
    "kb_cancel": {"en": "Cancel", "uk": "Скасувати", "de": "Abbrechen"},
    "kb_yes":    {"en": "Yes", "uk": "Так", "de": "Ja"},
    "kb_no":     {"en": "No", "uk": "Ні", "de": "Nein"},
    # ── onboarding ──
    "tagline": {
        "en": "We breathe every day.\nWe move every day.",
        "uk": "Ми дихаємо щодня.\nМи рухаємось щодня.",
        "de": "Wir atmen jeden Tag.\nWir bewegen uns jeden Tag.",
    },
    "start_body": {
        "en": "👋 Welcome to Move!\n\n{tagline}\n\n"
              "One move a day — whatever it is. Walk, swim, lift, stretch, dance.\n\n"
              "How it works:\n"
              "• Record a round video bubble (or a photo) and send it here\n"
              "• Add a comment right after if you want to say something\n"
              "• Your crew sees it and can send you a ⚡\n\n"
              "First, what would you like to be called?",
        "uk": "👋 Ласкаво просимо до Move!\n"
              "\n"
              "{tagline}\n"
              "\n"
              "Один рух на день — будь-який. Прогулянка, плавання, штанга, розтяжка, танці.\n"
              "\n"
              "Як це працює:\n"
              "• Запиши кругле відео (або фото) і надішли сюди\n"
              "• Одразу після цього можеш додати коментар\n"
              "• Твоє коло бачить це і може надіслати тобі ⚡\n"
              "\n"
              "Спершу: як тебе називати?",
        "de": "👋 Willkommen bei Move!\n\n{tagline}\n\n"
              "Eine Bewegung pro Tag — was auch immer. Gehen, Schwimmen, Heben, Dehnen, Tanzen.\n\n"
              "So funktioniert's:\n"
              "• Nimm ein rundes Video (oder ein Foto) auf und schick es hierher\n"
              "• Direkt danach kannst du einen Kommentar hinzufügen\n"
              "• Deine Crew sieht es und kann dir ein ⚡ schicken\n\n"
              "Zuerst: Wie möchtest du genannt werden?",
    },
    "info_body": {
        "en": "🏃 Move\n"
              "\n"
              "One move a day — any kind. Squats, swimming, barbell, stretching, dancing. Nothing is measured or compared. What counts is showing up.\n"
              "\n"
              "📹 Send a video bubble or a photo to this bot — that's your move of the day. You can add a text comment to it. The bot passes your move straight to your crew — and to strangers too, if you turn radar on.\n"
              "\n"
              "💬 A question or an idea? Send /feedback — it goes straight to the people who make Move.\n"
              "\n"
              "{tagline}\n"
              "Let's do it together.",
        "uk": "🏃 Move\n"
              "\n"
              "Один рух на день — будь-який. Присідання, плавання, штанга, розтяжка, танці. Нічого не вимірюється й не порівнюється. Головне — проявитися.\n"
              "\n"
              "📹 Надішли кругле відео або фото в цей чат-бот — це твій рух дня. Можеш доповнити рух текстовим коментарем. Бот одразу розішле рух твоєму колу — а якщо увімкнеш радар, то й незнайомцям.\n"
              "\n"
              "💬 Є питання чи ідея? Надішли /feedback — воно потрапить прямо до тих, хто робить Move.\n"
              "\n"
              "{tagline}\n"
              "Давай робити це разом.",
        "de": "🏃 Move\n"
              "\n"
              "Eine Bewegung pro Tag — welche auch immer. Kniebeugen, Schwimmen, Langhantel, Dehnen, Tanzen. Nichts wird gemessen oder verglichen. Es zählt, dass du auftauchst.\n"
              "\n"
              "📹 Schick ein rundes Video oder ein Foto an diesen Bot — das ist deine Bewegung des Tages. Du kannst einen Textkommentar ergänzen. Der Bot schickt deine Bewegung direkt an deine Crew — und an Fremde, wenn du Radar einschaltest.\n"
              "\n"
              "💬 Eine Frage oder eine Idee? Schick /feedback — sie geht direkt an die Leute hinter Move.\n"
              "\n"
              "{tagline}\n"
              "Machen wir das zusammen.",
    },
    "ask_name": {"en": "What would you like to be called?", "uk": "Як тебе називати?", "de": "Wie möchtest du genannt werden?"},
    "welcome": {
        "en": "Welcome, {name}! 👋\n\nNext: add your crew with 🤝 Move with.\nThey'll see every move you log — and you'll see theirs.",
        "uk": "Вітаємо, {name}! 👋\n"
              "\n"
              "Далі: додай своє коло через 🤝 Рух разом.\n"
              "Вони бачитимуть кожен твій рух — а ти їхні.",
        "de": "Willkommen, {name}! 👋\n\nAls Nächstes: Füge deine Crew über 🤝 Bewegen mit hinzu.\nSie sehen jede deiner Bewegungen — und du ihre.",
    },
    "already_registered": {"en": "You're already registered as {name}.", "uk": "Ти вже в Move як {name}.", "de": "Du bist bereits als {name} registriert."},
    "renamed": {"en": "Done! You're now {name}.", "uk": "Готово! Тепер ти {name}.", "de": "Fertig! Du bist jetzt {name}."},
    "ask_rename": {"en": "What should your new name be?", "uk": "Яке нове ім'я?", "de": "Wie soll dein neuer Name sein?"},
    "register_first": {"en": "Please register first — send /start", "uk": "Спершу зареєструйся — надішли /start", "de": "Bitte zuerst registrieren — sende /start"},
    "letters_only": {"en": "Letters only please, up to 32 characters.", "uk": "Лише літери, до 32 символів.", "de": "Bitte nur Buchstaben, bis zu 32 Zeichen."},
    "name_taken": {"en": "\"{name}\" is taken. Pick another.", "uk": "Ім'я «{name}» зайняте. Обери інше.", "de": "„{name}“ ist vergeben. Wähle einen anderen."},
    "unknown_msg": {"en": "Send a video bubble or a photo to log your move. Tap ℹ️ Info for more.", "uk": "Надішли кругле відео або фото, щоб записати свій рух. Натисни ℹ️ Інфо.", "de": "Schick ein rundes Video oder ein Foto, um deine Bewegung zu erfassen. Tippe ℹ️ Info."},
    # Same fallback, for someone who has already moved — telling them to record a
    # move they've just recorded reads as if the bot forgot.
    "unknown_msg_done": {
        "en": "Already moved today ✓ — tap ℹ️ Info to see what else I can do.",
        "uk": "Сьогодні рух уже є ✓ — натисни ℹ️ Інфо, щоб побачити, що я ще вмію.",
        "de": "Heute schon bewegt ✓ — tippe ℹ️ Info, um zu sehen, was ich sonst kann.",
    },
    # ── logging ──
    "logged": {"en": "✓ Move logged{streak}", "uk": "✓ Рух записано{streak}", "de": "✓ Bewegung erfasst{streak}"},
    "logged_shared": {"en": "✓ Move logged{streak} → shared with {names}", "uk": "✓ Рух записано{streak} → надіслано: {names}", "de": "✓ Bewegung erfasst{streak} → geteilt mit {names}"},
    "streak_suffix": {"en": " · 🔥 {days}-day streak", "uk": " · 🔥 серія {days} дн.", "de": " · 🔥 {days}-Tage-Serie"},
    "already_logged": {
        "en": "You've already moved today ✓ — only one move a day can be recorded.",
        "uk": "Сьогодні рух уже записано ✓ — один рух на день.",
        "de": "Du hast dich heute schon bewegt ✓ — pro Tag lässt sich nur eine Bewegung erfassen.",
    },
    "comment_added": {
        "en": "💬 Added under your move — your crew can see it.",
        "uk": "💬 Додано під твій рух — твоє коло це бачить.",
        "de": "💬 Unter deiner Bewegung ergänzt — deine Crew sieht es.",
    },
    "comment_saved_late": {
        "en": "💬 Saved with today's move. Your crew isn't notified again this late.",
        "uk": "💬 Збережено до сьогоднішнього руху. Твоє коло вже не сповіщаємо.",
        "de": "💬 Bei der heutigen Bewegung gespeichert. Deine Crew wird jetzt nicht mehr benachrichtigt.",
    },
    "comment_saved_alone": {
        "en": "💬 Saved with today's move. Nobody sees it yet — add someone with 🤝 Move with.",
        "uk": "💬 Збережено разом із сьогоднішнім рухом. Поки ніхто не бачить — додай когось через 🤝 Рух разом.",
        "de": "💬 Bei der heutigen Bewegung gespeichert. Noch sieht es niemand — "
              "füge jemanden über 🤝 Bewegen mit hinzu.",
    },
    "log_usage": {"en": "Usage: /log <what you did>", "uk": "Використання: /log <твоя активність>", "de": "Verwendung: /log <was du gemacht hast>"},
    # ── feedback ──
    "ask_feedback": {
        "en": "What's on your mind? Write your question or idea in one message — I'll pass it on.",
        "uk": "Що скажеш? Напиши питання або ідею одним повідомленням — я передам.",
        "de": "Was hast du auf dem Herzen? Schreib deine Frage oder Idee in einer Nachricht — ich leite sie weiter.",
    },
    "feedback_sent": {
        "en": "Thanks — passed on to the team 🙏",
        "uk": "Дякую — передав команді 🙏",
        "de": "Danke — an das Team weitergeleitet 🙏",
    },
    # Base form is deliberately genderless in Ukrainian, for users we haven't asked.
    "crew_move":   {"en": "{name} moved today", "uk": "{name} — рух сьогодні", "de": "{name} hat sich heute bewegt"},
    "crew_move_m": {"uk": "{name} рухався сьогодні"},
    "crew_move_f": {"uk": "{name} рухалася сьогодні"},
    "btn_undo": {"en": "🗑 Undo", "uk": "🗑 Скасувати", "de": "🗑 Rückgängig"},
    "undo_done": {
        "en": "🗑 Move removed — deleted from your crew's chats too.",
        "uk": "🗑 Рух видалено — прибрано і з чатів твого кола.",
        "de": "🗑 Bewegung entfernt — auch aus den Chats deiner Crew gelöscht.",
    },
    "undo_too_late": {
        "en": "Too late — a move can only be taken back within {secs} seconds.",
        "uk": "Запізно — рух можна скасувати лише протягом {secs} секунд.",
        "de": "Zu spät — eine Bewegung lässt sich nur innerhalb von {secs} Sekunden zurücknehmen.",
    },
    "undo_none": {
        "en": "Nothing to undo — you haven't logged a move today.",
        "uk": "Нічого скасовувати — сьогодні ще немає руху.",
        "de": "Nichts rückgängig zu machen — du hast heute noch nichts erfasst.",
    },
    "zap_btn": {"en": "⚡", "uk": "⚡", "de": "⚡"},
    "zap_btn_sent": {"en": "⚡ sent ✓", "uk": "⚡ надіслано ✓", "de": "⚡ gesendet ✓"},
    "zap_sent": {"en": "⚡ sent!", "uk": "⚡ надіслано!", "de": "⚡ gesendet!"},
    "zap_already": {"en": "You already sent a ⚡", "uk": "⚡ вже надіслано", "de": "Du hast schon ein ⚡ gesendet"},
    "zap_own": {"en": "That's your own move 🙂", "uk": "Це твій власний рух 🙂", "de": "Das ist deine eigene Bewegung 🙂"},
    # ── crew ──
    # Three parts, with the invite link between them: the prompt goes last so it
    # sits right above the input box, next to where you'd act on it. The
    # "your crew sees your moves" explainer lives in /info — /move is a command
    # people run repeatedly, and onboarding text wears out fast.
    # Hidden people are still in the crew, so listing them alongside everyone
    # else made the menu claim you're moving with someone you've muted.
    # Spells out both branches, because typing a name does two different things
    # depending on whether that person is already in your crew. "Participant's
    # name", not "username": it's the name they registered with, and @handle
    # would send people looking in the wrong place.
    # Says what the buttons do, and nothing else. Inviting is the link above this
    # message; typing a name still works but no longer needs advertising, since
    # the link reaches people who aren't in Move yet as well as people who are.
    "crew_prompt": {
        "en": "🤝 Your crew — tap someone to hide their moves or remove them:",
        "uk": "🤝 Твоє коло — обери когось, щоб сховати рухи або прибрати:",
        "de": "🤝 Deine Crew — tippe auf jemanden zum Ausblenden oder Entfernen:",
    },
    # Impersonal in Ukrainian and German: "прихований" and "ausgeblendet" would
    # both have to agree with a gender the bot often doesn't know.
    "crew_hidden_line": {
        "en": "{name} is 🙈 hidden until {until}",
        "uk": "{name} — 🙈 сховано до {until}",
        "de": "{name} — 🙈 ausgeblendet bis {until}",
    },
    "crew_prompt_empty": {
        "en": "Share the link above, or type a name if they're already on Move:",
        "uk": "Надішли посилання вище, або напиши ім'я, якщо людина вже в Move:",
        "de": "Teile den Link oben, oder gib einen Namen ein, wenn die Person schon dabei ist:",
    },
    "btn_back": {"en": "← Back", "uk": "← Назад", "de": "← Zurück"},
    # No "or send /move": the prompt is still armed, so retyping is the answer,
    # and the way back to the menu is the 🤝 button sitting on screen anyway.
    "crew_not_found": {"en": "No one named \"{name}\". Try again.", "uk": "Нікого з ім'ям «{name}». Спробуй ще.", "de": "Niemand namens „{name}“. Versuch es erneut."},
    # Adding someone is a request, never a fait accompli: moves are photos and
    # videos of people, so nobody's move travels anywhere they didn't agree to.
    "crew_request_sent": {
        "en": "🤝 Asked {name} to move with you.\n\nYou'll be connected once they accept.",
        "uk": "🤝 Запит надіслано: {name}.\n"
              "\n"
              "З'єднаємо, щойно вони погодяться.",
        "de": "🤝 {name} gefragt, ob ihr euch zusammen bewegt.\n\n"
              "Ihr werdet verbunden, sobald sie zustimmen.",
    },
    # Same decision as crew_request, but the owner never typed a name — they just
    # get a knock at the door, so the message has to say where it came from.
    "crew_request_link": {
        "en": "🔗 {name} opened your invite link and wants to move with you.\n\n"
              "Accept and you'll each see the other's moves.",
        "uk": "🔗 {name} відкрив(ла) твоє посилання-запрошення й хоче рухатися разом.\n"
              "\n"
              "Погодься — і бачитимете рухи одне одного.",
        "de": "🔗 {name} hat deinen Einladungslink geöffnet und möchte sich mit dir bewegen.\n\n"
              "Nimm an, und ihr seht gegenseitig eure Bewegungen.",
    },
    "crew_request": {
        "en": "🤝 {name} wants to move with you.\n\n"
              "Accept and you'll each see the other's moves.",
        "uk": "🤝 {name} хоче рухатися разом з тобою.\n"
              "\n"
              "Погодься — і бачитимете рухи одне одного.",
        "de": "🤝 {name} möchte sich mit dir zusammen bewegen.\n\n"
              "Nimm an, und ihr seht gegenseitig eure Bewegungen.",
    },
    # No gendered variants: "хоче" is present tense, which Ukrainian doesn't inflect
    # for gender — unlike the past-tense phrasing used for a logged move.
    "crew_request_accepted": {
        "en": "🤝 {name} accepted — you're now moving together.",
        "uk": "🤝 {name} погодилися — тепер рухаєтесь разом.",
        "de": "🤝 {name} hat zugestimmt — ihr bewegt euch jetzt zusammen.",
    },
    "crew_request_gone": {
        "en": "That request is no longer valid.",
        "uk": "Цей запит уже недійсний.",
        "de": "Diese Anfrage gilt nicht mehr.",
    },
    "btn_accept": {"en": "🤝 Accept", "uk": "🤝 Погодитись", "de": "🤝 Annehmen"},
    "btn_decline": {"en": "Not now", "uk": "Не зараз", "de": "Nicht jetzt"},
    "crew_added_back": {
        "en": "🤝 Added {name} — you're now moving together.",
        "uk": "🤝 {name} додано — тепер рухаєтесь разом.",
        "de": "🤝 {name} hinzugefügt — ihr bewegt euch jetzt zusammen.",
    },
    "crew_in_list": {"en": "{name} is in your crew{status}. What now?", "uk": "{name} у твоєму колі{status}. Що далі?", "de": "{name} ist in deiner Crew{status}. Was nun?"},
    # Not "mute": nothing is silenced, their moves simply don't arrive until the
    # date. "Без звуку" had people asking which sound the bot meant.
    "crew_muted_until": {
        "en": " (🙈 hidden until {until})",
        "uk": " (🙈 не показуємо до {until})",
        "de": " (🙈 ausgeblendet bis {until})",
    },
    # Removal is symmetric and needs the other side's consent to undo, so it asks
    # first — and says what "removing" now costs.
    "crew_remove_confirm": {
        "en": "🗑 Remove {name} from your crew?\n\n"
              "The link goes both ways, so it disappears for both of you. To get it "
              "back you'd have to send a request and wait for them to accept.",
        "uk": "🗑 Прибрати {name} з кола?\n\n"
              "Зв'язок взаємний, тож зникне з обох боків. Щоб повернути, доведеться "
              "надіслати запит і дочекатися згоди.",
        "de": "🗑 {name} aus deiner Crew entfernen?\n\n"
              "Die Verbindung gilt in beide Richtungen und verschwindet für euch "
              "beide. Zurückholen geht nur mit einer neuen Anfrage und ihrer Zustimmung.",
    },
    "btn_remove_yes": {"en": "🗑 Yes, remove", "uk": "🗑 Так, прибрати",
                       "de": "🗑 Ja, entfernen"},
    "crew_removed": {
        "en": "🗑 {name} removed — the link is gone on both sides.",
        "uk": "🗑 {name} прибрано — зв'язок зник з обох боків.",
        "de": "🗑 {name} entfernt — die Verbindung ist auf beiden Seiten weg.",
    },
    "crew_muted": {
        "en": "🙈 {name}: moves hidden until {until}.",
        "uk": "🙈 {name}: рухи не показуємо до {until}.",
        "de": "🙈 {name}: Bewegungen bis {until} ausgeblendet.",
    },
    "crew_unmuted": {
        "en": "👀 {name}: moves are coming through again.",
        "uk": "👀 {name}: рухи знову приходять.",
        "de": "👀 {name}: Bewegungen kommen wieder an.",
    },
    "btn_unmute": {"en": "👀 Show again", "uk": "👀 Показувати знову", "de": "👀 Wieder anzeigen"},
    "btn_mute_1d": {"en": "🙈 Hide 1 day", "uk": "🙈 Сховати на 1 день", "de": "🙈 1 Tag ausblenden"},
    "btn_mute_1w": {"en": "🙈 Hide 1 week", "uk": "🙈 Сховати на 1 тиждень", "de": "🙈 1 Woche ausblenden"},
    # "Remove" alone begs the question "from what?" — the menu also offers hiding.
    "btn_remove": {"en": "🗑 Remove from crew", "uk": "🗑 Прибрати з кола",
                   "de": "🗑 Aus der Crew entfernen"},
    "cancelled": {"en": "Cancelled.", "uk": "Скасовано.", "de": "Abgebrochen."},
    # ── radar ──
    # Two separate questions, asked one after the other: receiving and sharing are
    # independent choices, and one menu holding both made the toggle easy to miss.
    "radar_menu": {
        "en": "📡 Radar shows you a move from someone outside your crew.\n\n"
              "Receiving: {current}\n\nHow often?",
        "uk": "📡 Радар показує рух від учасника поза твоїм колом.\n"
              "\n"
              "Обери, як часто отримувати: {current}",
        "de": "📡 Radar zeigt dir eine Bewegung von jemandem außerhalb deiner Crew.\n\n"
              "Empfangen: {current}\n\nWie oft?",
    },
    "radar_share_menu": {
        "en": "📡 And your own moves — may radar show them to people outside your crew?\n\n"
              "Always anonymous: they see the move, never your name.\n\nNow: {current}",
        "uk": "📡 А твої власні рухи — чи може радар показувати їх людям поза твоїм колом?\n"
              "\n"
              "Завжди анонімно: вони бачать рух, але не твоє ім'я.\n"
              "\n"
              "Зараз: {current}",
        "de": "📡 Und deine eigenen Bewegungen — darf Radar sie Leuten außerhalb deiner "
              "Crew zeigen?\n\nImmer anonym: sie sehen die Bewegung, nie deinen Namen.\n\n"
              "Jetzt: {current}",
    },
    "radar_state_on": {"en": "sharing ✅", "uk": "ділюся ✅", "de": "wird geteilt ✅"},
    "radar_state_off": {"en": "private 🚫", "uk": "приватно 🚫", "de": "privat 🚫"},
    "btn_share_yes": {"en": "Yes, share ✅", "uk": "Так, ділитися ✅", "de": "Ja, teilen ✅"},
    "btn_share_no": {"en": "No, keep private 🚫", "uk": "Ні, лишити приватним 🚫",
                     "de": "Nein, privat behalten 🚫"},
    "radar_pull_btn": {"en": "👀 Show me someone now", "uk": "👀 Показати когось зараз",
                       "de": "👀 Zeig mir jetzt jemanden"},
    "radar_pull_none": {
        "en": "📡 Nothing new right now — you've seen everyone who moved lately. "
              "Try again tomorrow.",
        "uk": "📡 Зараз нічого нового — нових облич поки немає. Спробуй завтра.",
        "de": "📡 Gerade nichts Neues — du hast alle gesehen, die sich zuletzt bewegt "
              "haben. Versuch es morgen wieder.",
    },
    "radar_block_btn": {"en": "🚫 Not this person again", "uk": "🚫 Більше не показувати цю людину",
                        "de": "🚫 Diese Person nicht mehr"},
    "radar_report_btn": {"en": "⚠️ Report", "uk": "⚠️ Поскаржитись", "de": "⚠️ Melden"},
    "radar_reported": {
        "en": "⚠️ Reported — a human will look at it. You won't see this person again either.",
        "uk": "⚠️ Скаргу надіслано — її перегляне людина. Цю людину ти більше не побачиш.",
        "de": "⚠️ Gemeldet — ein Mensch schaut es sich an. Diese Person siehst du auch nicht mehr.",
    },
    # Neutral on purpose. The reports are unverified, most people who trip this
    # are careless rather than malicious, and an accusation makes them leave.
    "warned": {
        "en": "⚠️ A few people flagged one of your moves.\n\n"
              "Nothing has changed — you're still sharing as before. Radar shows your "
              "move to strangers, so keep it to your own activity.\n\n"
              "Warnings on your account: {n} of {max}.",
        "uk": "⚠️ Кілька людей поскаржились на один з твоїх рухів.\n"
              "\n"
              "Нічого не змінилось — ти ділишся як і раніше. Радар показує твій рух незнайомцям, тож нехай це буде твоя власна активність.\n"
              "\n"
              "Попереджень на акаунті: {n} з {max}.",
        "de": "⚠️ Ein paar Leute haben eine deiner Bewegungen gemeldet.\n\n"
              "Nichts hat sich geändert — du teilst wie bisher. Radar zeigt deine "
              "Bewegung Fremden, also halte dich an deine eigene Aktivität.\n\n"
              "Verwarnungen auf deinem Konto: {n} von {max}.",
    },
    "suspended": {
        "en": "🚫 Radar sharing is paused on your account after {n} warnings.\n\n"
              "Your crew is unaffected — you still post to them, and still see their "
              "moves. Only strangers no longer see yours.\n\n"
              "A human will review this.",
        "uk": "🚫 Показ у радарі призупинено після {n} попереджень.\n"
              "\n"
              "Твоє коло це не зачіпає — ти й далі надсилаєш їм рухи та бачиш їхні. Просто незнайомці більше не бачать твоїх.\n"
              "\n"
              "Це перегляне людина.",
        "de": "🚫 Radar-Teilen ist nach {n} Verwarnungen pausiert.\n\n"
              "Deine Crew ist nicht betroffen — du postest weiter an sie und siehst "
              "ihre Bewegungen. Nur Fremde sehen deine nicht mehr.\n\n"
              "Ein Mensch schaut sich das an.",
    },
    "restored": {
        "en": "✅ Reviewed — radar sharing is back on. Sorry for the interruption.",
        "uk": "✅ Перевірено — показ у радарі знову увімкнено. Вибачте за паузу.",
        "de": "✅ Geprüft — Radar-Teilen ist wieder an. Entschuldige die Unterbrechung.",
    },
    "banned": {
        "en": "🚫 Radar is switched off on your account. Your crew is unaffected.",
        "uk": "🚫 Радар вимкнено на твоєму акаунті. Твоє коло це не зачіпає.",
        "de": "🚫 Radar ist für dein Konto abgeschaltet. Deine Crew ist nicht betroffen.",
    },
    "radar_share_locked": {
        "en": "🚫 Radar sharing is paused on your account and can't be turned back on "
              "here. You can still receive radar, and your crew is unaffected.",
        "uk": "🚫 Показ у радарі призупинено — увімкнути його тут не можна. Отримувати радар ти й далі можеш, і твоє коло це не зачіпає.",
        "de": "🚫 Radar-Teilen ist pausiert und kann hier nicht wieder aktiviert werden. "
              "Empfangen kannst du weiter, und deine Crew ist nicht betroffen.",
    },
    "radar_reported_already": {
        "en": "⚠️ You've already reported this one.",
        "uk": "⚠️ Скаргу на це вже надіслано.",
        "de": "⚠️ Das hast du bereits gemeldet.",
    },
    "radar_blocked": {
        "en": "🚫 Done — this person won't turn up in your radar again.",
        "uk": "🚫 Готово — ця людина більше не з'явиться у твоєму радарі.",
        "de": "🚫 Erledigt — diese Person taucht in deinem Radar nicht mehr auf.",
    },
    # Icon last, matching the share question's "Так, ділитися ✅". Sun/moon read
    # as day/month without needing to be read; 🚫 is the same "no" as over there.
    "radar_daily": {"en": "Daily ☀️", "uk": "Щодня ☀️", "de": "Täglich ☀️"},
    "radar_weekly": {"en": "Weekly 📆", "uk": "Щотижня 📆", "de": "Wöchentlich 📆"},
    "radar_monthly": {"en": "Monthly 🌙", "uk": "Щомісяця 🌙", "de": "Monatlich 🌙"},
    "radar_off": {"en": "Off 🚫", "uk": "Вимкнено 🚫", "de": "Aus 🚫"},
    "radar_set": {"en": "📡 Radar: {label}.", "uk": "📡 Радар: {label}.", "de": "📡 Radar: {label}."},
    "radar_share_on": {"en": "📡 Share my moves: ON ✅", "uk": "📡 Ділитися моїми рухами: УВІМК ✅", "de": "📡 Meine Bewegungen teilen: AN ✅"},
    "radar_share_off": {"en": "📡 Share my moves: OFF 🚫", "uk": "📡 Ділитися моїми рухами: ВИМК 🚫", "de": "📡 Meine Bewegungen teilen: AUS 🚫"},
    # Anonymous on purpose: radar shares the move, never who made it.
    "radar_received": {
        "en": "📡 Someone outside your crew moved today.",
        "uk": "📡 Хтось поза твоїм колом рухався сьогодні.",
        "de": "📡 Jemand außerhalb deiner Crew hat sich heute bewegt.",
    },
    # ── pause ──
    "pause_menu": {"en": "⏸️ Pause everything — no moves from your crew, no radar.\n\nPause for:", "uk": "⏸️ Призупинити все — жодних рухів від кола, жодного радару.\n\nПризупинити на:", "de": "⏸️ Alles pausieren — keine Bewegungen der Crew, kein Radar.\n\nPausieren für:"},
    # "Продовжити" alone is ambiguous — it reads as both "extend" and "carry on
    # (i.e. resume)". Naming the object removes the ambiguity.
    "pause_active": {"en": "⏸️ Paused until {until}.\n\nExtend the pause or resume:",
                     "uk": "⏸️ Призупинено до {until}.\n\nПродовжити зупинку або відновити:",
                     "de": "⏸️ Pausiert bis {until}.\n\nPause verlängern oder fortsetzen:"},
    # An escalating ladder, so the three are told apart at a glance rather than
    # read: one night, one week on the calendar, one month.
    "pause_1d": {"en": "🌙 1 day", "uk": "🌙 1 день", "de": "🌙 1 Tag"},
    "pause_1w": {"en": "📅 1 week", "uk": "📅 1 тиждень", "de": "📅 1 Woche"},
    "pause_1m": {"en": "🗓 1 month", "uk": "🗓 1 місяць", "de": "🗓 1 Monat"},
    "pause_resume": {"en": "▶️ Resume now", "uk": "▶️ Відновити зараз", "de": "▶️ Jetzt fortsetzen"},
    "pause_set": {"en": "⏸️ Paused until {until}.", "uk": "⏸️ Призупинено до {until}.", "de": "⏸️ Pausiert bis {until}."},
    "pause_resumed": {"en": "▶️ Resumed.", "uk": "▶️ Відновлено.", "de": "▶️ Fortgesetzt."},
    # ── reports ──
    "zap_report": {"en": "⚡ Yesterday your move got {n} {word}.", "uk": "⚡ Вчора твій рух отримав {n} {word}.", "de": "⚡ Gestern hat deine Bewegung {n} {word} bekommen."},
    "zap_word_one":  {"en": "lightning", "uk": "блискавку", "de": "Blitz"},
    "zap_word_few":  {"en": "lightnings", "uk": "блискавки", "de": "Blitze"},
    "zap_word_many": {"en": "lightnings", "uk": "блискавок", "de": "Blitze"},
    "milestone": {"en": "🎉 {name}, {days} days in a row! Keep moving 💪", "uk": "🎉 {name}, {days} днів поспіль! Так тримати 💪", "de": "🎉 {name}, {days} Tage in Folge! Weiter so 💪"},
    "summary_header": {"en": "📅 {month} — {name}", "uk": "📅 {month} — {name}", "de": "📅 {month} — {name}"},
    "summary_days": {"en": "🏃 Days moved: {count} of {total} ({pct}%)", "uk": "🏃 Днів у русі: {count} з {total} ({pct}%)", "de": "🏃 Bewegte Tage: {count} von {total} ({pct}%)"},
    "summary_streak": {"en": "🔥 Longest streak: {days} days", "uk": "🔥 Найдовша серія: {days} днів", "de": "🔥 Längste Serie: {days} Tage"},
    "summary_zaps": {"en": "⚡ Lightnings received: {n}", "uk": "⚡ Отримано блискавок: {n}", "de": "⚡ Erhaltene Blitze: {n}"},
    "btn_new_link": {
        "en": "🔄 New link", "uk": "🔄 Нове посилання", "de": "🔄 Neuer Link",
    },
    "invite_rotated": {
        "en": "🔄 Done — here's your new link. The old one no longer works.\n\n{link}",
        "uk": "🔄 Готово — ось нове посилання. Старе більше не працює.\n"
              "\n"
              "{link}",
        "de": "🔄 Fertig — hier ist dein neuer Link. Der alte funktioniert nicht mehr.\n\n{link}",
    },
    "invite_text": {
        "en": "🔗 Share this link with anyone you'd like to move with:\n\n{link}\n\n"
              "When they tap it, you'll be added to each other's crew automatically — "
              "whether they're new here or already registered.",
        "uk": "🔗 Надішли це посилання тому, з ким хочеш рухатись разом:\n"
              "\n"
              "{link}\n"
              "\n"
              "Коли вони його відкриють, ти автоматично потрапиш у їхнє коло, а вони — у твоє. Неважливо, нові вони тут чи вже зареєстровані.",
        "de": "🔗 Teile diesen Link mit allen, mit denen du dich bewegen möchtest:\n\n{link}\n\n"
              "Wenn sie ihn antippen, landet ihr automatisch in der Crew des anderen — "
              "egal ob neu hier oder schon registriert.",
    },
    # Only asked of Ukrainian speakers — the other two languages don't inflect here.
    "ask_gender": {"uk": "Як про тебе писати?", "en": "How should we refer to you?",
                   "de": "Wie sollen wir über dich schreiben?"},
    "gender_m": {"uk": "Він", "en": "He", "de": "Er"},
    "gender_f": {"uk": "Вона", "en": "She", "de": "Sie"},
    "btn_language": {"en": "🌍 Language", "uk": "🌍 Мова", "de": "🌍 Sprache"},
    "lang_changed": {
        "en": "🌍 Language set to English.",
        "uk": "🌍 Мову змінено на українську.",
        "de": "🌍 Sprache auf Deutsch gestellt.",
    },
    "invite_line": {
        "en": "Send 🔗 your invite link to future members:\n{link}",
        "uk": "Надішли 🔗 своє посилання-запрошення майбутнім учасникам:\n"
              "{link}",
        "de": "Schick 🔗 deinen Einladungslink an künftige Mitglieder:\n{link}",
    },
    "invite_connected": {
        "en": "🤝 You and {name} are now moving together!",
        "uk": "🤝 Тепер ти з {name} рухаєшся разом!",
        "de": "🤝 Du und {name} bewegt euch jetzt zusammen!",
    },
    "invite_already": {
        "en": "You're already moving with {name} 🤝",
        "uk": "Ти вже рухаєшся з {name} 🤝",
        "de": "Du bewegst dich schon mit {name} 🤝",
    },
    "invite_self": {
        "en": "That's your own invite link 🙂 Share it with someone else.",
        "uk": "Це твоє власне посилання 🙂 Надішли його комусь іншому.",
        "de": "Das ist dein eigener Link 🙂 Teile ihn mit jemand anderem.",
    },
    "summary_hint": {
        "en": "📅 /summary — all your months, any time.",
        "uk": "📅 /summary — усі твої місяці, будь-коли.",
        "de": "📅 /summary — alle deine Monate, jederzeit.",
    },
    "summary_all_header": {"en": "📊 Your months", "uk": "📊 Твої місяці", "de": "📊 Deine Monate"},
    "summary_none": {"en": "No moves recorded yet.", "uk": "Ще немає записаних рухів.", "de": "Noch keine Bewegungen erfasst."},
}


# Shown before we know their language, so it carries all three.
_LANG_PROMPT = "🌍 Choose your language\nОберіть мову\nSprache wählen"


def _kb_lang() -> dict:
    # One per row: "Українська" is clipped when three share a row, and picking a
    # language is a one-time action so the extra height costs nothing. No flags —
    # a flag names a country, not a language.
    return {"inline_keyboard": [
        [{"text": "English", "callback_data": "mv:lang:en"}],
        [{"text": "Українська", "callback_data": "mv:lang:uk"}],
        [{"text": "Deutsch", "callback_data": "mv:lang:de"}],
    ]}


def _main_kb(lang: str = "en") -> dict:
    return {
        "keyboard": [
            [{"text": _t("btn_move", lang)}, {"text": _t("btn_radar", lang)}],
            [{"text": _t("btn_pause", lang)}, {"text": _t("btn_info", lang)}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


# Labels from earlier versions. A reply keyboard lives in the user's client until
# it's re-sent, so a renamed button would otherwise stop working for everyone who
# already has the old one.
_LEGACY_BUTTONS = {"🤝 Рухатись з": "/move"}


def _build_button_map() -> dict[str, str]:
    m: dict[str, str] = dict(_LEGACY_BUTTONS)
    for key, cmd in (("btn_move", "/move"), ("btn_radar", "/radar"),
                     ("btn_pause", "/pause"), ("btn_info", "/info")):
        for lang in _SUPPORTED_LANGS:
            m[_STRINGS[key][lang]] = cmd
    return m


_BUTTON_TO_CMD = _build_button_map()

_MONTHS = {
    "en": ["", "January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "uk": ["", "січень", "лютий", "березень", "квітень", "травень", "червень",
           "липень", "серпень", "вересень", "жовтень", "листопад", "грудень"],
    "de": ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"],
}


# ── user / state helpers ─────────────────────────────────────────────────────

def _user(cur, tg_id: int):
    cur.execute("SELECT * FROM move_users WHERE telegram_user_id = %s", (tg_id,))
    return cur.fetchone()


def _lang(cur, tg_id: int) -> str:
    u = _user(cur, tg_id)
    return _norm_lang(u["language_code"] if u else None)


def _short_date(dt) -> str:
    """01.09 — numeric on purpose.

    strftime("%b %d") printed "Sep 01" inside Ukrainian and German sentences,
    and _MONTHS only holds nominative names ("вересень"), which don't fit after
    "до" (Ukrainian wants the genitive "вересня"). A numeric date sidesteps both
    the translation and the grammar.
    """
    return dt.strftime("%d.%m")


def _fold(s: str) -> str:
    """Lowercase and strip accents, so "Master Yu" finds "Máster Yu"."""
    decomposed = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().strip()


def _by_name(cur, name: str):
    cur.execute("SELECT * FROM move_users WHERE LOWER(participant_name) = LOWER(%s)", (name,))
    hit = cur.fetchone()
    if hit:
        return hit
    # Nobody types the diacritic. Without this, a name like "Máster Yu" can only
    # be reached by someone who knows how to enter á — the person is effectively
    # unaddressable, and the bot just says "no one by that name".
    target = _fold(name)
    if not target:
        return None
    cur.execute("SELECT * FROM move_users WHERE participant_name IS NOT NULL")
    for row in cur.fetchall():
        if _fold(row["participant_name"]) == target:
            return row
    return None


def _get_state(cur, tg_id: int) -> str | None:
    cur.execute("SELECT state, created_at FROM move_state WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    if not row:
        return None
    if row["created_at"] and (datetime.now(timezone.utc) - row["created_at"]).total_seconds() > _STATE_TIMEOUT_MINUTES * 60:
        cur.execute("DELETE FROM move_state WHERE telegram_user_id = %s", (tg_id,))
        return None
    return row["state"]


def _set_state(cur, tg_id: int, state: str) -> None:
    cur.execute(
        "INSERT INTO move_state (telegram_user_id, state, created_at) VALUES (%s, %s, NOW()) "
        "ON CONFLICT (telegram_user_id) DO UPDATE SET state = EXCLUDED.state, created_at = NOW()",
        (tg_id, state),
    )


def _clear_state(cur, tg_id: int) -> None:
    cur.execute("DELETE FROM move_state WHERE telegram_user_id = %s", (tg_id,))


def _valid_name(text: str) -> bool:
    t = text.strip()
    return 0 < len(t) <= 32 and all(c.isalpha() or c.isspace() or c in "-_'" for c in t)


# ── streaks ──────────────────────────────────────────────────────────────────

def _streak(cur, tg_id: int, as_of: date | None = None) -> int:
    """Consecutive days ending today (or yesterday — a day isn't over yet)."""
    today = as_of or date.today()
    cur.execute(
        "SELECT entry_date FROM move_entries WHERE telegram_user_id = %s "
        "ORDER BY entry_date DESC LIMIT 400",
        (tg_id,),
    )
    days = [r["entry_date"] if hasattr(r["entry_date"], "toordinal")
            else date.fromisoformat(str(r["entry_date"])[:10]) for r in cur.fetchall()]
    if not days:
        return 0
    if days[0] < today - timedelta(days=1):
        return 0
    streak, expected = 0, days[0]
    for d in days:
        if d == expected:
            streak += 1
            expected -= timedelta(days=1)
        elif d < expected:
            break
    return streak


# ── crew helpers ─────────────────────────────────────────────────────────────

def _crew_names(cur, tg_id: int) -> list[str]:
    cur.execute("SELECT crew_name FROM move_crew WHERE telegram_user_id = %s ORDER BY crew_name", (tg_id,))
    return [r["crew_name"] for r in cur.fetchall()]


def _recipients(cur, tg_id: int, sender_name: str) -> list[tuple[int, int, str]]:
    """(tg_id, chat_id, name) for everyone who should see this move: in my crew,
    not paused, hasn't muted me, and accepts moves from me."""
    names = _crew_names(cur, tg_id)
    if not names:
        return []
    if "__all__" in names:
        cur.execute("SELECT * FROM move_users WHERE telegram_user_id != %s", (tg_id,))
        cands = cur.fetchall()
    else:
        cur.execute("SELECT * FROM move_users WHERE participant_name = ANY(%s)", (names,))
        cands = cur.fetchall()

    out = []
    now = datetime.now(timezone.utc)
    for c in cands:
        rid = c["telegram_user_id"]
        if c["paused_until"] and c["paused_until"] > now:
            continue
        cur.execute(
            "SELECT 1 FROM move_mute WHERE telegram_user_id = %s AND LOWER(muted_name) = LOWER(%s) "
            "AND muted_until > NOW()",
            (rid, sender_name),
        )
        if cur.fetchone():
            continue
        cur.execute("SELECT 1 FROM move_receive WHERE telegram_user_id = %s LIMIT 1", (rid,))
        if cur.fetchone():
            cur.execute(
                "SELECT 1 FROM move_receive WHERE telegram_user_id = %s "
                "AND (LOWER(from_name) = LOWER(%s) OR from_name = '__all__')",
                (rid, sender_name),
            )
            if not cur.fetchone():
                continue
        out.append((rid, c["chat_id"] or rid, c["participant_name"]))
    return out


# ── ⚡ ───────────────────────────────────────────────────────────────────────

def _zap_count(cur, entry_id: int) -> int:
    cur.execute("SELECT COUNT(*) AS n FROM move_reactions WHERE entry_id = %s", (entry_id,))
    return cur.fetchone()["n"] or 0


def _zap_kb(entry_id: int, sent: bool = False, lang: str = "en", radar: bool = False) -> dict:
    """No running total — a move isn't a popularity contest. You only see whether
    *you* cheered; the author gets the tally next morning.

    A radar copy carries a second button: this came from a stranger, so the
    viewer needs a way to never see them again.
    """
    rows = [[{"text": _t("zap_btn_sent" if sent else "zap_btn", lang),
              "callback_data": f"mv:zap:{entry_id}"}]]
    if radar:
        # Block is "stop showing me this"; report is "someone should look at this".
        # One per row — sharing a row clips the block label, which is a sentence.
        rows.append([{"text": _t("radar_block_btn", lang),
                      "callback_data": f"mv:rblock:{entry_id}"}])
        rows.append([{"text": _t("radar_report_btn", lang),
                      "callback_data": f"mv:rreport:{entry_id}"}])
    return {"inline_keyboard": rows}


def _revoke(cur, conn, tg_id: int, chat_id: int, lang: str, entry_id: int | None = None) -> bool:
    """Take today's move back — delete every copy the bot placed in other chats,
    then drop the entry. Telegram lets a bot delete its own messages for 48h,
    which covers a same-day move; anything it can't delete is skipped silently.

    Only within _UNDO_WINDOW_SECONDS of logging: a move your crew has already
    seen and cheered shouldn't be able to vanish. Returns False if refused.

    Needs an explicit trigger: Telegram never tells a bot that the user deleted
    their original message in a private chat.
    """
    cur.execute(
        "SELECT id, created_at FROM move_entries WHERE telegram_user_id = %s AND entry_date = %s",
        (tg_id, date.today()),
    )
    e = cur.fetchone()
    # entry_id guards a stale button from an earlier day revoking today's move.
    if not e or (entry_id is not None and e["id"] != entry_id):
        _send(chat_id, _t("undo_none", lang))
        return False
    age = (datetime.now(timezone.utc) - e["created_at"]).total_seconds()
    if age > _UNDO_WINDOW_SECONDS:
        _send(chat_id, _t("undo_too_late", lang, secs=_UNDO_WINDOW_SECONDS))
        return False
    cur.execute("SELECT chat_id, message_id FROM move_forwards WHERE entry_id = %s", (e["id"],))
    for f in cur.fetchall():
        _api_call("deleteMessage", {"chat_id": f["chat_id"], "message_id": f["message_id"]})
    # move_forwards / move_reactions cascade off the entry.
    cur.execute("DELETE FROM move_entries WHERE id = %s", (e["id"],))
    conn.commit()
    _send(chat_id, _t("undo_done", lang), reply_markup=_main_kb(lang))
    u = _user(cur, tg_id)
    _log(f"🗑 Move: revoked\n• {u['participant_name'] if u else tg_id}")
    return True


# ── moderation ───────────────────────────────────────────────────────────────

def _active_warnings(cur, tg_id: int) -> int:
    """Warnings that still count: not cleared by a moderator, not yet expired."""
    cur.execute(
        "SELECT COUNT(*) AS n FROM move_warnings WHERE telegram_user_id = %s "
        "AND cleared_at IS NULL AND created_at > NOW() - make_interval(days => %s)",
        (tg_id, _WARNING_TTL_DAYS),
    )
    return cur.fetchone()["n"] or 0


def _banned(u) -> bool:
    """Tolerates a row from before 044 added the column, as _tgen does for gender."""
    return bool(u and "banned_at" in u and u["banned_at"])


def _is_suspended(cur, tg_id: int) -> bool:
    cur.execute(
        "SELECT 1 FROM move_suspensions WHERE telegram_user_id = %s AND lifted_at IS NULL",
        (tg_id,),
    )
    return cur.fetchone() is not None


def _mod_kb(tg_id: int) -> dict:
    """Actions a moderator can take, attached to the log-channel message."""
    return {"inline_keyboard": [[
        {"text": "✅ Restore", "callback_data": f"mv:mod:restore:{tg_id}"},
        {"text": "🚫 Ban", "callback_data": f"mv:mod:ban:{tg_id}"},
    ]]}


def _suspend(cur, conn, author, warnings: int) -> None:
    """Pause radar sharing, pending a human. Reversible by design."""
    tg_id = author["telegram_user_id"]
    if _is_suspended(cur, tg_id):
        return
    cur.execute("UPDATE move_users SET radar_send = FALSE WHERE telegram_user_id = %s", (tg_id,))
    cur.execute("INSERT INTO move_suspensions (telegram_user_id) VALUES (%s)", (tg_id,))
    conn.commit()
    _send(author["chat_id"] or tg_id,
          _t("suspended", _norm_lang(author["language_code"]), n=warnings))
    _log(f"🛑 Move: SUSPENDED (auto)\n"
         f"• {author['participant_name']} (id {tg_id})\n"
         f"• {warnings} active warnings\n"
         f"• radar sharing off — crew untouched",
         reply_markup=_mod_kb(tg_id))


def _warn(cur, conn, author, entry_id: int) -> None:
    """One warning per entry, however many people reported it."""
    tg_id = author["telegram_user_id"]
    cur.execute(
        "INSERT INTO move_warnings (telegram_user_id, entry_id) VALUES (%s, %s) "
        "ON CONFLICT (telegram_user_id, entry_id) DO NOTHING RETURNING id",
        (tg_id, entry_id),
    )
    if cur.fetchone() is None:
        conn.commit()
        return                                # already warned for this move
    conn.commit()
    n = _active_warnings(cur, tg_id)
    if n >= _WARNINGS_PER_SUSPENSION:
        _suspend(cur, conn, author, n)
        return
    _send(author["chat_id"] or tg_id,
          _t("warned", _norm_lang(author["language_code"]),
             n=n, max=_WARNINGS_PER_SUSPENSION))
    _log(f"⚠️ Move: warning {n}/{_WARNINGS_PER_SUSPENSION}\n"
         f"• {author['participant_name']} (id {tg_id})\n"
         f"• entry #{entry_id}",
         reply_markup=_mod_kb(tg_id))


# ── logging a move ───────────────────────────────────────────────────────────

def _deliver(cur, conn, user, entry_id: int, media: tuple | None, text_body: str | None) -> list[str]:
    """Copy the move to each crew member, remembering where it landed so a late
    comment can be threaded under it. Returns the names it reached."""
    sender = user["participant_name"]
    gender = user["gender"] if "gender" in user else None
    names = []

    def track(rid, chat_id, res, kind):
        if res and res.get("message_id"):
            cur.execute(
                "INSERT INTO move_forwards (entry_id, recipient_tg_id, chat_id, message_id, kind) "
                "VALUES (%s, %s, %s, %s, %s)",
                (entry_id, rid, chat_id, res["message_id"], kind),
            )

    for rid, chat_id, rname in _recipients(cur, user["telegram_user_id"], sender):
        rlang = _lang(cur, rid)
        header = _tgen("crew_move", rlang, gender, name=sender)
        if media:
            from_chat, msg_id = media
            track(rid, chat_id,
                  _copy(from_chat, msg_id, chat_id, reply_markup=_zap_kb(entry_id, lang=rlang)),
                  "move")
            # Tracked too, so /undo takes the "X moved today" line with it.
            track(rid, chat_id, _send(chat_id, header), "header")
        else:
            track(rid, chat_id,
                  _send(chat_id, f"{header}\n{text_body or ''}".strip(),
                        reply_markup=_zap_kb(entry_id, lang=rlang)),
                  "move")
        names.append(rname)
    conn.commit()
    return names


def _log_move(cur, conn, tg_id: int, chat_id: int, media: tuple | None, text_body: str | None) -> None:
    user = _user(cur, tg_id)
    lang = _norm_lang(user["language_code"])
    today = date.today()

    cur.execute(
        "SELECT id FROM move_entries WHERE telegram_user_id = %s AND entry_date = %s",
        (tg_id, today),
    )
    if cur.fetchone():
        # Deliberately no comment invitation here: the move it would attach to
        # is hours old, so the note goes nowhere useful and the crew shouldn't
        # be re-pinged. Comments belong to a move you *just* logged.
        _send(chat_id, _t("already_logged", lang))
        _log(f"🔁 Move: second attempt\n👤 {user['participant_name']}")
        return

    media_type = None
    src_chat = src_msg = None
    if media:
        src_chat, src_msg, media_type = media[0], media[1], media[2]
    cur.execute(
        "INSERT INTO move_entries (telegram_user_id, entry_date, media_type, chat_id, message_id, text_body) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (tg_id, today, media_type or "text", src_chat, src_msg, text_body),
    )
    entry_id = cur.fetchone()["id"]
    conn.commit()

    names = _deliver(cur, conn, user, entry_id,
                     (src_chat, src_msg) if media else None, text_body)

    streak = _streak(cur, tg_id, today)
    suffix = _t("streak_suffix", lang, days=streak) if streak > 1 else ""
    # Inline undo — the persistent reply keyboard stays regardless.
    undo_kb = {"inline_keyboard": [[
        {"text": _t("btn_undo", lang), "callback_data": f"mv:undo:{entry_id}"}
    ]]}
    if names:
        _send(chat_id, _t("logged_shared", lang, streak=suffix, names=", ".join(names)),
              reply_markup=undo_kb)
    else:
        _send(chat_id, _t("logged", lang, streak=suffix), reply_markup=undo_kb)
    # Invite a comment: the next text is treated as one (state times out on its own).
    _set_state(cur, tg_id, "await_comment")
    conn.commit()
    _log(f"🏃 Move logged\n👤 {user['participant_name']}"
         + (f"\n📤 → {', '.join(names)}" if names else "\n📤 → nobody"))
    _check_milestone(cur, conn, user, streak)


def _attach_comment(cur, conn, tg_id: int, chat_id: int, text: str) -> bool:
    """Attach a text to today's move and deliver it as a reply under each
    forwarded copy, so it reads as one post. True if it was used.

    Accepted either shortly after the move, or whenever the bot has just invited
    a comment (`await_comment`) — otherwise the invitation would be a lie.
    """
    cur.execute(
        "SELECT id, created_at, comment FROM move_entries "
        "WHERE telegram_user_id = %s AND entry_date = %s",
        (tg_id, date.today()),
    )
    e = cur.fetchone()
    if not e:
        return False
    invited = _get_state(cur, tg_id) == "await_comment"
    age = (datetime.now(timezone.utc) - e["created_at"]).total_seconds() / 60
    if not invited and age > _COMMENT_WINDOW_MINUTES:
        return False

    # Each comment is delivered on its own, but the record keeps them all.
    merged = f"{e['comment']}\n{text}" if e["comment"] else text
    cur.execute("UPDATE move_entries SET comment = %s WHERE id = %s", (merged, e["id"]))
    # Deliberately NOT clearing the state: the invitation stays open for its full
    # 10 minutes so you can add several lines, instead of only ever one.
    # Only a comment on a still-fresh move goes out. Pinging the crew about a
    # move they saw hours ago — e.g. after a rejected second bubble — is noise;
    # the note is kept on the entry either way.
    fresh = age <= _COMMENT_WINDOW_MINUTES
    targets = []
    if fresh:
        cur.execute(
            "SELECT recipient_tg_id, chat_id, message_id FROM move_forwards "
            "WHERE entry_id = %s AND kind IN ('move', 'radar')",
            (e["id"],),
        )
        targets = cur.fetchall()

    delivered = 0
    for f in targets:
        res = _send(f["chat_id"], f"💬 {text}", reply_to=f["message_id"])
        # Track the reply too, so undo takes the comment with it.
        if res and res.get("message_id"):
            delivered += 1
            cur.execute(
                "INSERT INTO move_forwards (entry_id, recipient_tg_id, chat_id, message_id, kind) "
                "VALUES (%s, %s, %s, %s, 'comment')",
                (e["id"], f["recipient_tg_id"], f["chat_id"], res["message_id"]),
            )
    conn.commit()
    # Say where it went — "added" alone invites the question "added where?"
    lang = _lang(cur, tg_id)
    if delivered:
        key = "comment_added"
    elif fresh:
        key = "comment_saved_alone"      # nobody in the crew yet
    else:
        key = "comment_saved_late"       # kept, but the crew isn't re-pinged
    _send(chat_id, _t(key, lang))
    u = _user(cur, tg_id)
    _log(f"💬 Move: comment\n👤 {u['participant_name'] if u else tg_id}: {text}"
         f"\n📤 → {delivered}")
    return True


def _check_milestone(cur, conn, user, streak: int) -> None:
    if streak not in _MILESTONES:
        return
    tg_id = user["telegram_user_id"]
    cur.execute(
        "INSERT INTO move_milestones (telegram_user_id, streak_days) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING RETURNING streak_days",
        (tg_id, streak),
    )
    if not cur.fetchone():
        return
    conn.commit()
    lang = _norm_lang(user["language_code"])
    _send(user["chat_id"] or tg_id,
          _t("milestone", lang, name=user["participant_name"], days=streak))
    _log(f"🎉 Streak milestone\n👤 {user['participant_name']}: {streak} days")


# ── commands ─────────────────────────────────────────────────────────────────

def _cmd_start(cur, conn, tg_id: int, chat_id: int, lang: str, payload: str = "") -> None:
    """`/start`, optionally with an `invitation_of_<name>_<code>` deep-link payload.

    Already registered? We don't re-register — but we still honour the invite and
    connect the two, which is the useful thing to do with a tapped link.
    """
    inviter_id = _inviter_from_payload(cur, payload)

    u = _user(cur, tg_id)
    if u and u["participant_name"]:
        if inviter_id is not None:
            _apply_invite(cur, conn, tg_id, chat_id, lang, inviter_id)
        else:
            _send(chat_id, _t("already_registered", lang, name=u["participant_name"]),
                  reply_markup=_main_kb(lang))
        return

    cur.execute(
        "INSERT INTO move_users (telegram_user_id, chat_id, language_code) VALUES (%s, %s, %s) "
        "ON CONFLICT (telegram_user_id) DO UPDATE SET chat_id = EXCLUDED.chat_id",
        (tg_id, chat_id, lang),
    )
    # Language first, then the name. Any inviter rides along in the state key.
    _set_state(cur, tg_id, f"await_lang:{inviter_id}" if inviter_id is not None else "await_lang")
    conn.commit()
    _send(chat_id, _LANG_PROMPT, reply_markup=_kb_lang())


def _invite_code(cur, tg_id: int) -> str:
    """This user's secret invite token, minting one if the row somehow lacks it.

    Migration 045 backfills every row and sets a column default, so the mint
    below should never fire — it exists so a link is never silently built from
    nothing on a database that missed the migration.
    """
    cur.execute("SELECT invite_code FROM move_users WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    if row and row["invite_code"]:
        return row["invite_code"]
    import secrets
    code = "m" + secrets.token_hex(8)[:15]
    cur.execute("UPDATE move_users SET invite_code = %s WHERE telegram_user_id = %s",
                (code, tg_id))
    return code


def _invite_link(cur, tg_id: int, name: str | None = None) -> str:
    """`inv_<code>` — nothing but a random token.

    Two things used to ride along and both were liabilities. The Telegram user
    id was not secret, so links could be forged (migration 045). The name slug
    was cosmetic and never trusted for identity, but it published the owner's
    name into every chat the link passed through, and it could be rewritten to
    name someone else — which mattered while opening a link auto-connected.
    `name` is still accepted so callers need not change.
    """
    return f"https://t.me/{_bot_username()}?start=inv_{_invite_code(cur, tg_id)}"


def _rotate_invite_code(cur, tg_id: int) -> str:
    """Issue a fresh code, killing every link handed out so far."""
    import secrets
    code = "m" + secrets.token_hex(8)[:15]
    cur.execute("UPDATE move_users SET invite_code = %s WHERE telegram_user_id = %s",
                (code, tg_id))
    return code


def _inviter_from_payload(cur, payload: str) -> int | None:
    """Resolve a deep-link payload to the inviter's id, or None.

    The last underscore-separated chunk is the token; anything before it is the
    cosmetic name slug, which is never trusted — it is spoofable by anyone who
    can type a URL, so the greeting still reads the real name from the database.

    An all-digit chunk is a legacy `..._<telegram_user_id>` link. Those are
    refused: honouring them would leave the forgery hole wide open, which is the
    whole reason for the change. Codes always start with a letter, so the two
    can never be confused.
    """
    payload = payload.strip()
    if "_" not in payload:
        return None                       # no prefix at all — not one of our links
    token = payload.rsplit("_", 1)[-1]
    if not token or token.isdigit():
        return None
    cur.execute("SELECT telegram_user_id FROM move_users WHERE invite_code = %s", (token,))
    row = cur.fetchone()
    return row["telegram_user_id"] if row else None


def _invite_line(cur, tg_id: int, lang: str, name: str | None = None) -> str:
    return _t("invite_line", lang, link=_invite_link(cur, tg_id, name))


def _cmd_info(cur, tg_id: int, chat_id: int, lang: str, name: str | None = None) -> None:
    body = _t("info_body", lang,
              tagline=_t("tagline", lang),
              mins=_COMMENT_WINDOW_MINUTES,
              rdays=_RADAR_REPEAT_DAYS,
              undo=_UNDO_WINDOW_SECONDS,
              miles="/".join(str(m) for m in _MILESTONES))
    # Inline button, not the reply keyboard — the persistent one stays put anyway.
    _send(chat_id, f"{body}\n\n{_invite_line(cur, tg_id, lang, name)}",
          reply_markup={"inline_keyboard": [[
              {"text": _t("btn_language", lang), "callback_data": "mv:langmenu"}
          ]]})


def _cmd_move(cur, tg_id: int, chat_id: int, lang: str) -> None:
    """The invite link, then the crew as buttons.

    The crew used to be spelled out as a sentence above the link, with a second
    line naming the hidden people. Both are now the buttons themselves — the
    list, and a 🙈 on whoever is hidden — so printing the names as well said
    everything twice.
    """
    me = _user(cur, tg_id)
    # Resend the main keyboard here: it lives in the client until a message
    # carries a new one, so a renamed button stays stale otherwise. /info can't
    # do it (it uses an inline keyboard), and the old label still routes here via
    # _LEGACY_BUTTONS — so tapping the stale button upgrades it.
    _send(chat_id, _invite_line(cur, tg_id, lang, me["participant_name"] if me else None),
          reply_markup=_main_kb(lang))
    # The crew goes in its own message: one message can hold either the main
    # keyboard or an inline one, and the buttons need the inline slot.
    text, kb = _crew_pick_view(cur, tg_id, lang)
    _send(chat_id, text, reply_markup=kb)


# Telegram takes far more, but a wall of buttons stops being a shortcut. Beyond
# this the prompt above still works — typing a name is the path that scales.
_CREW_BUTTON_LIMIT = 20


def _crew_pick_view(cur, tg_id: int, lang: str) -> tuple[str, dict]:
    """The "type a name" prompt, with everyone already in the crew as a button.

    Typing still works and is still the only way to reach someone new; the
    buttons just remove the need to retype a name the bot already knows —
    including ones with characters that are awkward to enter.
    """
    names = [n for n in _crew_names(cur, tg_id) if n != "__all__"]
    if not names:
        # An empty keyboard, not no keyboard: editMessageText without reply_markup
        # leaves the old buttons in place, which would strand names that are gone.
        return _t("crew_prompt_empty", lang), {"inline_keyboard": []}
    cur.execute(
        "SELECT LOWER(muted_name) AS n, muted_until FROM move_mute "
        "WHERE telegram_user_id = %s AND muted_until > NOW()",
        (tg_id,),
    )
    hidden = {r["n"]: r["muted_until"] for r in cur.fetchall()}
    cur.execute("SELECT telegram_user_id, participant_name FROM move_users "
                "WHERE participant_name = ANY(%s)", (names,))
    rows = sorted(cur.fetchall(), key=lambda r: (r["participant_name"] or "").casefold())
    kb = [[{"text": ("🙈 " if (r["participant_name"] or "").lower() in hidden else "")
                    + r["participant_name"],
            "callback_data": f"mv:crew:open:{r['telegram_user_id']}"}]
          for r in rows[:_CREW_BUTTON_LIMIT]]
    # Spell out the hidden ones with their dates. A 🙈 on the button says someone
    # is hidden but not until when, and "until when" is the thing you come back
    # to check — hiding is temporary by design.
    lines = [_t("crew_prompt", lang)]
    lines += [_t("crew_hidden_line", lang, name=r["participant_name"],
                 until=_short_date(hidden[(r["participant_name"] or "").lower()]))
              for r in rows if (r["participant_name"] or "").lower() in hidden]
    return "\n".join(lines), {"inline_keyboard": kb}


def _handle_crew_name(cur, conn, tg_id: int, chat_id: int, lang: str, name: str) -> None:
    """A name typed after /move: invite them, or offer hide/remove if already there."""
    target = _by_name(cur, name)
    if not target or target["telegram_user_id"] == tg_id:
        # Leave await_crew armed so "try again" means it — but don't re-set it,
        # which would restart the 10-minute clock. Refreshing it on every miss
        # made the state immortal: keep typing and every plain message, for the
        # rest of time, is read as a crew name. Now the window closes on time.
        # Worth its own line, not just a trace: every one of these is someone who
        # wanted to add a person and couldn't. It's how you find out people are
        # typing @usernames, or that a name is spelled differently than they think.
        me = _user(cur, tg_id)
        _log(f"🔍 Move: name not found\n• {me['participant_name'] if me else tg_id}"
             f" searched: {name[:64]}")
        _send(chat_id, _t("crew_not_found", lang, name=name))
        return
    tname = target["participant_name"]
    cur.execute(
        "SELECT 1 FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
        (tg_id, tname),
    )
    if cur.fetchone():
        # Also left armed: the menu is informational and the prompt still invites
        # another name, so typing one has to keep working — within the window.
        text, kb = _crew_member_view(cur, tg_id, target, lang)
        _send(chat_id, text, reply_markup=kb)
        return
    # Not added — asked. Nothing enters either crew until the other side accepts,
    # and the accept wires up both directions at once.
    me = _user(cur, tg_id)
    myname = me["participant_name"] if me else str(tg_id)
    _send(target["chat_id"] or target["telegram_user_id"],
          _t("crew_request", _norm_lang(target["language_code"]), name=myname),
          reply_markup={"inline_keyboard": [[
              {"text": _t("btn_accept", _norm_lang(target["language_code"])),
               "callback_data": f"mv:crew:accept:{tg_id}"},
              {"text": _t("btn_decline", _norm_lang(target["language_code"])),
               "callback_data": "mv:crew:decline"},
          ]]})
    # The ask went out — that's the end of this prompt, so stop reading text as names.
    _clear_state(cur, tg_id)
    _send(chat_id, _t("crew_request_sent", lang, name=tname))
    _log(f"🤝 Move: crew request\n• {myname} → {tname}")


def _crew_target(cur, token: str):
    """Resolve a crew callback's subject — a telegram id, or a name.

    New buttons carry ids: callback_data is capped at 64 BYTES, Cyrillic costs
    two per character, and _valid_name allows 32 characters — so "mv:crew:
    mute1w:" plus a long Ukrainian name overruns the cap and Telegram rejects
    the button. Names are still accepted so buttons sent before this change
    keep working in people's chats.
    """
    if token.isdigit():
        return _user(cur, int(token))
    return _by_name(cur, token)


def _crew_member_view(cur, tg_id: int, target, lang: str) -> tuple[str, dict]:
    """What you can do with someone already in your crew, rendered from state.

    Carries a hidden-until date, so it has to be redrawn after every action —
    same reason the radar and pause menus are views rather than one-shot sends.
    """
    tname, tid = target["participant_name"], target["telegram_user_id"]
    cur.execute(
        "SELECT muted_until FROM move_mute WHERE telegram_user_id = %s "
        "AND LOWER(muted_name) = LOWER(%s) AND muted_until > NOW()",
        (tg_id, tname),
    )
    m = cur.fetchone()
    status = _t("crew_muted_until", lang, until=_short_date(m["muted_until"])) if m else ""
    rows = []
    if m:
        rows.append([{"text": _t("btn_unmute", lang), "callback_data": f"mv:crew:unmute:{tid}"}])
    rows.append([
        {"text": _t("btn_mute_1d", lang), "callback_data": f"mv:crew:mute1d:{tid}"},
        {"text": _t("btn_mute_1w", lang), "callback_data": f"mv:crew:mute1w:{tid}"},
    ])
    rows.append([{"text": _t("btn_remove", lang), "callback_data": f"mv:crew:remove:{tid}"}])
    # Back, not cancel. This menu asks nothing, so doing nothing was always a way
    # out — but opening it from the crew list replaces that list in place, and
    # this puts it back. (An earlier cancel button also cleared await_crew, which
    # quietly stopped you typing another name; this one leaves the state alone.)
    rows.append([{"text": _t("btn_back", lang), "callback_data": "mv:crew:list"}])
    return _t("crew_in_list", lang, name=tname, status=status), {"inline_keyboard": rows}


def _crew_remove_confirm_view(target, lang: str) -> tuple[str, dict]:
    tname, tid = target["participant_name"], target["telegram_user_id"]
    return _t("crew_remove_confirm", lang, name=tname), {"inline_keyboard": [
        [{"text": _t("btn_remove_yes", lang), "callback_data": f"mv:crew:removeok:{tid}"}],
        [{"text": _t("kb_cancel", lang), "callback_data": f"mv:crew:back:{tid}"}],
    ]}


def _disconnect(cur, conn, tg_id: int, other_id: int, my_name: str, other_name: str) -> None:
    """Undo a crew link in both directions.

    The link is created by mutual consent, so it shouldn't be able to survive
    half-alive: leaving their row behind means they keep sending to someone who
    removed them, which nobody can see and nobody can explain. Mutes on either
    side go too — they only describe a link that no longer exists.
    """
    for owner, name in ((tg_id, other_name), (other_id, my_name)):
        cur.execute(
            "DELETE FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
            (owner, name),
        )
        cur.execute(
            "DELETE FROM move_mute WHERE telegram_user_id = %s AND LOWER(muted_name) = LOWER(%s)",
            (owner, name),
        )
    conn.commit()


def _connect(cur, conn, a_id: int, b_id: int) -> str:
    """Put two people in each other's crew. Returns 'linked', 'already' or 'bad'."""
    a, b = _user(cur, a_id), _user(cur, b_id)
    if not a or not b or not a["participant_name"] or not b["participant_name"]:
        return "bad"
    cur.execute(
        "SELECT 1 FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
        (a_id, b["participant_name"]),
    )
    already = cur.fetchone() is not None
    for me, other in ((a_id, b["participant_name"]), (b_id, a["participant_name"])):
        cur.execute(
            "INSERT INTO move_crew (telegram_user_id, crew_name) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (me, other),
        )
    conn.commit()
    return "already" if already else "linked"


def _invite_kb(lang: str) -> dict:
    return {"inline_keyboard": [[
        {"text": _t("btn_new_link", lang), "callback_data": "mv:invite:rotate"}
    ]]}


def _cmd_invite(cur, tg_id: int, chat_id: int, lang: str) -> None:
    me = _user(cur, tg_id)
    link = _invite_link(cur, tg_id, me["participant_name"] if me else None)
    _send(chat_id, _t("invite_text", lang, link=link), reply_markup=_invite_kb(lang))


def _apply_invite(cur, conn, tg_id: int, chat_id: int, lang: str, inviter_id: int) -> None:
    """A deep-link invite was opened: ask the link's owner to approve.

    This used to connect the two outright. But a link is a bearer token — it
    gets forwarded, pasted into groups, screenshotted — and whoever holds it
    was landing in the owner's crew with no say from the owner, receiving their
    daily videos from then on. Nobody joins without a tap now.

    The approval belongs to the link's owner: they are the one exposed, and the
    person who opened the link already consented by opening it. So this is the
    same request the name flow sends, with the roles as they actually are —
    the opener is the requester, the owner decides.
    """
    if inviter_id == tg_id:
        _send(chat_id, _t("invite_self", lang))
        return
    inviter = _user(cur, inviter_id)
    if not inviter or not inviter["participant_name"]:
        return                                    # stale or unregistered inviter — ignore
    me = _user(cur, tg_id)
    if not me or not me["participant_name"]:
        return                                    # opener hasn't finished registering
    # Already crew? Say so instead of pestering the owner with a dead request.
    cur.execute(
        "SELECT 1 FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
        (tg_id, inviter["participant_name"]),
    )
    if cur.fetchone():
        _send(chat_id, _t("invite_already", lang, name=inviter["participant_name"]))
        return
    ilang = _norm_lang(inviter["language_code"])
    _send(inviter["chat_id"] or inviter_id,
          _t("crew_request_link", ilang, name=me["participant_name"]),
          reply_markup={"inline_keyboard": [[
              {"text": _t("btn_accept", ilang), "callback_data": f"mv:crew:accept:{tg_id}"},
              {"text": _t("btn_decline", ilang), "callback_data": "mv:crew:decline"},
          ]]})
    _send(chat_id, _t("crew_request_sent", lang, name=inviter["participant_name"]))
    _log(f"🔗 Move: invite link opened\n• {me['participant_name']} → {inviter['participant_name']}")


def _month_stats(cur, tg_id: int, start: date, end: date) -> dict | None:
    """Days moved / consistency / longest streak / ⚡ for one month."""
    import calendar
    cur.execute(
        "SELECT entry_date FROM move_entries WHERE telegram_user_id = %s "
        "AND entry_date >= %s AND entry_date <= %s ORDER BY entry_date",
        (tg_id, start, end),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    days = [r["entry_date"] if hasattr(r["entry_date"], "toordinal")
            else date.fromisoformat(str(r["entry_date"])[:10]) for r in rows]
    longest = run = 1
    for i in range(1, len(days)):
        run = run + 1 if (days[i] - days[i - 1]).days == 1 else 1
        longest = max(longest, run)
    cur.execute(
        "SELECT COUNT(*) AS n FROM move_reactions r JOIN move_entries e ON e.id = r.entry_id "
        "WHERE e.telegram_user_id = %s AND e.entry_date >= %s AND e.entry_date <= %s",
        (tg_id, start, end),
    )
    total_days = calendar.monthrange(start.year, start.month)[1]
    return {
        "count": len(days),
        "total": total_days,
        "pct": round(len(days) / total_days * 100),
        "longest": longest,
        "zaps": cur.fetchone()["n"] or 0,
    }


def _cmd_summary(cur, tg_id: int, chat_id: int, lang: str) -> None:
    """Every month on record, newest first — computed from entries, so it works
    retroactively rather than only for months a report was sent for."""
    cur.execute(
        "SELECT MIN(entry_date) AS first, MAX(entry_date) AS last FROM move_entries "
        "WHERE telegram_user_id = %s",
        (tg_id,),
    )
    span = cur.fetchone()
    if not span or not span["first"]:
        _send(chat_id, _t("summary_none", lang))
        return

    def as_date(v):
        return v if hasattr(v, "toordinal") else date.fromisoformat(str(v)[:10])

    first, last = as_date(span["first"]), as_date(span["last"])
    months = []
    cursor_m = date(last.year, last.month, 1)
    floor_m = date(first.year, first.month, 1)
    while cursor_m >= floor_m and len(months) < 24:
        nxt = date(cursor_m.year + (cursor_m.month == 12), (cursor_m.month % 12) + 1, 1)
        months.append((cursor_m, nxt - timedelta(days=1)))
        cursor_m = date(cursor_m.year - (cursor_m.month == 1),
                        12 if cursor_m.month == 1 else cursor_m.month - 1, 1)

    lines = [_t("summary_all_header", lang), ""]
    for m_start, m_end in months:
        st = _month_stats(cur, tg_id, m_start, m_end)
        if not st:
            continue
        month = _MONTHS.get(lang, _MONTHS["en"])[m_start.month]
        lines.append(f"📅 {month} {m_start.year}")
        lines.append(_t("summary_days", lang, count=st["count"], total=st["total"], pct=st["pct"]))
        lines.append(_t("summary_streak", lang, days=st["longest"]))
        if st["zaps"]:
            lines.append(_t("summary_zaps", lang, n=st["zaps"]))
        lines.append("")
    _send(chat_id, "\n".join(lines).strip())


_RADAR_FREQS = ("daily", "weekly", "monthly", "never")


def _radar_label(freq: str, lang: str) -> str:
    return _t("radar_off" if freq == "never" else f"radar_{freq}", lang)


def _radar_pool_size(cur) -> int:
    """How many people are willing to be shown to strangers."""
    cur.execute("SELECT COUNT(*) AS n FROM move_users WHERE radar_send = TRUE")
    return cur.fetchone()["n"] or 0


def _radar_candidates(cur, rid: int) -> list:
    """Every move this viewer is allowed to see right now, best-effort ordered.

    More than one, because delivery can still fail on the author having deleted
    their original — the caller walks the list until a copy lands.

    Excludes their own crew, anyone they've blocked, and anyone they were shown
    within _RADAR_REPEAT_DAYS. Random order, so two people asking on the same day
    don't get the same stranger.
    """
    crew = {n.lower() for n in _crew_names(cur, rid)}
    cur.execute(
        "SELECT e.id, e.chat_id, e.message_id, e.text_body, "
        "       u2.telegram_user_id AS from_id, u2.participant_name "
        "FROM move_entries e JOIN move_users u2 ON u2.telegram_user_id = e.telegram_user_id "
        "WHERE e.entry_date >= %s AND u2.radar_send = TRUE AND u2.banned_at IS NULL "
        "  AND u2.telegram_user_id <> %s "
        "  AND NOT EXISTS (SELECT 1 FROM move_radar_block b "
        "                  WHERE b.telegram_user_id = %s AND b.blocked_tg_id = u2.telegram_user_id) "
        "  AND NOT EXISTS (SELECT 1 FROM move_radar_history h "
        "                  WHERE h.telegram_user_id = %s AND h.from_tg_id = u2.telegram_user_id "
        "                    AND h.sent_at > NOW() - make_interval(days => %s)) "
        "ORDER BY random() LIMIT 25",
        (date.today() - timedelta(days=_RADAR_FRESH_DAYS), rid, rid, rid, _RADAR_REPEAT_DAYS),
    )
    return [c for c in cur.fetchall() if (c["participant_name"] or "").lower() not in crew]


def _radar_show(cur, conn, rid: int, chat_id: int, lang: str,
                touch_schedule: bool = True):
    """Deliver the first candidate that actually sends. Returns it, or None."""
    for cand in _radar_candidates(cur, rid):
        if _radar_deliver(cur, conn, rid, chat_id, lang, cand, touch_schedule):
            return cand
    return None


def _radar_deliver(cur, conn, rid: int, chat_id: int, lang: str, cand,
                   touch_schedule: bool = True) -> bool:
    """Copy one stranger's move into this viewer's chat. False if it couldn't be sent.

    touch_schedule=False for a pull: asking to see someone now shouldn't push
    back the daily drop they already subscribed to.
    """
    kb = _zap_kb(cand["id"], lang=lang, radar=True)
    if cand["message_id"]:
        # The author may have deleted the original — copyMessage then fails, so
        # the caller should move on rather than send a bare "someone moved".
        res = _copy(cand["chat_id"], cand["message_id"], chat_id, reply_markup=kb)
        if not res:
            return False
    else:
        res = _send(chat_id, cand["text_body"] or "", reply_markup=kb)
    # Track it so a later undo revokes the radar copy too. kind='radar' keeps the
    # block button alive when the ⚡ is ticked.
    if res and res.get("message_id"):
        cur.execute(
            "INSERT INTO move_forwards (entry_id, recipient_tg_id, chat_id, message_id, kind) "
            "VALUES (%s, %s, %s, %s, 'radar')",
            (cand["id"], rid, chat_id, res["message_id"]),
        )
    _send(chat_id, _t("radar_received", lang))
    cur.execute("INSERT INTO move_radar_history (telegram_user_id, from_tg_id) VALUES (%s, %s)",
                (rid, cand["from_id"]))
    if touch_schedule:
        cur.execute("UPDATE move_users SET radar_last_received = NOW() WHERE telegram_user_id = %s",
                    (rid,))
    conn.commit()
    return True


def _radar_freq_view(cur, tg_id: int, lang: str) -> tuple[str, dict]:
    """The frequency question, rendered from current state."""
    u = _user(cur, tg_id)
    cur_freq = (u["radar_freq"] if u else "never") or "never"
    rows = [[{"text": ("✓ " if f == cur_freq else "") + _radar_label(f, lang),
              "callback_data": f"mv:radar:{f}"}] for f in _RADAR_FREQS]
    # A pull with nobody to pull from is a dead button, so it stays hidden until
    # the pool is deep enough that "show me someone" usually finds someone.
    if _radar_pool_size(cur) >= _RADAR_PULL_MIN_POOL:
        rows.append([{"text": _t("radar_pull_btn", lang), "callback_data": "mv:radarnow"}])
    return (_t("radar_menu", lang, current=_radar_label(cur_freq, lang)),
            {"inline_keyboard": rows})


def _radar_share_view(cur, tg_id: int, lang: str) -> tuple[str, dict]:
    """The sharing question, rendered from current state."""
    u = _user(cur, tg_id)
    on = bool(u and u["radar_send"])
    return (_t("radar_share_menu", lang,
               current=_t("radar_state_on" if on else "radar_state_off", lang)),
            {"inline_keyboard": [[
                {"text": ("✓ " if on else "") + _t("btn_share_yes", lang),
                 "callback_data": "mv:radarsend:on"},
                {"text": ("✓ " if not on else "") + _t("btn_share_no", lang),
                 "callback_data": "mv:radarsend:off"},
            ]]})


def _cmd_radar(cur, tg_id: int, chat_id: int, lang: str) -> None:
    """Two questions, asked separately: how often you receive, and whether you share."""
    for text, kb in (_radar_freq_view(cur, tg_id, lang),
                     _radar_share_view(cur, tg_id, lang)):
        _send(chat_id, text, reply_markup=kb)


def _pause_view(cur, tg_id: int, lang: str) -> tuple[str, dict]:
    """The pause menu, rendered from current state — same contract as the radar views."""
    u = _user(cur, tg_id)
    now = datetime.now(timezone.utc)
    paused = bool(u and u["paused_until"] and u["paused_until"] > now)
    rows = [
        [{"text": _t("pause_1d", lang), "callback_data": "mv:pause:1d"}],
        [{"text": _t("pause_1w", lang), "callback_data": "mv:pause:1w"}],
        [{"text": _t("pause_1m", lang), "callback_data": "mv:pause:1m"}],
    ]
    if paused:
        rows.append([{"text": _t("pause_resume", lang), "callback_data": "mv:pause:resume"}])
        text = _t("pause_active", lang, until=_short_date(u["paused_until"]))
    else:
        text = _t("pause_menu", lang)
    return text, {"inline_keyboard": rows}


def _cmd_pause(cur, tg_id: int, chat_id: int, lang: str) -> None:
    text, kb = _pause_view(cur, tg_id, lang)
    _send(chat_id, text, reply_markup=kb)


def _cmd_mod(cur, conn, tg_id: int, chat_id: int, lang: str, args: str) -> None:
    """`/mod status|restore|ban <name>` — the typed equivalent of the log buttons.

    English only and unlocalized: it's for whoever runs the bot, not for users.
    """
    if tg_id not in _admin_ids():
        # Answer exactly as any other unknown word would — no hint that /mod exists.
        _send(chat_id, _t("unknown_msg", lang), reply_markup=_main_kb(lang))
        return
    action, _, name = args.strip().partition(" ")
    name = name.strip()
    if action not in ("status", "restore", "ban") or not name:
        _send(chat_id, "Usage:\n/mod status <name>\n/mod restore <name>\n/mod ban <name>")
        return
    who = _by_name(cur, name)
    if not who:
        _send(chat_id, f"No one named \"{name}\".")
        return
    target_id = who["telegram_user_id"]
    if action == "status":
        cur.execute("SELECT COUNT(*) AS n FROM move_reports r JOIN move_entries e "
                    "ON e.id = r.entry_id WHERE e.telegram_user_id = %s", (target_id,))
        reports = cur.fetchone()["n"] or 0
        _send(chat_id,
              f"{who['participant_name']} (id {target_id})\n"
              f"• active warnings: {_active_warnings(cur, target_id)}"
              f"/{_WARNINGS_PER_SUSPENSION}\n"
              f"• reports received: {reports}\n"
              f"• suspended: {'yes' if _is_suspended(cur, target_id) else 'no'}\n"
              f"• banned: {'yes' if _banned(who) else 'no'}\n"
              f"• sharing to radar: {'yes' if who['radar_send'] else 'no'}",
              reply_markup=_mod_kb(target_id))
        return
    # restore / ban reuse the button paths, so there's one implementation of each.
    _handle_callback(cur, conn, {
        "id": "0", "from": {"id": tg_id},
        "message": {"chat": {"id": chat_id}, "message_id": 0},
        "data": f"mv:mod:{action}:{target_id}",
    })


# ── webhook ──────────────────────────────────────────────────────────────────

def handle_move_webhook(body: dict, conn) -> None:
    cur = conn.cursor()
    # Before dispatch, so an update that goes on to crash is still recorded —
    # a silent failure at least leaves a trace of what triggered it.
    _trace(cur, body)

    cq = body.get("callback_query")
    if cq:
        _handle_callback(cur, conn, cq)
        return

    msg = body.get("message")
    if not msg:
        return
    tg_id = msg["from"]["id"]
    chat_id = msg["chat"]["id"]
    lang = _norm_lang(msg["from"].get("language_code"))
    u = _user(cur, tg_id)
    if u and u["language_code"]:
        lang = _norm_lang(u["language_code"])

    # 1) media = the move of the day
    media = None
    for key in _MEDIA_KEYS:
        if key in msg:
            media = (chat_id, msg["message_id"], key)
            break
    if media:
        if not (u and u["participant_name"]):
            _send(chat_id, _t("register_first", lang))
            return
        # Sending a move ends any half-finished prompt. Otherwise an armed
        # "await_crew" outranks the comment window below, and the text you type
        # under your own video comes back as "nobody is called that".
        _clear_state(cur, tg_id)
        _log_move(cur, conn, tg_id, chat_id, media, msg.get("caption"))
        conn.commit()
        return

    text = (msg.get("text") or "").strip()
    if not text:
        return
    text = _BUTTON_TO_CMD.get(text, text)   # localized keyboard buttons route as commands

    # 2) conversation state (name entry)
    state = _get_state(cur, tg_id)
    # "await_name" may carry a pending inviter as "await_name:<id>".
    base_state = (state or "").split(":")[0]
    if base_state in ("await_name", "await_rename") and not text.startswith("/"):
        if not _valid_name(text):
            _send(chat_id, _t("letters_only", lang))
            return
        if _by_name(cur, text):
            _send(chat_id, _t("name_taken", lang, name=text))
            return
        cur.execute(
            "UPDATE move_users SET participant_name = %s, language_code = %s WHERE telegram_user_id = %s",
            (text.strip(), lang, tg_id),
        )
        _clear_state(cur, tg_id)
        conn.commit()
        key = "welcome" if base_state == "await_name" else "renamed"
        _send(chat_id, _t(key, lang, name=text.strip()), reply_markup=_main_kb(lang))
        _log(("👋 Move: registered\n• " if base_state == "await_name" else "✏️ Move: renamed\n• ")
             + text.strip())
        # A deep-link invite waited for the name; connect them now.
        if base_state == "await_name" and ":" in (state or ""):
            try:
                _apply_invite(cur, conn, tg_id, chat_id, lang, int(state.split(":", 1)[1]))
            except ValueError:
                pass
        return

    # 2b) a question or suggestion typed after /feedback
    if base_state == "await_feedback":
        _clear_state(cur, tg_id)
        conn.commit()
        if not text.startswith("/"):
            # No storage: this is a message to a human, not app data. The log chat
            # is where the maintainers already watch, and the name + id let them
            # reply by hand.
            _log("💬 Move: feedback\n• {} ({})\n\n{}".format(
                (u or {}).get("participant_name") or "?", tg_id, text))
            _send(chat_id, _t("feedback_sent", lang), reply_markup=_main_kb(lang))
            return
        # A command instead of an answer means they changed their mind — the state
        # is already cleared, so let it fall through and run.

    # 3) commands
    head = text.split()[0]
    word = head.lstrip("/").lower()
    args = text[len(head):].strip()

    if word == "start":
        _cmd_start(cur, conn, tg_id, chat_id, lang, payload=args)
        conn.commit()
        return
    if not (u and u["participant_name"]):
        _send(chat_id, _t("register_first", lang))
        return
    if word in ("info", "help"):
        _cmd_info(cur, tg_id, chat_id, lang, u["participant_name"])
        return
    if word == "rename":
        _set_state(cur, tg_id, "await_rename")
        conn.commit()
        _send(chat_id, _t("ask_rename", lang))
        return
    if word == "move":
        _cmd_move(cur, tg_id, chat_id, lang)
        _set_state(cur, tg_id, "await_crew")
        conn.commit()
        return
    if word in ("feedback", "support"):
        # Inline form supported too: "/feedback the radar is confusing" skips the ask.
        if args:
            _log("💬 Move: feedback\n• {} ({})\n\n{}".format(u["participant_name"], tg_id, args))
            _send(chat_id, _t("feedback_sent", lang), reply_markup=_main_kb(lang))
            return
        _set_state(cur, tg_id, "await_feedback")
        conn.commit()
        _send(chat_id, _t("ask_feedback", lang))
        return
    if word == "radar":
        _cmd_radar(cur, tg_id, chat_id, lang)
        return
    if word == "pause":
        _cmd_pause(cur, tg_id, chat_id, lang)
        return
    if word == "summary":
        _cmd_summary(cur, tg_id, chat_id, lang)
        return
    if word == "invite":
        _cmd_invite(cur, tg_id, chat_id, lang)
        return
    if word == "mod":
        _cmd_mod(cur, conn, tg_id, chat_id, lang, args)
        return
    if word in ("language", "lang"):
        _send(chat_id, _LANG_PROMPT, reply_markup=_kb_lang())
        return
    if word in ("undo", "delete"):
        _revoke(cur, conn, tg_id, chat_id, lang)
        return
    if word == "log":
        if not args:
            _send(chat_id, _t("log_usage", lang))
            return
        _log_move(cur, conn, tg_id, chat_id, None, args)
        conn.commit()
        return

    # 4) a name typed after /move.
    # The state is deliberately left in place for the handler to decide: it clears
    # it once the invite is actually sent, and otherwise leaves it armed with its
    # original timestamp so the 10-minute window still expires on schedule.
    if state == "await_crew":
        _handle_crew_name(cur, conn, tg_id, chat_id, lang, text)
        conn.commit()
        return

    # 5) a plain text soon after a move is its comment
    if _attach_comment(cur, conn, tg_id, chat_id, text):
        return

    cur.execute(
        "SELECT 1 FROM move_entries WHERE telegram_user_id = %s AND entry_date = %s",
        (tg_id, date.today()),
    )
    _send(chat_id, _t("unknown_msg_done" if cur.fetchone() else "unknown_msg", lang),
          reply_markup=_main_kb(lang))
    conn.commit()


def _handle_callback(cur, conn, cq: dict) -> None:
    tg_id = cq["from"]["id"]
    chat_id = cq["message"]["chat"]["id"]
    msg_id = cq["message"]["message_id"]
    data = cq.get("data") or ""
    if not data.startswith("mv:"):
        return
    lang = _lang(cur, tg_id)
    body = data[3:]

    if body == "invite:rotate":
        _rotate_invite_code(cur, tg_id)
        conn.commit()
        _answer(cq["id"])
        # New message rather than an edit: the old link stays visible above it,
        # which is what makes "the old one no longer works" legible.
        _send(chat_id, _t("invite_rotated", lang, link=_invite_link(cur, tg_id)),
              reply_markup=_invite_kb(lang))
        _log("🔄 Move: invite link rotated\n• " + str((_user(cur, tg_id) or {}).get(
            "participant_name") or tg_id))
        return

    if body.startswith("zap:"):
        entry_id = int(body[4:])
        cur.execute("SELECT telegram_user_id FROM move_entries WHERE id = %s", (entry_id,))
        owner = cur.fetchone()
        if owner and owner["telegram_user_id"] == tg_id:
            _answer(cq["id"], _t("zap_own", lang))
            return
        cur.execute(
            "INSERT INTO move_reactions (entry_id, reactor_tg_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING RETURNING entry_id",
            (entry_id, tg_id),
        )
        fresh = cur.fetchone() is not None
        conn.commit()
        _answer(cq["id"], _t("zap_sent" if fresh else "zap_already", lang))

        # Tick the message that was actually pressed. We already know which one
        # it is, so this needs no lookup and works even when move_forwards has no
        # row for it. Done on every press, not just the first: if an earlier
        # attempt failed to redraw, a second tap should still fix the button.
        # Two keyboard rows means a radar copy, whose block/report row must survive.
        existing = (cq["message"].get("reply_markup") or {}).get("inline_keyboard") or []
        _api_call("editMessageReplyMarkup", {
            "chat_id": chat_id, "message_id": msg_id,
            "reply_markup": _zap_kb(entry_id, sent=True, lang=lang, radar=len(existing) > 1),
        })
        if fresh:
            me = _user(cur, tg_id)
            cur.execute(
                "SELECT u.participant_name FROM move_entries e "
                "JOIN move_users u ON u.telegram_user_id = e.telegram_user_id WHERE e.id = %s",
                (entry_id,),
            )
            to = cur.fetchone()
            _log(f"⚡ Move: lightning\n• {me['participant_name'] if me else tg_id}"
                 f" → {to['participant_name'] if to else '?'}")
        return

    if body.startswith("undo"):
        # Strip the button either way — once it's been pressed it's spent, and a
        # lingering Undo that no longer works is worse than none.
        _api_call("editMessageReplyMarkup",
                  {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        eid = None
        if ":" in body:
            try:
                eid = int(body.split(":", 1)[1])
            except ValueError:
                eid = None
        _revoke(cur, conn, tg_id, chat_id, lang, entry_id=eid)
        return

    if body == "langmenu":
        _send(chat_id, _LANG_PROMPT, reply_markup=_kb_lang())
        return

    if body.startswith("lang:"):
        code = body[len("lang:"):]
        if code not in _SUPPORTED_LANGS:
            return
        u = _user(cur, tg_id)
        if u and u["participant_name"]:
            # Already registered — just switch. Resend the main keyboard so its
            # localized button labels update too.
            cur.execute("UPDATE move_users SET language_code = %s WHERE telegram_user_id = %s",
                        (code, tg_id))
            conn.commit()
            _api_call("editMessageReplyMarkup",
                      {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            _send(chat_id, _t("lang_changed", code), reply_markup=_main_kb(code))
            _log(f"🌍 Move: language → {code}\n• {u['participant_name']}")
            return
        # Registration flow — keep any pending inviter from the /start payload.
        state = _get_state(cur, tg_id) or ""
        pending = state.split(":", 1)[1] if ":" in state else None
        cur.execute("UPDATE move_users SET language_code = %s WHERE telegram_user_id = %s",
                    (code, tg_id))
        _set_state(cur, tg_id, f"await_name:{pending}" if pending else "await_name")
        conn.commit()
        _api_call("editMessageReplyMarkup",
                  {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        # Ukrainian inflects the verb, so we need to know; EN/DE don't.
        if code == "uk":
            _set_state(cur, tg_id, f"await_gender:{pending}" if pending else "await_gender")
            conn.commit()
            _send(chat_id, _t("ask_gender", code), reply_markup={"inline_keyboard": [[
                {"text": _t("gender_m", code), "callback_data": "mv:gender:m"},
                {"text": _t("gender_f", code), "callback_data": "mv:gender:f"},
            ]]})
            return
        _send(chat_id, _t("start_body", code, tagline=_t("tagline", code)))
        return

    if body.startswith("gender:"):
        g = body[len("gender:"):]
        if g not in ("m", "f"):
            return
        state = _get_state(cur, tg_id) or ""
        pending = state.split(":", 1)[1] if ":" in state else None
        cur.execute("UPDATE move_users SET gender = %s WHERE telegram_user_id = %s", (g, tg_id))
        u = _user(cur, tg_id)
        code = _norm_lang(u["language_code"]) if u else "uk"
        _api_call("editMessageReplyMarkup",
                  {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if u and u["participant_name"]:          # changing it later, not onboarding
            _clear_state(cur, tg_id)
            conn.commit()
            _send(chat_id, _t("lang_changed", code), reply_markup=_main_kb(code))
            return
        _set_state(cur, tg_id, f"await_name:{pending}" if pending else "await_name")
        conn.commit()
        _send(chat_id, _t("start_body", code, tagline=_t("tagline", code)))
        return

    if body.startswith("crew:"):
        sub = body[5:]
        # Only the actions that end the conversation drop their buttons. Mute and
        # unmute keep the menu open and redraw it below, so stripping here first
        # would remove the buttons and immediately put them back.
        if not sub.startswith(("mute1d:", "mute1w:", "unmute:", "remove:", "back:", "open:")) \
                and sub != "list":
            _api_call("editMessageReplyMarkup",
                      {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if sub == "list":
            # Back out of a member's menu into the crew picker it replaced.
            _redraw(chat_id, msg_id, *_crew_pick_view(cur, tg_id, lang))
            _answer(cq["id"])
            return
        if sub in ("cancel", "decline"):
            # A decline stays between the button and the person who pressed it —
            # telling the asker they were turned down only invites a second ask.
            _send(chat_id, _t("cancelled", lang))
            return
        action, _, name = sub.partition(":")
        if action == "accept":
            requester = _crew_target(cur, name)
            me = _user(cur, tg_id)
            if not requester or not me or requester["telegram_user_id"] == tg_id:
                _send(chat_id, _t("crew_request_gone", lang))
                return
            if _connect(cur, conn, tg_id, requester["telegram_user_id"]) == "bad":
                _send(chat_id, _t("crew_request_gone", lang))
                return
            rname = requester["participant_name"]
            _send(chat_id, _t("crew_added_back", lang, name=rname))
            _send(requester["chat_id"] or requester["telegram_user_id"],
                  _t("crew_request_accepted", _norm_lang(requester["language_code"]),
                     name=me["participant_name"]))
            _log(f"🤝 Move: crew ↔\n• {rname} ↔ {me['participant_name']}")
            return
        if action == "addback":
            cur.execute(
                "INSERT INTO move_crew (telegram_user_id, crew_name) VALUES (%s, %s) "
                "ON CONFLICT DO NOTHING",
                (tg_id, name),
            )
            conn.commit()
            _send(chat_id, _t("crew_added_back", lang, name=name))
            me = _user(cur, tg_id)
            _log(f"🤝 Move: crew +\n• {me['participant_name'] if me else tg_id} → {name}")
            return
        # Everything below acts on someone in your crew, addressed by id (or by
        # name, for buttons sent before the switch).
        target = _crew_target(cur, name)
        if not target or not target["participant_name"]:
            _send(chat_id, _t("crew_request_gone", lang))
            return
        tname = target["participant_name"]

        if action == "open":
            _redraw(chat_id, msg_id, *_crew_member_view(cur, tg_id, target, lang))
            _answer(cq["id"])
            return
        if action == "remove":
            # Ask first — this is the one action here that needs the other
            # person's agreement to undo.
            _redraw(chat_id, msg_id, *_crew_remove_confirm_view(target, lang))
            _answer(cq["id"])
            return
        if action == "back":
            _redraw(chat_id, msg_id, *_crew_member_view(cur, tg_id, target, lang))
            _answer(cq["id"])
            return
        if action == "removeok":
            me = _user(cur, tg_id)
            if not me:
                _send(chat_id, _t("crew_request_gone", lang))
                return
            _disconnect(cur, conn, tg_id, target["telegram_user_id"],
                        me["participant_name"], tname)
            _send(chat_id, _t("crew_removed", lang, name=tname))
            _log(f"🗑 Move: crew − (both ways)\n• {me['participant_name']} ✗ {tname}")
            return
        # Hiding leaves the person in your crew, so the menu stays open and is
        # redrawn — its text carries the hidden-until date, which would otherwise
        # still read "не показуємо до 01.09" right after showing them again.
        if action == "unmute":
            cur.execute("DELETE FROM move_mute WHERE telegram_user_id = %s AND LOWER(muted_name) = LOWER(%s)",
                        (tg_id, tname))
            conn.commit()
            _redraw(chat_id, msg_id, *_crew_pick_view(cur, tg_id, lang))
            _answer(cq["id"], _t("crew_unmuted", lang, name=tname))
            return
        if action in ("mute1d", "mute1w"):
            until = datetime.now(timezone.utc) + timedelta(days=1 if action == "mute1d" else 7)
            cur.execute(
                "INSERT INTO move_mute (telegram_user_id, muted_name, muted_until) VALUES (%s, %s, %s) "
                "ON CONFLICT (telegram_user_id, muted_name) DO UPDATE SET muted_until = EXCLUDED.muted_until",
                (tg_id, tname, until),
            )
            conn.commit()
            # Back to the list, not this menu: the action is done, and the list is
            # where you see it took effect — who's hidden, and until when.
            _redraw(chat_id, msg_id, *_crew_pick_view(cur, tg_id, lang))
            _answer(cq["id"], _t("crew_muted", lang, name=tname, until=_short_date(until)))
        return

    if body == "radarnow":
        # Guard again on press: the button may be sitting in a chat from before
        # the pool shrank back under the threshold.
        if _radar_pool_size(cur) < _RADAR_PULL_MIN_POOL:
            _answer(cq["id"], _t("radar_pull_none", lang))
            return
        _answer(cq["id"])
        if not _radar_show(cur, conn, tg_id, chat_id, lang, touch_schedule=False):
            _send(chat_id, _t("radar_pull_none", lang))
            return
        u = _user(cur, tg_id)
        _log(f"📡 Move: radar pull\n• → {u['participant_name'] if u else tg_id}")
        return

    if body.startswith("rblock:"):
        entry_id = int(body[len("rblock:"):])
        cur.execute("SELECT telegram_user_id FROM move_entries WHERE id = %s", (entry_id,))
        owner = cur.fetchone()
        if not owner:
            # Entry undone since — nothing to block, and naming nobody keeps radar anonymous.
            _answer(cq["id"], _t("crew_request_gone", lang))
            return
        cur.execute(
            "INSERT INTO move_radar_block (telegram_user_id, blocked_tg_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (tg_id, owner["telegram_user_id"]),
        )
        conn.commit()
        # Drop both buttons: cheering a move you just muted makes no sense.
        _api_call("editMessageReplyMarkup",
                  {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _answer(cq["id"])
        _send(chat_id, _t("radar_blocked", lang))
        u = _user(cur, tg_id)
        _log(f"🚫 Move: radar block\n• {u['participant_name'] if u else tg_id} ✗ (anon)")
        return

    if body.startswith("rreport:"):
        entry_id = int(body[len("rreport:"):])
        cur.execute(
            "SELECT e.telegram_user_id, e.media_type, e.entry_date, u.participant_name "
            "FROM move_entries e JOIN move_users u ON u.telegram_user_id = e.telegram_user_id "
            "WHERE e.id = %s",
            (entry_id,),
        )
        entry = cur.fetchone()
        if not entry:
            _answer(cq["id"], _t("crew_request_gone", lang))
            return
        cur.execute(
            "INSERT INTO move_reports (entry_id, reporter_tg_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING RETURNING entry_id",
            (entry_id, tg_id),
        )
        fresh = cur.fetchone() is not None
        if not fresh:
            conn.commit()
            _answer(cq["id"], _t("radar_reported_already", lang))
            return
        # Reporting implies blocking: nobody who flags a move wants to be shown
        # that person again while a human gets around to it.
        cur.execute(
            "INSERT INTO move_radar_block (telegram_user_id, blocked_tg_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (tg_id, entry["telegram_user_id"]),
        )
        conn.commit()
        _api_call("editMessageReplyMarkup",
                  {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _answer(cq["id"])
        _send(chat_id, _t("radar_reported", lang))
        me = _user(cur, tg_id)
        # Distinct reporters, not reports: the PK on move_reports already makes
        # one person's second tap a no-op, so a row is a person.
        cur.execute("SELECT COUNT(*) AS n FROM move_reports WHERE entry_id = %s", (entry_id,))
        total = cur.fetchone()["n"] or 0
        # Named on purpose: the log channel is the moderators' view, and they
        # can't act on "someone reported someone". Radar stays anonymous to the
        # viewer — this is the one place identity is spelled out.
        _log(f"⚠️ Move: REPORT\n"
             f"• entry #{entry_id} ({entry['media_type'] or 'text'}, {entry['entry_date']})\n"
             f"• author: {entry['participant_name']} (id {entry['telegram_user_id']})\n"
             f"• reported by: {me['participant_name'] if me else tg_id} (id {tg_id})\n"
             f"• reports on this entry: {total}",
             reply_markup=_mod_kb(entry["telegram_user_id"]))
        if total >= _REPORTS_PER_WARNING:
            author = _user(cur, entry["telegram_user_id"])
            if author:
                _warn(cur, conn, author, entry_id)
        return

    if body.startswith("mod:"):
        # Pressed in the log channel. Whoever is in that channel isn't
        # automatically a moderator, so the presser is checked, not the chat.
        if tg_id not in _admin_ids():
            _answer(cq["id"], "Not for you.")
            return
        action, _, target = body[len("mod:"):].partition(":")
        if not target.isdigit():
            return
        target_id = int(target)
        who = _user(cur, target_id)
        name = who["participant_name"] if who else target_id
        if action == "restore":
            cur.execute(
                "UPDATE move_suspensions SET lifted_at = NOW(), lifted_by = %s "
                "WHERE telegram_user_id = %s AND lifted_at IS NULL",
                (tg_id, target_id),
            )
            cur.execute(
                "UPDATE move_warnings SET cleared_at = NOW(), cleared_by = %s "
                "WHERE telegram_user_id = %s AND cleared_at IS NULL",
                (tg_id, target_id),
            )
            cur.execute(
                "UPDATE move_users SET radar_send = TRUE, banned_at = NULL "
                "WHERE telegram_user_id = %s",
                (target_id,),
            )
            conn.commit()
            if who:
                _send(who["chat_id"] or target_id, _t("restored", _norm_lang(who["language_code"])))
            _answer(cq["id"], "Restored.")
            _log(f"✅ Move: restored\n• {name} (id {target_id})\n• by admin {tg_id}")
            return
        if action == "ban":
            cur.execute(
                "UPDATE move_users SET radar_send = FALSE, banned_at = NOW() "
                "WHERE telegram_user_id = %s",
                (target_id,),
            )
            conn.commit()
            if who:
                _send(who["chat_id"] or target_id, _t("banned", _norm_lang(who["language_code"])))
            _answer(cq["id"], "Banned from radar.")
            _log(f"🚫 Move: banned from radar\n• {name} (id {target_id})\n• by admin {tg_id}")
            return
        return

    if body.startswith("radarsend:"):
        on = body[len("radarsend:"):] == "on"
        u = _user(cur, tg_id)
        # A suspension the user can undo from a menu isn't a suspension.
        if on and (_is_suspended(cur, tg_id) or _banned(u)):
            _answer(cq["id"])
            _send(chat_id, _t("radar_share_locked", lang))
            return
        cur.execute("UPDATE move_users SET radar_send = %s WHERE telegram_user_id = %s", (on, tg_id))
        conn.commit()
        # Redraw the question itself. Stripping the buttons and sending the new
        # state as a separate message left the original reading "Now: sharing ✅"
        # under a later line saying it's off — two answers, one of them wrong.
        _redraw(chat_id, msg_id, *_radar_share_view(cur, tg_id, lang))
        _answer(cq["id"], _t("radar_share_on" if on else "radar_share_off", lang))
        _log(f"📡 Move: radar share\n• {u['participant_name'] if u else tg_id}"
             f" → {'yes' if on else 'no'}")
        return

    if body.startswith("radar:"):
        freq = body[len("radar:"):]
        if freq not in _RADAR_FREQS:
            return
        cur.execute("UPDATE move_users SET radar_freq = %s WHERE telegram_user_id = %s", (freq, tg_id))
        conn.commit()
        _redraw(chat_id, msg_id, *_radar_freq_view(cur, tg_id, lang))
        _answer(cq["id"], _t("radar_set", lang, label=_radar_label(freq, lang)))
        u = _user(cur, tg_id)
        _log(f"📡 Move: radar set\n• {u['participant_name'] if u else tg_id}"
             f" → {_radar_label(freq, 'en')}")
        return

    if body.startswith("pause:"):
        what = body[len("pause:"):]
        u = _user(cur, tg_id)
        who = u["participant_name"] if u else tg_id
        if what == "resume":
            cur.execute("UPDATE move_users SET paused_until = NULL WHERE telegram_user_id = %s", (tg_id,))
            conn.commit()
            # Same as the radar menus: redraw, so the message can't keep saying
            # "paused until Sep 04" after the pause has been lifted.
            _redraw(chat_id, msg_id, *_pause_view(cur, tg_id, lang))
            _answer(cq["id"], _t("pause_resumed", lang))
            _log(f"▶️ Move: resumed\n• {who}")
            return
        days = {"1d": 1, "1w": 7, "1m": 30}.get(what, 1)
        until = datetime.now(timezone.utc) + timedelta(days=days)
        cur.execute("UPDATE move_users SET paused_until = %s WHERE telegram_user_id = %s", (until, tg_id))
        conn.commit()
        _redraw(chat_id, msg_id, *_pause_view(cur, tg_id, lang))
        _answer(cq["id"], _t("pause_set", lang, until=_short_date(until)))
        _log(f"⏸️ Move: paused {what}\n• {who}")
        return


# ── cron jobs ────────────────────────────────────────────────────────────────

def _claim_job(cur, conn, job_name: str, day: date) -> bool:
    """cron_log dedup guard — Vercel may retry the cron endpoint."""
    cur.execute(
        "INSERT INTO cron_log (job_name, run_date) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING RETURNING job_name",
        (job_name, day),
    )
    if not cur.fetchone():
        return False
    conn.commit()
    return True


def send_move_zap_reports(conn) -> None:
    """Morning: tell each mover how many ⚡ yesterday's move collected."""
    cur = conn.cursor()
    today = date.today()
    if not _claim_job(cur, conn, "move_zap_report", today):
        return
    yesterday = today - timedelta(days=1)
    cur.execute(
        "SELECT e.id, e.telegram_user_id, u.chat_id, u.language_code, "
        "       (SELECT COUNT(*) FROM move_reactions r WHERE r.entry_id = e.id) AS zaps "
        "FROM move_entries e JOIN move_users u ON u.telegram_user_id = e.telegram_user_id "
        "WHERE e.entry_date = %s",
        (yesterday,),
    )
    rows = cur.fetchall()
    notified = 0
    for r in rows:
        n = r["zaps"] or 0
        if not n:
            continue                      # no ⚡ — better silence than "you got 0"
        lang = _norm_lang(r["language_code"])
        word = _t(f"zap_word_{_plural_form(n, lang)}", lang)
        _send(r["chat_id"] or r["telegram_user_id"], _t("zap_report", lang, n=n, word=word))
        notified += 1
    conn.commit()
    # Always log, so a missing report can be told apart from a job that never ran.
    _log(f"⚡ Move: zap report ({yesterday})\n• moves: {len(rows)} · notified: {notified}")


def _radar_due(freq: str | None, last) -> bool:
    if not freq or freq == "never":
        return False
    if last is None:
        return True
    now = datetime.now(timezone.utc)
    if freq == "daily":
        return last.date() < now.date()
    if freq == "weekly":
        return (now - last) >= timedelta(weeks=1)
    if freq == "monthly":
        return (now - last) >= timedelta(days=30)
    return False


def process_move_radar(conn) -> None:
    """Show each opted-in user one move from outside their crew. The same
    stranger can't reappear for them within _RADAR_REPEAT_DAYS."""
    cur = conn.cursor()
    today = date.today()
    if not _claim_job(cur, conn, "move_radar", today):
        return

    cur.execute("SELECT * FROM move_users WHERE radar_freq IS NOT NULL AND radar_freq <> 'never'")
    users = cur.fetchall()
    sent_any = 0
    for u in users:
        rid = u["telegram_user_id"]
        now = datetime.now(timezone.utc)
        if u["paused_until"] and u["paused_until"] > now:
            continue
        if not _radar_due(u["radar_freq"], u["radar_last_received"]):
            continue

        lang = _norm_lang(u["language_code"])
        cand = _radar_show(cur, conn, rid, u["chat_id"] or rid, lang)
        if cand:
            _log(f"📡 Move: radar\n• {cand['participant_name']} → {u['participant_name']}")
            sent_any += 1
    conn.commit()
    _log(f"📡 Move: radar pass\n• candidates: {len(users)} · sent: {sent_any}")


def send_move_monthly_summaries(conn) -> None:
    """On the 1st: days moved, consistency, longest streak, ⚡ received."""
    import calendar
    cur = conn.cursor()
    today = date.today()
    if today.day != 1:
        return
    prev_end = today - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    if not _claim_job(cur, conn, f"move_summary_{prev_start.strftime('%Y-%m')}", today):
        return

    days_in_month = calendar.monthrange(prev_start.year, prev_start.month)[1]
    cur.execute("SELECT * FROM move_users WHERE participant_name IS NOT NULL")
    for u in cur.fetchall():
        tg_id = u["telegram_user_id"]
        cur.execute(
            "SELECT entry_date FROM move_entries WHERE telegram_user_id = %s "
            "AND entry_date >= %s AND entry_date <= %s ORDER BY entry_date",
            (tg_id, prev_start, prev_end),
        )
        rows = cur.fetchall()
        if not rows:
            continue
        days = [r["entry_date"] if hasattr(r["entry_date"], "toordinal")
                else date.fromisoformat(str(r["entry_date"])[:10]) for r in rows]
        longest = run = 1
        for i in range(1, len(days)):
            run = run + 1 if (days[i] - days[i - 1]).days == 1 else 1
            longest = max(longest, run)

        cur.execute(
            "SELECT COUNT(*) AS n FROM move_reactions r JOIN move_entries e ON e.id = r.entry_id "
            "WHERE e.telegram_user_id = %s AND e.entry_date >= %s AND e.entry_date <= %s",
            (tg_id, prev_start, prev_end),
        )
        zaps = cur.fetchone()["n"] or 0

        lang = _norm_lang(u["language_code"])
        month = _MONTHS.get(lang, _MONTHS["en"])[prev_start.month]
        lines = [
            _t("summary_header", lang, month=month, name=u["participant_name"]),
            "",
            _t("summary_days", lang, count=len(days), total=days_in_month,
               pct=round(len(days) / days_in_month * 100)),
            _t("summary_streak", lang, days=longest),
        ]
        if zaps:
            lines.append(_t("summary_zaps", lang, n=zaps))
        # The only place /summary is named. It's not on the keyboard and not in
        # the /move menu, and a monthly recap is exactly where "there's more of
        # this" belongs.
        lines += ["", _t("summary_hint", lang)]
        _send(u["chat_id"] or tg_id, "\n".join(lines))
    conn.commit()
