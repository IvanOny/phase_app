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
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

_TOKEN = os.environ.get("MOVE_BOT_TOKEN", "")
_API = f"https://api.telegram.org/bot{_TOKEN}"
# Activity goes to the same log channel as the burpee bot (Бурчик лог).
# MOVE_LOG_CHAT_ID only exists to split them later if that's ever wanted.
_LOG_CHAT_ID = os.environ.get("MOVE_LOG_CHAT_ID", "") or os.environ.get("LOG_CHAT_ID", "")

_STATE_TIMEOUT_MINUTES = 10
_COMMENT_WINDOW_MINUTES = 10          # a text this soon after a move is its comment
_RADAR_REPEAT_DAYS = 7                # same stranger can't reappear within a week
_MILESTONES = (7, 14, 30, 50, 100, 200, 365)
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


def _log(text: str) -> None:
    if not _LOG_CHAT_ID:
        return
    ts = datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
    try:
        _api_call("sendMessage", {"chat_id": int(_LOG_CHAT_ID), "text": f"[{ts}]\n{text}"})
    except Exception:
        pass


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


_STRINGS: dict[str, dict[str, str]] = {
    # ── keyboard ──
    "btn_move":  {"en": "🤝 Move with", "uk": "🤝 Рухатись з", "de": "🤝 Bewegen mit"},
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
        "uk": "👋 Ласкаво просимо до Move!\n\n{tagline}\n\n"
              "Один рух на день — будь-який. Прогулянка, плавання, штанга, розтяжка, танці.\n\n"
              "Як це працює:\n"
              "• Запишіть кругле відео (або фото) і надішліть сюди\n"
              "• Одразу після цього можете додати коментар\n"
              "• Ваше коло бачить це і може надіслати вам ⚡\n\n"
              "Спершу: як вас називати?",
        "de": "👋 Willkommen bei Move!\n\n{tagline}\n\n"
              "Eine Bewegung pro Tag — was auch immer. Gehen, Schwimmen, Heben, Dehnen, Tanzen.\n\n"
              "So funktioniert's:\n"
              "• Nimm ein rundes Video (oder ein Foto) auf und schick es hierher\n"
              "• Direkt danach kannst du einen Kommentar hinzufügen\n"
              "• Deine Crew sieht es und kann dir ein ⚡ schicken\n\n"
              "Zuerst: Wie möchtest du genannt werden?",
    },
    "info_body": {
        "en": "🏃 Move\n{tagline}\n\n"
              "One move a day — whatever it is. Walk, swim, lift, stretch, dance.\n"
              "Nothing is measured or compared. What counts is showing up.\n\n"
              "📹 LOGGING YOUR MOVE\n"
              "• Send a round video bubble, a photo, a video or a GIF — that's your move of the day\n"
              "• It goes to your crew straight away\n"
              "• Want to say something? Send a text within {mins} minutes and it appears "
              "as a reply right under your move\n"
              "• No camera? Use /log <text> instead\n"
              "• One move per day — the first one counts\n\n"
              "⚡ LIGHTNINGS\n"
              "• Tap ⚡ under someone's move to cheer them on — one per move\n"
              "• The counter on the button updates for everyone\n"
              "• Each morning you get a note of how many ⚡ yesterday's move collected\n\n"
              "🤝 YOUR CREW — /move\n"
              "• Type a name to add them; they see every move you log, and you see theirs\n"
              "• Type a name already in your crew to mute (1 day / 1 week) or remove them\n"
              "• /invite gives you a personal link — anyone who taps it is connected to you "
              "automatically, new or already registered\n\n"
              "📡 RADAR — /radar\n"
              "• Get a move from someone outside your crew — daily, weekly, monthly or off\n"
              "• The same stranger won't reach you twice within {rdays} days\n"
              "• Separately, you choose whether your own moves may be shown to strangers\n\n"
              "🔥 STREAKS\n"
              "• Consecutive days are counted and shown when you log\n"
              "• Milestones at {miles} days\n"
              "• On the 1st of each month you get a summary: days moved, consistency, "
              "longest streak and ⚡ received\n"
              "• /summary — every month you've recorded, any time\n\n"
              "⏸️ QUIET — /pause\n"
              "• Mute everything for a day, a week or a month. Resume any time.\n\n"
              "COMMANDS\n"
              "/start — register · /rename — change your name\n"
              "/move — your crew · /invite — invite link\n"
              "/radar — strangers' moves\n"
              "/log <text> — log without media · /summary — your months\n"
              "/pause — mute · /info — this list",
        "uk": "🏃 Move\n{tagline}\n\n"
              "Один рух на день — будь-який. Прогулянка, плавання, штанга, розтяжка, танці.\n"
              "Нічого не вимірюється й не порівнюється. Головне — з'явитися.\n\n"
              "📹 ЯК ЗАПИСАТИ РУХ\n"
              "• Надішліть кругле відео, фото, відео або GIF — це ваш рух дня\n"
              "• Він одразу йде до вашого кола\n"
              "• Хочете щось сказати? Надішліть текст протягом {mins} хвилин — він з'явиться "
              "відповіддю просто під вашим рухом\n"
              "• Немає камери? Скористайтесь /log <текст>\n"
              "• Один рух на день — зараховується перший\n\n"
              "⚡ БЛИСКАВКИ\n"
              "• Натисніть ⚡ під чиїмось рухом, щоб підтримати — одна на рух\n"
              "• Лічильник на кнопці оновлюється для всіх\n"
              "• Щоранку ви дізнаєтесь, скільки ⚡ зібрав учорашній рух\n\n"
              "🤝 ВАШЕ КОЛО — /move\n"
              "• Напишіть ім'я, щоб додати; вони бачитимуть кожен ваш рух, а ви їхні\n"
              "• Напишіть ім'я з кола, щоб приглушити (1 день / 1 тиждень) або прибрати\n"
              "• /invite дає особисте посилання — кожен, хто його відкриє, автоматично "
              "з'єднується з вами, новий чи вже зареєстрований\n\n"
              "📡 РАДАР — /radar\n"
              "• Отримуйте рух від когось поза вашим колом — щодня, щотижня, щомісяця або вимкнено\n"
              "• Той самий незнайомець не потрапить до вас двічі протягом {rdays} днів\n"
              "• Окремо ви обираєте, чи можна показувати ваші рухи незнайомцям\n\n"
              "🔥 СЕРІЇ\n"
              "• Дні поспіль рахуються й показуються при записі\n"
              "• Віхи на {miles} днях\n"
              "• 1-го числа щомісяця — підсумок: днів у русі, регулярність, "
              "найдовша серія та отримані ⚡\n"
              "• /summary — усі ваші місяці, будь-коли\n\n"
              "⏸️ ТИША — /pause\n"
              "• Вимкнути все на день, тиждень чи місяць. Відновити будь-коли.\n\n"
              "КОМАНДИ\n"
              "/start — реєстрація · /rename — змінити ім'я\n"
              "/move — ваше коло · /invite — посилання-запрошення\n"
              "/radar — рухи незнайомців\n"
              "/log <текст> — запис без медіа · /summary — ваші місяці\n"
              "/pause — тиша · /info — цей список",
        "de": "🏃 Move\n{tagline}\n\n"
              "Eine Bewegung pro Tag — was auch immer. Gehen, Schwimmen, Heben, Dehnen, Tanzen.\n"
              "Nichts wird gemessen oder verglichen. Es zählt, dass du auftauchst.\n\n"
              "📹 BEWEGUNG ERFASSEN\n"
              "• Schick ein rundes Video, ein Foto, ein Video oder ein GIF — das ist deine Bewegung des Tages\n"
              "• Sie geht sofort an deine Crew\n"
              "• Willst du etwas sagen? Schick innerhalb von {mins} Minuten einen Text — er erscheint "
              "als Antwort direkt unter deiner Bewegung\n"
              "• Keine Kamera? Nutze /log <Text>\n"
              "• Eine Bewegung pro Tag — die erste zählt\n\n"
              "⚡ BLITZE\n"
              "• Tippe ⚡ unter einer Bewegung, um anzufeuern — einer pro Bewegung\n"
              "• Der Zähler auf dem Button aktualisiert sich für alle\n"
              "• Jeden Morgen erfährst du, wie viele ⚡ die gestrige Bewegung bekommen hat\n\n"
              "🤝 DEINE CREW — /move\n"
              "• Gib einen Namen ein zum Hinzufügen; sie sehen jede deiner Bewegungen und du ihre\n"
              "• Gib einen Namen aus der Crew ein, um stumm zu schalten (1 Tag / 1 Woche) oder zu entfernen\n"
              "• /invite gibt dir einen persönlichen Link — wer ihn antippt, wird automatisch "
              "mit dir verbunden, neu oder schon registriert\n\n"
              "📡 RADAR — /radar\n"
              "• Bekomm eine Bewegung von außerhalb deiner Crew — täglich, wöchentlich, monatlich oder aus\n"
              "• Dieselbe fremde Person erreicht dich nicht zweimal innerhalb von {rdays} Tagen\n"
              "• Separat entscheidest du, ob deine Bewegungen Fremden gezeigt werden dürfen\n\n"
              "🔥 SERIEN\n"
              "• Aufeinanderfolgende Tage werden gezählt und beim Erfassen angezeigt\n"
              "• Meilensteine bei {miles} Tagen\n"
              "• Am 1. jedes Monats: Zusammenfassung mit bewegten Tagen, Konstanz, "
              "längster Serie und erhaltenen ⚡\n"
              "• /summary — alle deine Monate, jederzeit\n\n"
              "⏸️ RUHE — /pause\n"
              "• Alles für einen Tag, eine Woche oder einen Monat stummschalten. Jederzeit fortsetzen.\n\n"
              "BEFEHLE\n"
              "/start — registrieren · /rename — Namen ändern\n"
              "/move — deine Crew · /invite — Einladungslink\n"
              "/radar — fremde Bewegungen\n"
              "/log <Text> — ohne Medien erfassen · /summary — deine Monate\n"
              "/pause — stumm · /info — diese Liste",
    },
    "ask_name": {"en": "What would you like to be called?", "uk": "Як вас називати?", "de": "Wie möchtest du genannt werden?"},
    "welcome": {
        "en": "Welcome, {name}! 👋\n\nNext: add your crew with 🤝 Move with.\nThey'll see every move you log — and you'll see theirs.",
        "uk": "Вітаємо, {name}! 👋\n\nДалі: додайте своє коло через 🤝 Рухатись з.\nВони бачитимуть кожен ваш рух — а ви їхні.",
        "de": "Willkommen, {name}! 👋\n\nAls Nächstes: Füge deine Crew über 🤝 Bewegen mit hinzu.\nSie sehen jede deiner Bewegungen — und du ihre.",
    },
    "already_registered": {"en": "You're already registered as {name}.", "uk": "Ви вже зареєстровані як {name}.", "de": "Du bist bereits als {name} registriert."},
    "renamed": {"en": "Done! You're now {name}.", "uk": "Готово! Тепер ви {name}.", "de": "Fertig! Du bist jetzt {name}."},
    "ask_rename": {"en": "What should your new name be?", "uk": "Яке нове ім'я?", "de": "Wie soll dein neuer Name sein?"},
    "register_first": {"en": "Please register first — send /start", "uk": "Спершу зареєструйтесь — надішліть /start", "de": "Bitte zuerst registrieren — sende /start"},
    "letters_only": {"en": "Letters only please, up to 32 characters.", "uk": "Лише літери, до 32 символів.", "de": "Bitte nur Buchstaben, bis zu 32 Zeichen."},
    "name_taken": {"en": "\"{name}\" is taken. Pick another.", "uk": "Ім'я «{name}» зайняте. Оберіть інше.", "de": "„{name}“ ist vergeben. Wähle einen anderen."},
    "unknown_msg": {"en": "Send a video bubble or a photo to log your move. Tap ℹ️ Info for more.", "uk": "Надішліть кругле відео або фото, щоб записати свій рух. Натисніть ℹ️ Інфо.", "de": "Schick ein rundes Video oder ein Foto, um deine Bewegung zu erfassen. Tippe ℹ️ Info."},
    # ── logging ──
    "logged": {"en": "✓ Move logged{streak}", "uk": "✓ Рух записано{streak}", "de": "✓ Bewegung erfasst{streak}"},
    "logged_shared": {"en": "✓ Move logged{streak} → shared with {names}", "uk": "✓ Рух записано{streak} → надіслано: {names}", "de": "✓ Bewegung erfasst{streak} → geteilt mit {names}"},
    "streak_suffix": {"en": " · 🔥 {days}-day streak", "uk": " · 🔥 серія {days} дн.", "de": " · 🔥 {days}-Tage-Serie"},
    "already_logged": {"en": "You've already moved today ✓ — send a comment if you want to add something.", "uk": "Ви вже рухались сьогодні ✓ — надішліть коментар, якщо хочете щось додати.", "de": "Du hast dich heute schon bewegt ✓ — schick einen Kommentar, wenn du etwas ergänzen willst."},
    "comment_added": {"en": "💬 Comment added.", "uk": "💬 Коментар додано.", "de": "💬 Kommentar hinzugefügt."},
    "log_usage": {"en": "Usage: /log <what you did>", "uk": "Використання: /log <що ви зробили>", "de": "Verwendung: /log <was du gemacht hast>"},
    "crew_move": {"en": "{name} moved today", "uk": "{name} рухався сьогодні", "de": "{name} hat sich heute bewegt"},
    "zap_btn": {"en": "⚡", "uk": "⚡", "de": "⚡"},
    "zap_btn_sent": {"en": "⚡ sent ✓", "uk": "⚡ надіслано ✓", "de": "⚡ gesendet ✓"},
    "zap_sent": {"en": "⚡ sent!", "uk": "⚡ надіслано!", "de": "⚡ gesendet!"},
    "zap_already": {"en": "You already sent a ⚡", "uk": "Ви вже надіслали ⚡", "de": "Du hast schon ein ⚡ gesendet"},
    "zap_own": {"en": "That's your own move 🙂", "uk": "Це ваш власний рух 🙂", "de": "Das ist deine eigene Bewegung 🙂"},
    # ── crew ──
    "crew_menu": {
        "en": "🤝 Your crew sees every move you log — and you see theirs.\n\nMoving with: {crew}\n\nType a name to add, mute or remove:",
        "uk": "🤝 Ваше коло бачить кожен ваш рух — а ви їхні.\n\nРухаєтесь з: {crew}\n\nНапишіть ім'я, щоб додати, приглушити або прибрати:",
        "de": "🤝 Deine Crew sieht jede deiner Bewegungen — und du ihre.\n\nBewegst dich mit: {crew}\n\nGib einen Namen ein zum Hinzufügen, Stummschalten oder Entfernen:",
    },
    "crew_nobody": {"en": "nobody yet", "uk": "поки нікого", "de": "noch niemand"},
    "crew_not_found": {"en": "No one named \"{name}\". Try again or send /move.", "uk": "Нікого з ім'ям «{name}». Спробуйте ще або надішліть /move.", "de": "Niemand namens „{name}“. Versuch es erneut oder sende /move."},
    "crew_added": {"en": "Added {name} 🤝\n\nLet {name} know?", "uk": "{name} додано 🤝\n\nПовідомити {name}?", "de": "{name} hinzugefügt 🤝\n\n{name} benachrichtigen?"},
    "crew_added_you": {
        "en": "🤝 {name} added you to their crew — you'll see their moves.\n\n"
              "Add {name} back so they see yours?",
        "uk": "🤝 {name} додав(-ла) вас до свого кола — ви бачитимете їхні рухи.\n\n"
              "Додати {name} у відповідь, щоб вони бачили ваші?",
        "de": "🤝 {name} hat dich zur Crew hinzugefügt — du siehst ihre Bewegungen.\n\n"
              "{name} zurück hinzufügen, damit sie deine sehen?",
    },
    "crew_added_back": {
        "en": "🤝 Added {name} — you're now moving together.",
        "uk": "🤝 {name} додано — тепер ви рухаєтесь разом.",
        "de": "🤝 {name} hinzugefügt — ihr bewegt euch jetzt zusammen.",
    },
    "crew_in_list": {"en": "{name} is in your crew{status}. What now?", "uk": "{name} у вашому колі{status}. Що далі?", "de": "{name} ist in deiner Crew{status}. Was nun?"},
    "crew_muted_until": {"en": " (muted until {until})", "uk": " (без звуку до {until})", "de": " (stumm bis {until})"},
    "crew_removed": {"en": "Removed {name}.", "uk": "{name} прибрано.", "de": "{name} entfernt."},
    "crew_muted": {"en": "🔕 {name} muted until {until}.", "uk": "🔕 {name} без звуку до {until}.", "de": "🔕 {name} stumm bis {until}."},
    "crew_unmuted": {"en": "▶️ {name} unmuted.", "uk": "▶️ Звук {name} увімкнено.", "de": "▶️ {name} nicht mehr stumm."},
    "btn_unmute": {"en": "▶️ Unmute", "uk": "▶️ Увімкнути звук", "de": "▶️ Ton an"},
    "btn_mute_1d": {"en": "🔕 1 day", "uk": "🔕 1 день", "de": "🔕 1 Tag"},
    "btn_mute_1w": {"en": "🔕 1 week", "uk": "🔕 1 тиждень", "de": "🔕 1 Woche"},
    "btn_remove": {"en": "🗑 Remove", "uk": "🗑 Прибрати", "de": "🗑 Entfernen"},
    "cancelled": {"en": "Cancelled.", "uk": "Скасовано.", "de": "Abgebrochen."},
    # ── radar ──
    "radar_menu": {
        "en": "📡 Radar shows you a move from someone outside your crew — and can show yours to them.\n\nReceiving: {current}\n\nHow often?",
        "uk": "📡 Радар показує рух від когось поза вашим колом — і може показати ваш їм.\n\nОтримувати: {current}\n\nЯк часто?",
        "de": "📡 Radar zeigt dir eine Bewegung von jemandem außerhalb deiner Crew — und kann deine zeigen.\n\nEmpfangen: {current}\n\nWie oft?",
    },
    "radar_daily": {"en": "Daily", "uk": "Щодня", "de": "Täglich"},
    "radar_weekly": {"en": "Weekly", "uk": "Щотижня", "de": "Wöchentlich"},
    "radar_monthly": {"en": "Monthly", "uk": "Щомісяця", "de": "Monatlich"},
    "radar_off": {"en": "Off", "uk": "Вимкнено", "de": "Aus"},
    "radar_set": {"en": "📡 Radar: {label}.", "uk": "📡 Радар: {label}.", "de": "📡 Radar: {label}."},
    "radar_share_on": {"en": "📡 Share my moves: ON ✅", "uk": "📡 Ділитися моїми рухами: УВІМК ✅", "de": "📡 Meine Bewegungen teilen: AN ✅"},
    "radar_share_off": {"en": "📡 Share my moves: OFF 🚫", "uk": "📡 Ділитися моїми рухами: ВИМК 🚫", "de": "📡 Meine Bewegungen teilen: AUS 🚫"},
    # Anonymous on purpose: radar shares the move, never who made it.
    "radar_received": {
        "en": "📡 Someone outside your crew moved today.",
        "uk": "📡 Хтось поза вашим колом рухався сьогодні.",
        "de": "📡 Jemand außerhalb deiner Crew hat sich heute bewegt.",
    },
    # ── pause ──
    "pause_menu": {"en": "⏸️ Pause everything — no moves from your crew, no radar.\n\nPause for:", "uk": "⏸️ Призупинити все — жодних рухів від кола, жодного радару.\n\nПризупинити на:", "de": "⏸️ Alles pausieren — keine Bewegungen der Crew, kein Radar.\n\nPausieren für:"},
    "pause_active": {"en": "⏸️ Paused until {until}.\n\nExtend or resume:", "uk": "⏸️ Призупинено до {until}.\n\nПродовжити або відновити:", "de": "⏸️ Pausiert bis {until}.\n\nVerlängern oder fortsetzen:"},
    "pause_1d": {"en": "1 day", "uk": "1 день", "de": "1 Tag"},
    "pause_1w": {"en": "1 week", "uk": "1 тиждень", "de": "1 Woche"},
    "pause_1m": {"en": "1 month", "uk": "1 місяць", "de": "1 Monat"},
    "pause_resume": {"en": "▶️ Resume now", "uk": "▶️ Відновити зараз", "de": "▶️ Jetzt fortsetzen"},
    "pause_set": {"en": "⏸️ Paused until {until}.", "uk": "⏸️ Призупинено до {until}.", "de": "⏸️ Pausiert bis {until}."},
    "pause_resumed": {"en": "▶️ Resumed.", "uk": "▶️ Відновлено.", "de": "▶️ Fortgesetzt."},
    # ── reports ──
    "zap_report": {"en": "⚡ Yesterday your move got {n} {word}.", "uk": "⚡ Вчора ваш рух отримав {n} {word}.", "de": "⚡ Gestern hat deine Bewegung {n} {word} bekommen."},
    "zap_word_one": {"en": "lightning", "uk": "блискавку", "de": "Blitz"},
    "zap_word_many": {"en": "lightnings", "uk": "блискавок", "de": "Blitze"},
    "milestone": {"en": "🎉 {name}, {days} days in a row! Keep moving 💪", "uk": "🎉 {name}, {days} днів поспіль! Так тримати 💪", "de": "🎉 {name}, {days} Tage in Folge! Weiter so 💪"},
    "summary_header": {"en": "📅 {month} — {name}", "uk": "📅 {month} — {name}", "de": "📅 {month} — {name}"},
    "summary_days": {"en": "🏃 Days moved: {count} of {total} ({pct}%)", "uk": "🏃 Днів у русі: {count} з {total} ({pct}%)", "de": "🏃 Bewegte Tage: {count} von {total} ({pct}%)"},
    "summary_streak": {"en": "🔥 Longest streak: {days} days", "uk": "🔥 Найдовша серія: {days} днів", "de": "🔥 Längste Serie: {days} Tage"},
    "summary_zaps": {"en": "⚡ Lightnings received: {n}", "uk": "⚡ Отримано блискавок: {n}", "de": "⚡ Erhaltene Blitze: {n}"},
    "invite_text": {
        "en": "🔗 Share this link with anyone you'd like to move with:\n\n{link}\n\n"
              "When they tap it, you'll be added to each other's crew automatically — "
              "whether they're new here or already registered.",
        "uk": "🔗 Надішліть це посилання тому, з ким хочете рухатись разом:\n\n{link}\n\n"
              "Коли вони його відкриють, ви автоматично потрапите в кола одне одного — "
              "незалежно від того, нові вони тут чи вже зареєстровані.",
        "de": "🔗 Teile diesen Link mit allen, mit denen du dich bewegen möchtest:\n\n{link}\n\n"
              "Wenn sie ihn antippen, landet ihr automatisch in der Crew des anderen — "
              "egal ob neu hier oder schon registriert.",
    },
    "btn_language": {"en": "🌍 Language", "uk": "🌍 Мова", "de": "🌍 Sprache"},
    "lang_changed": {
        "en": "🌍 Language set to English.",
        "uk": "🌍 Мову змінено на українську.",
        "de": "🌍 Sprache auf Deutsch gestellt.",
    },
    "invite_line": {
        "en": "🔗 Your invite link — share it to connect instantly:\n{link}",
        "uk": "🔗 Ваше посилання-запрошення — надішліть, щоб одразу з'єднатись:\n{link}",
        "de": "🔗 Dein Einladungslink — teile ihn, um euch sofort zu verbinden:\n{link}",
    },
    "invite_connected": {
        "en": "🤝 You and {name} are now moving together!",
        "uk": "🤝 Тепер ви з {name} рухаєтесь разом!",
        "de": "🤝 Du und {name} bewegt euch jetzt zusammen!",
    },
    "invite_already": {
        "en": "You're already moving with {name} 🤝",
        "uk": "Ви вже рухаєтесь з {name} 🤝",
        "de": "Du bewegst dich schon mit {name} 🤝",
    },
    "invite_self": {
        "en": "That's your own invite link 🙂 Share it with someone else.",
        "uk": "Це ваше власне посилання 🙂 Надішліть його комусь іншому.",
        "de": "Das ist dein eigener Link 🙂 Teile ihn mit jemand anderem.",
    },
    "summary_all_header": {"en": "📊 Your months", "uk": "📊 Ваші місяці", "de": "📊 Deine Monate"},
    "summary_none": {"en": "No moves recorded yet.", "uk": "Ще немає записаних рухів.", "de": "Noch keine Bewegungen erfasst."},
}


# Shown before we know their language, so it carries all three.
_LANG_PROMPT = "🌍 Choose your language\nОберіть мову\nSprache wählen"


def _kb_lang() -> dict:
    return {"inline_keyboard": [[
        {"text": "English", "callback_data": "mv:lang:en"},
        {"text": "Українська", "callback_data": "mv:lang:uk"},
        {"text": "Deutsch", "callback_data": "mv:lang:de"},
    ]]}


def _main_kb(lang: str = "en") -> dict:
    return {
        "keyboard": [
            [{"text": _t("btn_move", lang)}, {"text": _t("btn_radar", lang)}],
            [{"text": _t("btn_pause", lang)}, {"text": _t("btn_info", lang)}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _build_button_map() -> dict[str, str]:
    m: dict[str, str] = {}
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


def _by_name(cur, name: str):
    cur.execute("SELECT * FROM move_users WHERE LOWER(participant_name) = LOWER(%s)", (name,))
    return cur.fetchone()


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


def _zap_kb(entry_id: int, sent: bool = False, lang: str = "en") -> dict:
    """No running total — a move isn't a popularity contest. You only see whether
    *you* cheered; the author gets the tally next morning."""
    return {"inline_keyboard": [[
        {"text": _t("zap_btn_sent" if sent else "zap_btn", lang),
         "callback_data": f"mv:zap:{entry_id}"}
    ]]}


def _mark_zapped(cur, entry_id: int, reactor_tg_id: int) -> None:
    """Tick the button on the reactor's own copy only — each recipient has their
    own forwarded message, so nobody else's view changes."""
    cur.execute(
        "SELECT chat_id, message_id FROM move_forwards "
        "WHERE entry_id = %s AND recipient_tg_id = %s",
        (entry_id, reactor_tg_id),
    )
    for f in cur.fetchall():
        _api_call("editMessageReplyMarkup", {
            "chat_id": f["chat_id"], "message_id": f["message_id"],
            "reply_markup": _zap_kb(entry_id, sent=True),
        })


# ── logging a move ───────────────────────────────────────────────────────────

def _deliver(cur, conn, user, entry_id: int, media: tuple | None, text_body: str | None) -> list[str]:
    """Copy the move to each crew member, remembering where it landed so a late
    comment can be threaded under it. Returns the names it reached."""
    sender = user["participant_name"]
    lang_of = {}
    names = []
    for rid, chat_id, rname in _recipients(cur, user["telegram_user_id"], sender):
        rlang = _lang(cur, rid)
        lang_of[rid] = rlang
        header = _t("crew_move", rlang, name=sender)
        if media:
            from_chat, msg_id = media
            res = _copy(from_chat, msg_id, chat_id, reply_markup=_zap_kb(entry_id, lang=rlang))
            if res and res.get("message_id"):
                cur.execute(
                    "INSERT INTO move_forwards (entry_id, recipient_tg_id, chat_id, message_id) "
                    "VALUES (%s, %s, %s, %s)",
                    (entry_id, rid, chat_id, res["message_id"]),
                )
            _send(chat_id, header)
        else:
            res = _send(chat_id, f"{header}\n{text_body or ''}".strip(),
                        reply_markup=_zap_kb(entry_id, lang=rlang))
            if res and res.get("message_id"):
                cur.execute(
                    "INSERT INTO move_forwards (entry_id, recipient_tg_id, chat_id, message_id) "
                    "VALUES (%s, %s, %s, %s)",
                    (entry_id, rid, chat_id, res["message_id"]),
                )
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
        _send(chat_id, _t("already_logged", lang))
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
    if names:
        _send(chat_id, _t("logged_shared", lang, streak=suffix, names=", ".join(names)),
              reply_markup=_main_kb(lang))
    else:
        _send(chat_id, _t("logged", lang, streak=suffix), reply_markup=_main_kb(lang))
    _log(f"🏃 Move logged\n👤 {user['participant_name']}"
         + (f"\n📤 → {', '.join(names)}" if names else "\n📤 → nobody"))
    _check_milestone(cur, conn, user, streak)


def _attach_comment(cur, conn, tg_id: int, chat_id: int, text: str) -> bool:
    """A text sent shortly after a move is its comment — delivered as a reply
    under each forwarded copy so it reads as one post. True if it was used."""
    cur.execute(
        "SELECT id, created_at, comment FROM move_entries "
        "WHERE telegram_user_id = %s AND entry_date = %s",
        (tg_id, date.today()),
    )
    e = cur.fetchone()
    if not e or e["comment"]:
        return False
    age = (datetime.now(timezone.utc) - e["created_at"]).total_seconds() / 60
    if age > _COMMENT_WINDOW_MINUTES:
        return False

    cur.execute("UPDATE move_entries SET comment = %s WHERE id = %s", (text, e["id"]))
    cur.execute("SELECT chat_id, message_id FROM move_forwards WHERE entry_id = %s", (e["id"],))
    for f in cur.fetchall():
        _send(f["chat_id"], f"💬 {text}", reply_to=f["message_id"])
    conn.commit()
    _send(chat_id, _t("comment_added", _lang(cur, tg_id)))
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
    """`/start`, optionally with an `inv_<id>` deep-link payload.

    Already registered? We don't re-register — but we still honour the invite and
    connect the two, which is the useful thing to do with a tapped link.
    """
    inviter_id = None
    if payload.startswith("inv_"):
        try:
            inviter_id = int(payload[4:])
        except ValueError:
            inviter_id = None

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


def _invite_line(tg_id: int, lang: str) -> str:
    return _t("invite_line", lang, link=f"https://t.me/{_bot_username()}?start=inv_{tg_id}")


def _cmd_info(tg_id: int, chat_id: int, lang: str) -> None:
    body = _t("info_body", lang,
              tagline=_t("tagline", lang),
              mins=_COMMENT_WINDOW_MINUTES,
              rdays=_RADAR_REPEAT_DAYS,
              miles="/".join(str(m) for m in _MILESTONES))
    # Inline button, not the reply keyboard — the persistent one stays put anyway.
    _send(chat_id, f"{body}\n\n{_invite_line(tg_id, lang)}",
          reply_markup={"inline_keyboard": [[
              {"text": _t("btn_language", lang), "callback_data": "mv:langmenu"}
          ]]})


def _cmd_move(cur, tg_id: int, chat_id: int, lang: str) -> None:
    names = [n for n in _crew_names(cur, tg_id) if n != "__all__"]
    crew = ", ".join(names) or _t("crew_nobody", lang)
    _send(chat_id, f"{_t('crew_menu', lang, crew=crew)}\n\n{_invite_line(tg_id, lang)}")


def _handle_crew_name(cur, conn, tg_id: int, chat_id: int, lang: str, name: str) -> None:
    """A name typed after /move: add it, or offer mute/remove if already there."""
    target = _by_name(cur, name)
    if not target or target["telegram_user_id"] == tg_id:
        _send(chat_id, _t("crew_not_found", lang, name=name))
        return
    tname = target["participant_name"]
    cur.execute(
        "SELECT 1 FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
        (tg_id, tname),
    )
    if cur.fetchone():
        cur.execute(
            "SELECT muted_until FROM move_mute WHERE telegram_user_id = %s "
            "AND LOWER(muted_name) = LOWER(%s) AND muted_until > NOW()",
            (tg_id, tname),
        )
        m = cur.fetchone()
        status = _t("crew_muted_until", lang, until=m["muted_until"].strftime("%b %d")) if m else ""
        rows = []
        if m:
            rows.append([{"text": _t("btn_unmute", lang), "callback_data": f"mv:crew:unmute:{tname}"}])
        rows.append([
            {"text": _t("btn_mute_1d", lang), "callback_data": f"mv:crew:mute1d:{tname}"},
            {"text": _t("btn_mute_1w", lang), "callback_data": f"mv:crew:mute1w:{tname}"},
        ])
        rows.append([{"text": _t("btn_remove", lang), "callback_data": f"mv:crew:remove:{tname}"}])
        rows.append([{"text": _t("kb_cancel", lang), "callback_data": "mv:crew:cancel"}])
        _send(chat_id, _t("crew_in_list", lang, name=tname, status=status),
              reply_markup={"inline_keyboard": rows})
        return
    cur.execute(
        "INSERT INTO move_crew (telegram_user_id, crew_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (tg_id, tname),
    )
    conn.commit()
    me = _user(cur, tg_id)
    _log(f"🤝 Move: crew +\n• {me['participant_name'] if me else tg_id} → {tname}")
    _send(chat_id, _t("crew_added", lang, name=tname), reply_markup={"inline_keyboard": [[
        {"text": _t("kb_yes", lang), "callback_data": f"mv:crew:notify:{tname}"},
        {"text": _t("kb_no", lang), "callback_data": "mv:crew:cancel"},
    ]]})


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


def _cmd_invite(cur, tg_id: int, chat_id: int, lang: str) -> None:
    link = f"https://t.me/{_bot_username()}?start=inv_{tg_id}"
    _send(chat_id, _t("invite_text", lang, link=link))


def _apply_invite(cur, conn, tg_id: int, chat_id: int, lang: str, inviter_id: int) -> None:
    """Wire up a deep-link invite once both sides are registered."""
    if inviter_id == tg_id:
        _send(chat_id, _t("invite_self", lang))
        return
    inviter = _user(cur, inviter_id)
    if not inviter or not inviter["participant_name"]:
        return                                    # stale or unregistered inviter — ignore
    result = _connect(cur, conn, tg_id, inviter_id)
    if result == "bad":
        return
    me = _user(cur, tg_id)
    if result == "already":
        _send(chat_id, _t("invite_already", lang, name=inviter["participant_name"]))
        return
    _send(chat_id, _t("invite_connected", lang, name=inviter["participant_name"]))
    _send(inviter["chat_id"] or inviter_id,
          _t("invite_connected", _norm_lang(inviter["language_code"]),
             name=me["participant_name"]))
    _log(f"🔗 Move: invite\n• {inviter['participant_name']} ↔ {me['participant_name']}")


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


def _cmd_radar(cur, tg_id: int, chat_id: int, lang: str) -> None:
    u = _user(cur, tg_id)
    cur_freq = (u["radar_freq"] if u else "never") or "never"
    rows = [[{"text": ("✓ " if f == cur_freq else "") + _radar_label(f, lang),
              "callback_data": f"mv:radar:{f}"}] for f in _RADAR_FREQS]
    on = bool(u and u["radar_send"])
    rows.append([{"text": _t("radar_share_on" if on else "radar_share_off", lang),
                  "callback_data": f"mv:radarsend:{'off' if on else 'on'}"}])
    _send(chat_id, _t("radar_menu", lang, current=_radar_label(cur_freq, lang)),
          reply_markup={"inline_keyboard": rows})


def _cmd_pause(cur, tg_id: int, chat_id: int, lang: str) -> None:
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
        text = _t("pause_active", lang, until=u["paused_until"].strftime("%b %d"))
    else:
        text = _t("pause_menu", lang)
    _send(chat_id, text, reply_markup={"inline_keyboard": rows})


# ── webhook ──────────────────────────────────────────────────────────────────

def handle_move_webhook(body: dict, conn) -> None:
    cur = conn.cursor()

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
        _cmd_info(tg_id, chat_id, lang)
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
    if word in ("language", "lang"):
        _send(chat_id, _LANG_PROMPT, reply_markup=_kb_lang())
        return
    if word == "log":
        if not args:
            _send(chat_id, _t("log_usage", lang))
            return
        _log_move(cur, conn, tg_id, chat_id, None, args)
        conn.commit()
        return

    # 4) a name typed after /move
    if state == "await_crew":
        _clear_state(cur, tg_id)
        _handle_crew_name(cur, conn, tg_id, chat_id, lang, text)
        conn.commit()
        return

    # 5) a plain text soon after a move is its comment
    if _attach_comment(cur, conn, tg_id, chat_id, text):
        return

    _send(chat_id, _t("unknown_msg", lang), reply_markup=_main_kb(lang))
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
        if fresh:
            _mark_zapped(cur, entry_id, tg_id)
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
        _send(chat_id, _t("start_body", code, tagline=_t("tagline", code)))
        return

    if body.startswith("crew:"):
        sub = body[5:]
        _api_call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if sub == "cancel":
            _send(chat_id, _t("cancelled", lang))
            return
        action, _, name = sub.partition(":")
        if action == "notify":
            t = _by_name(cur, name)
            me = _user(cur, tg_id)
            if t and me:
                tlang = _norm_lang(t["language_code"])
                mine = me["participant_name"]
                # Crew is directional, so offer the reciprocal add — otherwise
                # their moves reach you but yours reach nobody.
                _send(t["chat_id"] or t["telegram_user_id"],
                      _t("crew_added_you", tlang, name=mine),
                      reply_markup={"inline_keyboard": [[
                          {"text": _t("kb_yes", tlang), "callback_data": f"mv:crew:addback:{mine}"},
                          {"text": _t("kb_no", tlang), "callback_data": "mv:crew:cancel"},
                      ]]})
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
        if action == "remove":
            cur.execute("DELETE FROM move_crew WHERE telegram_user_id = %s AND LOWER(crew_name) = LOWER(%s)",
                        (tg_id, name))
            conn.commit()
            _send(chat_id, _t("crew_removed", lang, name=name))
            me = _user(cur, tg_id)
            _log(f"🗑 Move: crew −\n• {me['participant_name'] if me else tg_id} ✗ {name}")
            return
        if action == "unmute":
            cur.execute("DELETE FROM move_mute WHERE telegram_user_id = %s AND LOWER(muted_name) = LOWER(%s)",
                        (tg_id, name))
            conn.commit()
            _send(chat_id, _t("crew_unmuted", lang, name=name))
            return
        if action in ("mute1d", "mute1w"):
            until = datetime.now(timezone.utc) + timedelta(days=1 if action == "mute1d" else 7)
            cur.execute(
                "INSERT INTO move_mute (telegram_user_id, muted_name, muted_until) VALUES (%s, %s, %s) "
                "ON CONFLICT (telegram_user_id, muted_name) DO UPDATE SET muted_until = EXCLUDED.muted_until",
                (tg_id, name, until),
            )
            conn.commit()
            _send(chat_id, _t("crew_muted", lang, name=name, until=until.strftime("%b %d")))
        return

    if body.startswith("radarsend:"):
        on = body[len("radarsend:"):] == "on"
        cur.execute("UPDATE move_users SET radar_send = %s WHERE telegram_user_id = %s", (on, tg_id))
        conn.commit()
        _api_call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _send(chat_id, _t("radar_share_on" if on else "radar_share_off", lang))
        return

    if body.startswith("radar:"):
        freq = body[len("radar:"):]
        cur.execute("UPDATE move_users SET radar_freq = %s WHERE telegram_user_id = %s", (freq, tg_id))
        conn.commit()
        _api_call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        _send(chat_id, _t("radar_set", lang, label=_radar_label(freq, lang)))
        return

    if body.startswith("pause:"):
        what = body[len("pause:"):]
        _api_call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
        if what == "resume":
            cur.execute("UPDATE move_users SET paused_until = NULL WHERE telegram_user_id = %s", (tg_id,))
            conn.commit()
            _send(chat_id, _t("pause_resumed", lang))
            return
        days = {"1d": 1, "1w": 7, "1m": 30}.get(what, 1)
        until = datetime.now(timezone.utc) + timedelta(days=days)
        cur.execute("UPDATE move_users SET paused_until = %s WHERE telegram_user_id = %s", (until, tg_id))
        conn.commit()
        _send(chat_id, _t("pause_set", lang, until=until.strftime("%b %d")))
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
    for r in cur.fetchall():
        n = r["zaps"] or 0
        if not n:
            continue
        lang = _norm_lang(r["language_code"])
        word = _t("zap_word_one" if n == 1 else "zap_word_many", lang)
        _send(r["chat_id"] or r["telegram_user_id"], _t("zap_report", lang, n=n, word=word))
    conn.commit()


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
    for u in cur.fetchall():
        rid = u["telegram_user_id"]
        now = datetime.now(timezone.utc)
        if u["paused_until"] and u["paused_until"] > now:
            continue
        if not _radar_due(u["radar_freq"], u["radar_last_received"]):
            continue

        crew = {n.lower() for n in _crew_names(cur, rid)}
        cur.execute(
            "SELECT e.id, e.chat_id, e.message_id, e.text_body, "
            "       u2.telegram_user_id AS from_id, u2.participant_name "
            "FROM move_entries e JOIN move_users u2 ON u2.telegram_user_id = e.telegram_user_id "
            "WHERE e.entry_date >= %s AND u2.radar_send = TRUE AND u2.telegram_user_id <> %s "
            "ORDER BY random() LIMIT 25",
            (today - timedelta(days=2), rid),
        )
        for cand in cur.fetchall():
            if (cand["participant_name"] or "").lower() in crew:
                continue
            cur.execute(
                "SELECT 1 FROM move_radar_history WHERE telegram_user_id = %s AND from_tg_id = %s "
                "AND sent_at > NOW() - make_interval(days => %s)",
                (rid, cand["from_id"], _RADAR_REPEAT_DAYS),
            )
            if cur.fetchone():
                continue

            lang = _norm_lang(u["language_code"])
            chat_id = u["chat_id"] or rid
            kb = _zap_kb(cand["id"], lang=lang)
            if cand["message_id"]:
                # The author may have deleted the original — copyMessage then
                # fails, so move on to another candidate rather than sending a
                # bare "someone moved" with nothing attached.
                if not _copy(cand["chat_id"], cand["message_id"], chat_id, reply_markup=kb):
                    continue
            else:
                _send(chat_id, cand["text_body"] or "", reply_markup=kb)
            _send(chat_id, _t("radar_received", lang))
            cur.execute(
                "INSERT INTO move_radar_history (telegram_user_id, from_tg_id) VALUES (%s, %s)",
                (rid, cand["from_id"]),
            )
            cur.execute(
                "UPDATE move_users SET radar_last_received = NOW() WHERE telegram_user_id = %s",
                (rid,),
            )
            conn.commit()
            _log(f"📡 Move: radar\n• {cand['participant_name']} → {u['participant_name']}")
            break
    conn.commit()


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
        _send(u["chat_id"] or tg_id, "\n".join(lines))
    conn.commit()
