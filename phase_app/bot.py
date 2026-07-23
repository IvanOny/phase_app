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

# Plain-text aliases for slash commands — update when adding a new command
_COMMAND_ALIASES = {"info", "help", "start", "rename", "secret", "radar", "pause", "sweat"}

# ── i18n ──────────────────────────────────────────────────────────────────────
# Full localization in English / Ukrainian / German. Every user-facing string
# lives in _STRINGS keyed by a short slug, with one entry per supported language.
# _t(key, lang, **fmt) looks it up (falling back to English) and .format()s it.
# When adding a new user-facing string, add a key here with en/uk/de.

_SUPPORTED_LANGS = ("en", "uk", "de")


def _norm_lang(raw: str | None) -> str:
    """Map a Telegram language_code (e.g. 'uk-UA', 'de') to a supported lang."""
    if not raw:
        return "en"
    code = raw.split("-")[0].lower()
    return code if code in _SUPPORTED_LANGS else "en"


def _t(key: str, lang: str = "en", **fmt) -> str:
    entry = _STRINGS.get(key, {})
    template = entry.get(lang) or entry.get("en") or key
    return template.format(**fmt) if fmt else template


def _user_lang(cur, tg_id: int) -> str:
    cur.execute("SELECT language_code FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
    row = cur.fetchone()
    return _norm_lang(row["language_code"] if row else None)


def _lang_for_name(cur, name: str) -> str | None:
    cur.execute("SELECT language_code FROM telegram_bot_users WHERE participant_name = %s", (name,))
    row = cur.fetchone()
    return row["language_code"] if row else None


_STRINGS: dict[str, dict[str, str]] = {
    # ── Main keyboard buttons ──
    "btn_sweat": {"en": "🤝 Sweat with", "uk": "🤝 Спільний піт", "de": "🤝 Schwitzen mit"},
    "btn_radar": {"en": "📡 Radar", "uk": "📡 Радар", "de": "📡 Radar"},
    "btn_pause": {"en": "⏸️ Pause", "uk": "⏸️ Пауза", "de": "⏸️ Pause"},
    "btn_info": {"en": "ℹ️ Info", "uk": "ℹ️ Інфо", "de": "ℹ️ Info"},
    # ── Generic inline buttons ──
    "kb_anyone": {"en": "Anyone", "uk": "Будь-хто", "de": "Jeder"},
    "kb_done": {"en": "Done", "uk": "Готово", "de": "Fertig"},
    "kb_cancel": {"en": "Cancel", "uk": "Скасувати", "de": "Abbrechen"},
    "kb_yes": {"en": "Yes", "uk": "Так", "de": "Ja"},
    "kb_no": {"en": "No", "uk": "Ні", "de": "Nein"},
    # ── Pause keyboard ──
    "pause_1d": {"en": "1 day", "uk": "1 день", "de": "1 Tag"},
    "pause_1w": {"en": "1 week", "uk": "1 тиждень", "de": "1 Woche"},
    "pause_1m": {"en": "1 month", "uk": "1 місяць", "de": "1 Monat"},
    "pause_resume": {"en": "▶️ Resume now", "uk": "▶️ Відновити зараз", "de": "▶️ Jetzt fortsetzen"},
    # ── Radar keyboard labels ──
    "radar_daily": {"en": "Daily", "uk": "Щодня", "de": "Täglich"},
    "radar_weekly": {"en": "Weekly", "uk": "Щотижня", "de": "Wöchentlich"},
    "radar_monthly": {"en": "Monthly", "uk": "Щомісяця", "de": "Monatlich"},
    "radar_once": {"en": "Just once", "uk": "Лише раз", "de": "Nur einmal"},
    "radar_off": {"en": "Off", "uk": "Вимкнено", "de": "Aus"},
    "radar_period_daily": {"en": "every day", "uk": "щодня", "de": "jeden Tag"},
    "radar_period_weekly": {"en": "every week", "uk": "щотижня", "de": "jede Woche"},
    "radar_period_monthly": {"en": "every month", "uk": "щомісяця", "de": "jeden Monat"},
    "radar_share_on": {"en": "📡 Share my videos: ON ✅", "uk": "📡 Ділитися моїми відео: УВІМК ✅", "de": "📡 Meine Videos teilen: AN ✅"},
    "radar_share_off": {"en": "📡 Share my videos: OFF 🚫", "uk": "📡 Ділитися моїми відео: ВИМК 🚫", "de": "📡 Meine Videos teilen: AUS 🚫"},
    "radar_send_yes": {"en": "✅ Yes, that's fine", "uk": "✅ Так, згоден", "de": "✅ Ja, in Ordnung"},
    "radar_send_no": {"en": "🚫 No, keep my videos in my crew", "uk": "🚫 Ні, лишити відео в моєму колі", "de": "🚫 Nein, Videos nur in meiner Crew"},
    # ── Sweat manage keyboard ──
    "sweat_unmute_btn": {"en": "▶️ Unmute (muted until {until})", "uk": "▶️ Увімкнути звук (без звуку до {until})", "de": "▶️ Ton an (stumm bis {until})"},
    "sweat_mute_1d_btn": {"en": "🔕 Mute 1 day", "uk": "🔕 Без звуку 1 день", "de": "🔕 1 Tag stumm"},
    "sweat_mute_1w_btn": {"en": "🔕 Mute 1 week", "uk": "🔕 Без звуку 1 тиждень", "de": "🔕 1 Woche stumm"},
    "sweat_mute_1m_btn": {"en": "🔕 Mute 1 month", "uk": "🔕 Без звуку 1 місяць", "de": "🔕 1 Monat stumm"},
    "sweat_remove_btn": {"en": "🗑 Remove from sweat list", "uk": "🗑 Прибрати зі списку", "de": "🗑 Aus Liste entfernen"},
    # ── Common ──
    "register_first": {"en": "Please register first — send /start", "uk": "Спершу зареєструйтесь — надішліть /start", "de": "Bitte zuerst registrieren — sende /start"},
    "letters_32": {"en": "Please use letters only, up to 32 characters.", "uk": "Лише літери, до 32 символів.", "de": "Nur Buchstaben, bis zu 32 Zeichen."},
    "letters_64": {"en": "Letters only please (up to 64 characters).", "uk": "Лише літери, будь ласка (до 64 символів).", "de": "Bitte nur Buchstaben (bis zu 64 Zeichen)."},
    "name_taken": {"en": "\"{name}\" is already taken. Please choose a different name.", "uk": "Ім'я «{name}» вже зайняте. Оберіть інше.", "de": "„{name}“ ist bereits vergeben. Bitte wähle einen anderen Namen."},
    "ask_secret": {"en": "Name a fictional character you love:", "uk": "Назвіть улюбленого вигаданого персонажа:", "de": "Nenne eine erfundene Figur, die du magst:"},
    "unknown_msg": {"en": "Tap ℹ️ Info to see what I can do.", "uk": "Натисніть ℹ️ Інфо, щоб побачити, що я вмію.", "de": "Tippe auf ℹ️ Info, um zu sehen, was ich kann."},
    # ── Reps logging ──
    "how_many_reps": {"en": "{greet}how many reps?", "uk": "{greet}скільки повторень?", "de": "{greet}wie viele Wiederholungen?"},
    "reps_logged": {"en": "✓ {reps} reps logged", "uk": "✓ {reps} повторень записано", "de": "✓ {reps} Wiederholungen gespeichert"},
    "reps_updated": {"en": "✓ updated to {reps} reps", "uk": "✓ оновлено до {reps} повторень", "de": "✓ auf {reps} Wiederholungen aktualisiert"},
    "reps_short": {"en": "{reps} reps", "uk": "{reps} повторень", "de": "{reps} Wdh."},
    "confirm_reps": {"en": "✓ {reps} reps", "uk": "✓ {reps} повторень", "de": "✓ {reps} Wdh."},
    "confirm_reps_comment": {"en": "✓ {reps} reps ({comment})", "uk": "✓ {reps} повторень ({comment})", "de": "✓ {reps} Wdh. ({comment})"},
    "forwarded_to": {"en": "{confirm} → forwarded to {names}", "uk": "{confirm} → надіслано: {names}", "de": "{confirm} → weitergeleitet an {names}"},
    "confirm_logged": {"en": "{confirm} logged", "uk": "{confirm} записано", "de": "{confirm} gespeichert"},
    # ── /rename ──
    "ask_rename": {"en": "{greet}what would you like to change your name to?", "uk": "{greet}на яке ім'я змінити?", "de": "{greet}wie möchtest du dich nennen?"},
    "renamed_done": {"en": "Done! Your name is now {name}.\n\nUpdated app link:\n{url}", "uk": "Готово! Тепер ваше ім'я {name}.\n\nОновлене посилання:\n{url}", "de": "Fertig! Dein Name ist jetzt {name}.\n\nAktualisierter App-Link:\n{url}"},
    # ── /secret ──
    "secret_done": {"en": "Done! Your new app link:\n{url}", "uk": "Готово! Ваше нове посилання:\n{url}", "de": "Fertig! Dein neuer App-Link:\n{url}"},
    # ── /start ──
    "already_registered": {"en": "You're already registered as {name}.\n\nYour app link:\n{url}", "uk": "Ви вже зареєстровані як {name}.\n\nВаше посилання:\n{url}", "de": "Du bist bereits als {name} registriert.\n\nDein App-Link:\n{url}"},
    "ask_name_first": {"en": "First, what would you like to be called?", "uk": "Спершу: як вас називати?", "de": "Zuerst: Wie möchtest du genannt werden?"},
    "welcome_registered": {"en": "Welcome, {name}! 👋 Your app link:\n{url}\n\nNext: add your crew via 🤝 Sweat with.\nThey'll get every video you log — and you'll get theirs.", "uk": "Вітаємо, {name}! 👋 Ваше посилання:\n{url}\n\nДалі: додайте свій гурт через 🤝 Спільний піт.\nВони отримуватимуть кожне ваше відео — а ви їхні.", "de": "Willkommen, {name}! 👋 Dein App-Link:\n{url}\n\nAls Nächstes: Füge deine Crew über 🤝 Schwitzen mit hinzu.\nSie bekommen jedes deiner Videos — und du ihre."},
    # ── Info / start body ──
    "app_link_line": {"en": "\nYour app link:\nhttps://phase-app-yf5x.vercel.app/?token={token}\n", "uk": "\nВаше посилання на застосунок:\nhttps://phase-app-yf5x.vercel.app/?token={token}\n", "de": "\nDein App-Link:\nhttps://phase-app-yf5x.vercel.app/?token={token}\n"},
    "app_link_none": {"en": "\n(register first with /start)\n", "uk": "\n(спершу зареєструйтесь через /start)\n", "de": "\n(zuerst mit /start registrieren)\n"},
    "info_body": {
        "en": "👋 Welcome to Бурчик Challenge!\n\n"
              "3 minutes of AMRAP burpees every day — tracked, shared, and competed.\n\n"
              "How it works:\n"
              "• Record the first minute of your 3-minute burpee session as a round video bubble and send it here\n"
              "• Then type your rep count. Optional: add a comment after a comma — it shows up in the app: 25, tough day\n"
              "• Your workout is logged and forwarded to your crew\n\n"
              "{link_line}\n"
              "Available commands:\n\n"
              "/start — register your name\n"
              "/rename — change your name\n"
              "/secret — update your app link secret\n"
              "/sweat — find who you share and follow\n"
              "/radar — receive and send random burpees from outside your sweat list\n"
              "/pause — pause all notifications for 1 day, 1 week, or 1 month\n"
              "/info — show this list",
        "uk": "👋 Ласкаво просимо до Бурчик Challenge!\n\n"
              "3 хвилини берпі AMRAP щодня — з обліком, обміном і змаганням.\n\n"
              "Як це працює:\n"
              "• Запишіть першу хвилину вашої 3-хвилинної сесії берпі як кругле відео-повідомлення й надішліть сюди\n"
              "• Потім напишіть кількість повторень. За бажанням: додайте коментар після коми — він з'явиться в застосунку: 25, важкий день\n"
              "• Ваше тренування зберігається й надсилається вашому гурту\n\n"
              "{link_line}\n"
              "Доступні команди:\n\n"
              "/start — зареєструвати ім'я\n"
              "/rename — змінити ім'я\n"
              "/secret — оновити секрет посилання\n"
              "/sweat — керувати тим, з ким ви ділитесь і за ким стежите\n"
              "/radar — отримувати й надсилати випадкові берпі за межами вашого списку\n"
              "/pause — призупинити всі сповіщення на 1 день, 1 тиждень чи 1 місяць\n"
              "/info — показати цей список",
        "de": "👋 Willkommen bei Бурчик Challenge!\n\n"
              "3 Minuten AMRAP-Burpees jeden Tag — erfasst, geteilt und im Wettkampf.\n\n"
              "So funktioniert's:\n"
              "• Nimm die erste Minute deiner 3-minütigen Burpee-Session als rundes Video-Bubble auf und schick es hierher\n"
              "• Dann tippe deine Wiederholungszahl. Optional: ein Kommentar nach einem Komma — er erscheint in der App: 25, harter Tag\n"
              "• Dein Workout wird gespeichert und an deine Crew weitergeleitet\n\n"
              "{link_line}\n"
              "Verfügbare Befehle:\n\n"
              "/start — Namen registrieren\n"
              "/rename — Namen ändern\n"
              "/secret — App-Link-Geheimnis aktualisieren\n"
              "/sweat — verwalten, mit wem du teilst und wem du folgst\n"
              "/radar — zufällige Burpees von außerhalb deiner Liste empfangen und senden\n"
              "/pause — alle Benachrichtigungen für 1 Tag, 1 Woche oder 1 Monat pausieren\n"
              "/info — diese Liste anzeigen",
    },
    "start_body": {
        "en": "👋 Welcome to Бурчик Challenge!\n\n"
              "3 minutes of AMRAP burpees every day — tracked, shared, and competed.\n\n"
              "How it works:\n"
              "• Record the first minute of your 3-minute burpee session as a round video bubble and send it here\n"
              "• Then type your rep count. Optional: add a comment after a comma — it shows up in the app: 25, tough day\n"
              "• Your workout is logged and forwarded to your crew\n\n"
              "Use /sweat to find who you share and follow.\n\n"
              "First, what would you like to be called?",
        "uk": "👋 Ласкаво просимо до Бурчик Challenge!\n\n"
              "3 хвилини берпі AMRAP щодня — з обліком, обміном і змаганням.\n\n"
              "Як це працює:\n"
              "• Запишіть першу хвилину вашої 3-хвилинної сесії берпі як кругле відео-повідомлення й надішліть сюди\n"
              "• Потім напишіть кількість повторень. За бажанням: додайте коментар після коми — він з'явиться в застосунку: 25, важкий день\n"
              "• Ваше тренування зберігається й надсилається вашому гурту\n\n"
              "Скористайтесь /sweat, щоб керувати тим, з ким ви ділитесь і за ким стежите.\n\n"
              "Спершу: як вас називати?",
        "de": "👋 Willkommen bei Бурчик Challenge!\n\n"
              "3 Minuten AMRAP-Burpees jeden Tag — erfasst, geteilt und im Wettkampf.\n\n"
              "So funktioniert's:\n"
              "• Nimm die erste Minute deiner 3-minütigen Burpee-Session als rundes Video-Bubble auf und schick es hierher\n"
              "• Dann tippe deine Wiederholungszahl. Optional: ein Kommentar nach einem Komma — er erscheint in der App: 25, harter Tag\n"
              "• Dein Workout wird gespeichert und an deine Crew weitergeleitet\n\n"
              "Nutze /sweat, um zu verwalten, mit wem du teilst und wem du folgst.\n\n"
              "Zuerst: Wie möchtest du genannt werden?",
    },
    # ── Radar ──
    "radar_setup_freq": {"en": "📡 Radar works differently — it sends you one random burpee from someone outside your crew. How often?", "uk": "📡 Радар працює інакше — він надсилає вам одне випадкове берпі від когось поза вашим гуртом. Як часто?", "de": "📡 Radar funktioniert anders — es schickt dir einen zufälligen Burpee von jemandem außerhalb deiner Crew. Wie oft?"},
    "radar_nudge_freq": {"en": "📡 Before we continue — Radar can send you a random burpee from outside your crew. How often?", "uk": "📡 Перш ніж продовжити — Радар може надсилати вам випадкове берпі за межами вашого гурту. Як часто?", "de": "📡 Bevor wir fortfahren — Radar kann dir einen zufälligen Burpee von außerhalb deiner Crew schicken. Wie oft?"},
    "radar_menu": {"en": "📡 Radar — receive random burpees & share yours with the world outside your crew.\n\nReceive: {current}\n\nHow often?", "uk": "📡 Радар — отримуйте випадкові берпі й діліться своїми зі світом поза вашим гуртом.\n\nОтримувати: {current}\n\nЯк часто?", "de": "📡 Radar — empfange zufällige Burpees und teile deine mit der Welt außerhalb deiner Crew.\n\nEmpfangen: {current}\n\nWie oft?"},
    "radar_ask_send": {"en": "📡 Radar works both ways — you can not only receive random burpees, but your videos can appear in others' Radar as well. Is that okay?\n\nYou can change this setting later via 📡 Radar.", "uk": "📡 Радар працює в обидва боки — ви не лише отримуєте випадкові берпі, а й ваші відео можуть з'являтися в Радарі інших. Це нормально?\n\nЦе налаштування можна змінити пізніше через 📡 Радар.", "de": "📡 Radar funktioniert in beide Richtungen — du empfängst nicht nur zufällige Burpees, sondern deine Videos können auch im Radar anderer erscheinen. Ist das okay?\n\nDu kannst diese Einstellung später über 📡 Radar ändern."},
    "radar_off_msg": {"en": "📡 Radar off.", "uk": "📡 Радар вимкнено.", "de": "📡 Radar aus."},
    "radar_set_msg": {"en": "📡 Radar set to {label} — you'll receive a random burpee from outside your sweat list.", "uk": "📡 Радар: {label} — ви отримуватимете випадкове берпі за межами вашого списку.", "de": "📡 Radar: {label} — du bekommst einen zufälligen Burpee von außerhalb deiner Liste."},
    "radar_send_ok_yes": {"en": "✅ Got it — your videos can be shared via Radar.", "uk": "✅ Зрозуміло — вашими відео можна ділитися через Радар.", "de": "✅ Verstanden — deine Videos können über Radar geteilt werden."},
    "radar_send_ok_no": {"en": "🔒 Got it — your videos stay within your crew.", "uk": "🔒 Зрозуміло — ваші відео лишаються у вашому гурті.", "de": "🔒 Verstanden — deine Videos bleiben in deiner Crew."},
    "radar_recv_first_once": {"en": "📡 {name}: {reps} reps\nYou're getting this because your radar is on — a burpee from outside your crew. According to your radar settings you'll get 1 burpee bubble, just once. Use /radar to adjust frequency.", "uk": "📡 {name}: {reps} повторень\nВи отримали це, бо ваш радар увімкнено — берпі з-поза вашого гурту. За вашими налаштуваннями ви отримаєте 1 відео, лише раз. Використайте /radar, щоб змінити частоту.", "de": "📡 {name}: {reps} Wdh.\nDu bekommst das, weil dein Radar an ist — ein Burpee von außerhalb deiner Crew. Laut deinen Einstellungen bekommst du 1 Video, nur einmal. Nutze /radar, um die Häufigkeit zu ändern."},
    "radar_recv_first_period": {"en": "📡 {name}: {reps} reps\nYou're getting this because your radar is on — a burpee from outside your crew. According to your radar settings you will get 1 random burpee bubble {period}. Use /radar to adjust frequency.", "uk": "📡 {name}: {reps} повторень\nВи отримали це, бо ваш радар увімкнено — берпі з-поза вашого гурту. За вашими налаштуваннями ви отримуватимете 1 випадкове відео {period}. Використайте /radar, щоб змінити частоту.", "de": "📡 {name}: {reps} Wdh.\nDu bekommst das, weil dein Radar an ist — ein Burpee von außerhalb deiner Crew. Laut deinen Einstellungen bekommst du 1 zufälliges Video {period}. Nutze /radar, um die Häufigkeit zu ändern."},
    "radar_recv_repeat": {"en": "📡 {name}: {reps} reps\nYour Radar detected some burpee activity from someone outside your crew.", "uk": "📡 {name}: {reps} повторень\nВаш Радар виявив активність берпі від когось поза вашим гуртом.", "de": "📡 {name}: {reps} Wdh.\nDein Radar hat Burpee-Aktivität von jemandem außerhalb deiner Crew erkannt."},
    # ── Pause ──
    "pause_menu_active": {"en": "⏸️ Paused until {until} UTC.\n\nExtend or resume:", "uk": "⏸️ Призупинено до {until} UTC.\n\nПродовжити або відновити:", "de": "⏸️ Pausiert bis {until} UTC.\n\nVerlängern oder fortsetzen:"},
    "pause_menu_inactive": {"en": "⏸️ Pause notifications — no sweat forwards or radar while paused.\n\nPause for:", "uk": "⏸️ Призупинити сповіщення — жодних надсилань чи радару під час паузи.\n\nПризупинити на:", "de": "⏸️ Benachrichtigungen pausieren — keine Weiterleitungen oder Radar während der Pause.\n\nPausieren für:"},
    "pause_resumed": {"en": "▶️ Notifications resumed.", "uk": "▶️ Сповіщення відновлено.", "de": "▶️ Benachrichtigungen fortgesetzt."},
    "pause_set": {"en": "⏸️ Paused until {until} — no sweat forwards or radar until then.", "uk": "⏸️ Призупинено до {until} — жодних надсилань чи радару до того часу.", "de": "⏸️ Pausiert bis {until} — bis dahin keine Weiterleitungen oder Radar."},
    # ── Sweat ──
    "sweat_menu": {"en": "🤝 Your sweat crew gets every video you log — and you get theirs.\nRadar is for strangers. Sweat is for your people.\n\nSweating with: {partners}\n\nType a name to add, mute, or remove:", "uk": "🤝 Ваш гурт отримує кожне ваше відео — а ви їхні.\nРадар — для незнайомців. Спільний піт — для своїх.\n\nСпільний піт з: {partners}\n\nНапишіть ім'я, щоб додати, приглушити або прибрати:", "de": "🤝 Deine Crew bekommt jedes deiner Videos — und du ihre.\nRadar ist für Fremde. Schwitzen ist für deine Leute.\n\nSchwitzt mit: {partners}\n\nGib einen Namen ein zum Hinzufügen, Stummschalten oder Entfernen:"},
    "sweat_nobody": {"en": "nobody yet", "uk": "поки нікого", "de": "noch niemand"},
    "sweat_name_not_found": {"en": "No user named \"{name}\" found. Try again or send /sweat to see current list.", "uk": "Користувача з ім'ям «{name}» не знайдено. Спробуйте ще або надішліть /sweat, щоб побачити список.", "de": "Kein Nutzer namens „{name}“ gefunden. Versuch es erneut oder sende /sweat, um die Liste zu sehen."},
    "sweat_already_muted_until": {"en": " (muted until {until})", "uk": " (без звуку до {until})", "de": " (stumm bis {until})"},
    "sweat_already_in_list": {"en": "{name} is in your sweat list{status}. What would you like to do?", "uk": "{name} у вашому списку{status}. Що бажаєте зробити?", "de": "{name} ist in deiner Liste{status}. Was möchtest du tun?"},
    "sweat_added_notify": {"en": "Added {name} to your sweat list 🤝\n\nNotify {name}?", "uk": "{name} додано до вашого списку 🤝\n\nПовідомити {name}?", "de": "{name} zu deiner Liste hinzugefügt 🤝\n\n{name} benachrichtigen?"},
    "sweat_summary": {"en": "{greet}sharing to: {summary}\n\nNow send your burpee video 💪", "uk": "{greet}ділитесь із: {summary}\n\nТепер надішліть своє відео берпі 💪", "de": "{greet}geteilt mit: {summary}\n\nJetzt schick dein Burpee-Video 💪"},
    "follow_summary": {"en": "{greet}following: {summary}", "uk": "{greet}стежите за: {summary}", "de": "{greet}folgst: {summary}"},
    "summary_anyone": {"en": "anyone", "uk": "будь-ким", "de": "jedem"},
    "summary_nobody": {"en": "nobody", "uk": "ніким", "de": "niemandem"},
    "cancelled": {"en": "Cancelled.", "uk": "Скасовано.", "de": "Abgebrochen."},
    "sweat_unmuted": {"en": "▶️ {name} unmuted — you'll receive their updates again.", "uk": "▶️ Звук {name} увімкнено — ви знову отримуватимете їхні оновлення.", "de": "▶️ {name} nicht mehr stumm — du bekommst wieder ihre Updates."},
    "sweat_muted": {"en": "🔕 {name} muted until {until} — still in your sweat list.", "uk": "🔕 {name} без звуку до {until} — досі у вашому списку.", "de": "🔕 {name} stumm bis {until} — bleibt in deiner Liste."},
    "sweat_removed": {"en": "Removed {name} from your sweat list.", "uk": "{name} прибрано з вашого списку.", "de": "{name} aus deiner Liste entfernt."},
    "sweat_added_you": {"en": "🤝 {name} added you to their sweat list!", "uk": "🤝 {name} додав(-ла) вас до свого списку!", "de": "🤝 {name} hat dich zu seiner Liste hinzugefügt!"},
    "sweat_added_you_ask": {"en": "🤝 {name} added you to their sweat list!\n\nAdd {name} to your sweat list?", "uk": "🤝 {name} додав(-ла) вас до свого списку!\n\nДодати {name} до свого списку?", "de": "🤝 {name} hat dich zu seiner Liste hinzugefügt!\n\n{name} zu deiner Liste hinzufügen?"},
    "sweat_added_back": {"en": "✓ Added {name} to your sweat list 🤝", "uk": "✓ {name} додано до вашого списку 🤝", "de": "✓ {name} zu deiner Liste hinzugefügt 🤝"},
    "sweat_added_you_too": {"en": "🤝 {name} added you to their sweat list too!", "uk": "🤝 {name} теж додав(-ла) вас до свого списку!", "de": "🤝 {name} hat dich ebenfalls hinzugefügt!"},
    # ── Milestone / monthly summary ──
    "milestone": {"en": "🎉 Great job, {name}! You've already done {milestone} burpees this month!\nNext milestone: {next_m} 💪", "uk": "🎉 Чудова робота, {name}! Ви вже зробили {milestone} берпі цього місяця!\nНаступна ціль: {next_m} 💪", "de": "🎉 Super, {name}! Du hast diesen Monat schon {milestone} Burpees gemacht!\nNächstes Ziel: {next_m} 💪"},
    "summary_header": {"en": "📅 {month} Summary, {name}!", "uk": "📅 Підсумок за {month}, {name}!", "de": "📅 {month}-Zusammenfassung, {name}!"},
    "summary_workouts": {"en": "💪 Workouts: {count}  (consistency: {pct}%)", "uk": "💪 Тренувань: {count}  (регулярність: {pct}%)", "de": "💪 Workouts: {count}  (Konstanz: {pct}%)"},
    "summary_total": {"en": "📊 Total reps: {total}  (avg {avg})", "uk": "📊 Усього повторень: {total}  (сер. {avg})", "de": "📊 Wiederholungen gesamt: {total}  (Ø {avg})"},
    "summary_best": {"en": "🏆 Best day: {reps} reps on {day}", "uk": "🏆 Найкращий день: {reps} повторень {day}", "de": "🏆 Bester Tag: {reps} Wdh. am {day}"},
    "summary_vs": {"en": "📈 vs {month}: {arrow} {pct}%  ({total} reps last month)", "uk": "📈 порівняно з {month}: {arrow} {pct}%  ({total} повторень торік. місяця)", "de": "📈 vs. {month}: {arrow} {pct}%  ({total} Wdh. letzten Monat)"},
    "summary_streak": {"en": "🔥 Current streak: {streak} days — keep it going!", "uk": "🔥 Поточна серія: {streak} днів — так тримати!", "de": "🔥 Aktuelle Serie: {streak} Tage — weiter so!"},
    "summary_milestones": {"en": "🏅 Milestones: {list}", "uk": "🏅 Досягнення: {list}", "de": "🏅 Meilensteine: {list}"},
}


# Localized main-keyboard button label → canonical slash command. Built once at
# import; lets a tap on a translated reply-keyboard button route like a command.
def _build_button_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key, cmd in (("btn_sweat", "/sweat"), ("btn_radar", "/radar"),
                     ("btn_pause", "/pause"), ("btn_info", "/info")):
        for lang in _SUPPORTED_LANGS:
            mapping[_STRINGS[key][lang]] = cmd
    return mapping


_BUTTON_TO_CMD = _build_button_map()

# Localized full month names (index 1..12), for summaries.
_MONTHS = {
    "en": ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "uk": ["", "січень", "лютий", "березень", "квітень", "травень", "червень", "липень", "серпень", "вересень", "жовтень", "листопад", "грудень"],
    "de": ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
}


def _month_name(month_num: int, lang: str = "en") -> str:
    return _MONTHS.get(lang, _MONTHS["en"])[month_num]


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


def _share_keyboard(cur, tg_id: int, lang: str = "en") -> dict:
    stored = _get_share_set(cur, tg_id)
    has_all = "__all__" in stored
    others = _all_other_names(cur, tg_id)
    anyone = _t("kb_anyone", lang)
    rows = []
    rows.append([{"text": ("✓ " if has_all else "") + anyone, "callback_data": "share:__all__"}])
    for p in others:
        label = f"✓ {p}" if (has_all or p in stored) else p
        rows.append([{"text": label, "callback_data": f"share:{p}"}])
    rows.append([{"text": _t("kb_done", lang), "callback_data": "share:done"}])
    return {"inline_keyboard": rows}


# ── Follow (accept from) ─────────────────────────────────────────────────────

def _get_follow_set(cur, tg_id: int) -> set[str]:
    cur.execute(
        "SELECT receive_participant FROM telegram_bot_receive WHERE telegram_user_id = %s",
        (tg_id,),
    )
    return {r["receive_participant"] for r in cur.fetchall()}


def _main_kb(lang: str = "en") -> dict:
    return {
        "keyboard": [
            [{"text": _t("btn_sweat", lang)}, {"text": _t("btn_radar", lang)}],
            [{"text": _t("btn_pause", lang)}, {"text": _t("btn_info", lang)}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def _pause_keyboard(is_paused: bool, lang: str = "en") -> dict:
    rows = [
        [{"text": _t("pause_1d", lang), "callback_data": "pause:1d"}],
        [{"text": _t("pause_1w", lang), "callback_data": "pause:1w"}],
        [{"text": _t("pause_1m", lang), "callback_data": "pause:1m"}],
    ]
    if is_paused:
        rows.append([{"text": _t("pause_resume", lang), "callback_data": "pause:resume"}])
    return {"inline_keyboard": rows}

_REPS_RE = _re.compile(r"^(\d+)\s*(.*)", _re.DOTALL)


def _parse_reps(text: str) -> tuple[int, str] | None:
    m = _REPS_RE.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip()


_RADAR_FREQS = ["daily", "weekly", "monthly", "once", "never"]
_RADAR_LABEL_KEYS = {"daily": "radar_daily", "weekly": "radar_weekly", "monthly": "radar_monthly", "once": "radar_once", "never": "radar_off"}
_RADAR_PERIOD_KEYS = {"daily": "radar_period_daily", "weekly": "radar_period_weekly", "monthly": "radar_period_monthly"}


def _radar_label(freq: str, lang: str = "en") -> str:
    return _t(_RADAR_LABEL_KEYS.get(freq, "radar_off"), lang)


def _radar_keyboard(current: str, lang: str = "en", radar_send: bool | None = None) -> dict:
    rows = []
    for freq in _RADAR_FREQS:
        label = ("✓ " if freq == current else "") + _radar_label(freq, lang)
        rows.append([{"text": label, "callback_data": f"radar:{freq}"}])
    if radar_send is not None:
        rows.append([
            {"text": ("✓ " if radar_send else "") + _t("radar_share_on", lang), "callback_data": "radar_send_toggle:on"},
            {"text": ("✓ " if not radar_send else "") + _t("radar_share_off", lang), "callback_data": "radar_send_toggle:off"},
        ])
    return {"inline_keyboard": rows}


def _radar_send_kb(lang: str = "en") -> dict:
    return {"inline_keyboard": [
        [{"text": _t("radar_send_yes", lang), "callback_data": "radar_send:yes"}],
        [{"text": _t("radar_send_no", lang), "callback_data": "radar_send:no"}],
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


def _sweat_manage_keyboard(name: str, lang: str = "en", muted_until=None) -> dict:
    rows = []
    if muted_until:
        until_str = muted_until.strftime("%b %d")
        rows.append([{"text": _t("sweat_unmute_btn", lang, until=until_str), "callback_data": f"sweat_manage:unmute:{name}"}])
    rows.append([
        {"text": _t("sweat_mute_1d_btn", lang), "callback_data": f"sweat_manage:mute_1d:{name}"},
        {"text": _t("sweat_mute_1w_btn", lang), "callback_data": f"sweat_manage:mute_1w:{name}"},
        {"text": _t("sweat_mute_1m_btn", lang), "callback_data": f"sweat_manage:mute_1m:{name}"},
    ])
    rows.append([{"text": _t("sweat_remove_btn", lang), "callback_data": f"sweat_manage:remove:{name}"}])
    rows.append([{"text": _t("kb_cancel", lang), "callback_data": "sweat_manage:cancel"}])
    return {"inline_keyboard": rows}


def _follow_keyboard(cur, tg_id: int, lang: str = "en") -> dict:
    stored = _get_follow_set(cur, tg_id)
    has_all = "__all__" in stored
    others = _all_other_names(cur, tg_id)
    anyone = _t("kb_anyone", lang)
    rows = []
    rows.append([{"text": ("✓ " if has_all else "") + anyone, "callback_data": "follow:__all__"}])
    for p in others:
        label = f"✓ {p}" if (has_all or p in stored) else p
        rows.append([{"text": label, "callback_data": f"follow:{p}"}])
    rows.append([{"text": _t("kb_done", lang), "callback_data": "follow:done"}])
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
    sender_lang = _user_lang(cur, tg_id)
    targets = _get_share_chats(cur, tg_id)
    conn.commit()
    for to_chat_id, name in targets:
        if message_id:
            _forward(from_chat_id, message_id, to_chat_id)
        recip_lang = _norm_lang(_lang_for_name(cur, name))
        crew_msg = f"{participant}: {_t('reps_short', recip_lang, reps=reps)}"
        if comment:
            crew_msg += f"\n{comment}"
        _send(to_chat_id, crew_msg)
    confirm = (_t("confirm_reps_comment", sender_lang, reps=reps, comment=comment)
               if comment else _t("confirm_reps", sender_lang, reps=reps))
    if targets:
        forwarded_to = ", ".join(n for _, n in targets)
        _send(from_chat_id, _t("forwarded_to", sender_lang, confirm=confirm, names=forwarded_to), reply_markup=_main_kb(sender_lang))
        _log(f"💪 Video logged\n👤 {participant}: {reps} reps\n📤 → {forwarded_to}")
    else:
        _send(from_chat_id, _t("confirm_logged", sender_lang, confirm=confirm), reply_markup=_main_kb(sender_lang))
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

    # ── Milestones: cheer immediately if a monthly threshold is crossed ──
    _check_milestone_for_user(cur, conn, tg_id, participant)


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
        days_ago = 0
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
        user_stats.append((streak, -days_ago if streak == 0 else 0, line))

    user_stats.sort(key=lambda x: (x[0], x[1]), reverse=True)
    lines = [f"📊 Burpee Report — {today.strftime('%B %d')}\n"] + [line for _, _, line in user_stats]

    _tg("sendMessage", {"chat_id": int(_REPORT_CHAT_ID), "text": "\n".join(lines)})
    _log(f"📊 Daily report sent to channel")


def _milestone_step(avg_reps: float) -> int:
    if avg_reps < 15:
        return 50
    if avg_reps < 35:
        return 100
    return 200


def _check_milestone_for_user(cur, conn, tg_id: int, participant: str) -> None:
    """Fire a milestone cheer immediately after a workout is logged, if one is due."""
    import math
    today = date.today()
    month_start = today.replace(day=1)
    ten_days_ago = today - timedelta(days=10)

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM burpee_entries "
        "WHERE participant = %s AND entry_date >= %s",
        (participant, ten_days_ago),
    )
    if cur.fetchone()["cnt"] < 3:
        return

    cur.execute(
        "SELECT reps FROM burpee_entries WHERE participant = %s AND entry_date >= %s",
        (participant, month_start),
    )
    month_reps = [r["reps"] for r in cur.fetchall()]
    if not month_reps:
        return

    total = sum(month_reps)
    avg = total / len(month_reps)
    step = _milestone_step(avg)
    first = math.ceil(avg * 5 / step) * step

    crossed = []
    m = first
    while m <= total:
        crossed.append(m)
        m += step
    if not crossed:
        return

    cur.execute(
        "SELECT milestone_reps FROM milestone_notifications WHERE participant = %s AND month = %s",
        (participant, month_start),
    )
    already_sent = {r["milestone_reps"] for r in cur.fetchall()}

    new_milestones = [m for m in crossed if m not in already_sent]
    if not new_milestones:
        return

    milestone = max(new_milestones)
    next_m = milestone + step
    lang = _user_lang(cur, tg_id)
    text = _t("milestone", lang, name=participant, milestone=milestone, next_m=next_m)
    _tg("sendMessage", {"chat_id": tg_id, "text": text})
    _log(f"🏅 Milestone {milestone} sent to {participant}")

    for m in new_milestones:
        cur.execute(
            "INSERT INTO milestone_notifications (participant, month, milestone_reps) "
            "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (participant, month_start, m),
        )
    conn.commit()


def check_milestones(conn) -> None:
    """Cron fallback: sweep all frequent users for unclaimed milestones."""
    cur = conn.cursor()
    ten_days_ago = date.today() - timedelta(days=10)
    cur.execute(
        "SELECT u.telegram_user_id, u.participant_name "
        "FROM telegram_bot_users u "
        "WHERE (SELECT COUNT(*) FROM burpee_entries e "
        "       WHERE e.participant = u.participant_name AND e.entry_date >= %s) >= 3",
        (ten_days_ago,),
    )
    for user in cur.fetchall():
        _check_milestone_for_user(cur, conn, user["telegram_user_id"], user["participant_name"])


def send_monthly_summaries(conn) -> None:
    """On the 1st of each month, send each user a summary of their previous month."""
    import math as _math
    import calendar
    cur = conn.cursor()
    today = date.today()
    if today.day != 1:
        return

    prev_month_end = today - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    # Dedup — only send once per month
    job_key = f"monthly_summary_{prev_month_start.strftime('%Y-%m')}"
    cur.execute(
        "INSERT INTO cron_log (job_name, run_date) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING RETURNING job_name",
        (job_key, today),
    )
    if not cur.fetchone():
        return
    conn.commit()

    # Previous-month entries for all users who logged at least once
    cur.execute(
        "SELECT u.telegram_user_id, u.participant_name, u.chat_id, u.language_code "
        "FROM telegram_bot_users u "
        "WHERE EXISTS (SELECT 1 FROM burpee_entries e "
        "              WHERE e.participant = u.participant_name "
        "              AND e.entry_date >= %s AND e.entry_date <= %s)",
        (prev_month_start, prev_month_end),
    )
    users = cur.fetchall()

    days_in_month = calendar.monthrange(prev_month_start.year, prev_month_start.month)[1]

    for user in users:
        tg_id = user["telegram_user_id"]
        name = user["participant_name"]
        chat_id = user["chat_id"]
        lang = _norm_lang(user["language_code"])

        cur.execute(
            "SELECT entry_date, reps FROM burpee_entries "
            "WHERE participant = %s AND entry_date >= %s AND entry_date <= %s "
            "ORDER BY entry_date",
            (name, prev_month_start, prev_month_end),
        )
        entries = cur.fetchall()
        if not entries:
            continue

        total = sum(r["reps"] for r in entries)
        count = len(entries)
        avg = total / count
        best = max(entries, key=lambda r: r["reps"])
        consistency_pct = round(count / days_in_month * 100)

        # Streak at end of prev month (entries already ASC, need DESC for _compute_streak)
        entries_desc = list(reversed(entries))
        streak, _, _ = _compute_streak(entries_desc)

        # Previous-previous month for comparison
        pprev_end = prev_month_start - timedelta(days=1)
        pprev_start = pprev_end.replace(day=1)
        cur.execute(
            "SELECT COALESCE(SUM(reps), 0) AS total FROM burpee_entries "
            "WHERE participant = %s AND entry_date >= %s AND entry_date <= %s",
            (name, pprev_start, pprev_end),
        )
        prev_total = cur.fetchone()["total"] or 0

        # Milestones hit that month
        cur.execute(
            "SELECT milestone_reps FROM milestone_notifications "
            "WHERE participant = %s AND month = %s ORDER BY milestone_reps",
            (name, prev_month_start),
        )
        milestones = [r["milestone_reps"] for r in cur.fetchall()]

        # Build message
        best_day = f"{_month_name(best['entry_date'].month, lang)} {best['entry_date'].day}"
        lines = [_t("summary_header", lang, month=_month_name(prev_month_start.month, lang), name=name) + "\n"]
        lines.append(_t("summary_workouts", lang, count=count, pct=consistency_pct))
        lines.append(_t("summary_total", lang, total=total, avg=round(avg)))
        lines.append(_t("summary_best", lang, reps=best["reps"], day=best_day))
        if prev_total > 0:
            delta = round((total - prev_total) / prev_total * 100)
            arrow = "↑" if delta >= 0 else "↓"
            lines.append(_t("summary_vs", lang, month=_month_name(pprev_start.month, lang), arrow=arrow, pct=abs(delta), total=prev_total))
        if streak > 0:
            lines.append(_t("summary_streak", lang, streak=streak))
        if milestones:
            lines.append(_t("summary_milestones", lang, list=", ".join(str(m) for m in milestones)))

        _tg("sendMessage", {"chat_id": chat_id, "text": "\n".join(lines)})
        _log(f"📅 Monthly summary sent to {name}")


def _store_or_bind_video(cur, conn, tg_id: int, participant: str, chat_id: int, message_id: int) -> None:
    """Store a video as pending (ask for reps), or bind it to reps logged within the last hour."""
    # Upsert the video WITHOUT touching reps, so reps that arrived first (or land
    # concurrently) are preserved. RETURNING tells us whether fresh reps are already
    # waiting — if so, pair them and forward instead of asking again. Video notes
    # can't carry a caption, so this is the only chance to reunite them.
    cur.execute(
        "INSERT INTO telegram_bot_pending (telegram_user_id, chat_id, message_id, reps) "
        "VALUES (%s, %s, %s, NULL) ON CONFLICT (telegram_user_id) "
        "DO UPDATE SET message_id = EXCLUDED.message_id, chat_id = EXCLUDED.chat_id "
        "RETURNING reps, comment, (created_at > NOW() - INTERVAL '1 hour') AS reps_fresh",
        (tg_id, chat_id, message_id),
    )
    row = cur.fetchone()
    if row and row["reps"] is not None and row["reps_fresh"]:
        reps = row["reps"]
        comment = row["comment"]
        cur.execute("DELETE FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
        _do_forward(cur, conn, tg_id, participant, chat_id, message_id, reps, comment)
    else:
        conn.commit()
        _send(chat_id, _t("how_many_reps", _user_lang(cur, tg_id), greet=_greet(cur, tg_id, participant)))


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
            "SELECT telegram_user_id, chat_id, participant_name, radar_freq, radar_last_received, paused_until, language_code "
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

            rlang = _norm_lang(recipient.get("language_code"))
            is_first = recipient["radar_last_received"] is None
            if is_first:
                if freq == "once":
                    explanation = _t("radar_recv_first_once", rlang,
                                     name=best["participant_name"], reps=best["reps"])
                else:
                    period = _t(_RADAR_PERIOD_KEYS.get(freq, "radar_period_daily"), rlang)
                    explanation = _t("radar_recv_first_period", rlang,
                                     name=best["participant_name"], reps=best["reps"], period=period)
            else:
                explanation = _t("radar_recv_repeat", rlang,
                                 name=best["participant_name"], reps=best["reps"])

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
        lang = _norm_lang(cq["from"].get("language_code"))

        # Exercise queue callbacks (single admin user) — route before burpee logic
        if data.startswith("ex:"):
            _ex_admin = os.environ.get("ADMIN_TG_ID", "")
            if _ex_admin and str(tg_id) == _ex_admin:
                from phase_app.exercise_bot import handle_exercise_callback
                handle_exercise_callback(cur, conn, tg_id, chat_id, msg_id, data)
            return

        participant = _lookup_user(cur, tg_id)
        if not participant:
            return

        # Share callbacks
        if data.startswith("share:"):
            target = data[len("share:"):]
            if target == "done":
                stored = _get_share_set(cur, tg_id)
                has_all = "__all__" in stored
                summary = _t("summary_anyone", lang) if has_all else (", ".join(sorted(stored - {"__all__"})) or _t("summary_nobody", lang))
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, _t("sweat_summary", lang, greet=_greet(cur, tg_id, participant), summary=summary), reply_markup=_main_kb(lang))
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
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _share_keyboard(cur, tg_id, lang)})
            return

        # Follow callbacks
        if data.startswith("follow:"):
            target = data[len("follow:"):]
            if target == "done":
                stored = _get_follow_set(cur, tg_id)
                has_all = "__all__" in stored
                summary = _t("summary_anyone", lang) if has_all else (", ".join(sorted(stored - {"__all__"})) or _t("summary_nobody", lang))
                _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
                _send(chat_id, _t("follow_summary", lang, greet=_greet(cur, tg_id, participant), summary=summary), reply_markup=_main_kb(lang))
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
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _follow_keyboard(cur, tg_id, lang)})
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
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _radar_keyboard(freq, lang, radar_send=radar_send if show_toggle else None)})
            if setup_mode or needs_send_question:
                # Next: ask about sending
                _send(chat_id, _t("radar_ask_send", lang), reply_markup=_radar_send_kb(lang))
            else:
                label = _radar_label(freq, lang)
                if freq == "never":
                    _send(chat_id, _t("radar_off_msg", lang), reply_markup=_main_kb(lang))
                else:
                    _send(chat_id, _t("radar_set_msg", lang, label=label.lower()), reply_markup=_main_kb(lang))
                _log(f"📡 Radar set\n👤 {participant} → {_radar_label(freq, 'en')}")
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
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": _radar_keyboard(current_freq, lang, radar_send=new_send)})
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
                _send(chat_id, _t("radar_send_ok_yes", lang), reply_markup=_main_kb(lang))
            else:
                _send(chat_id, _t("radar_send_ok_no", lang), reply_markup=_main_kb(lang))
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
                _send(chat_id, _t("pause_resumed", lang), reply_markup=_main_kb(lang))
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
                _send(chat_id, _t("pause_set", lang, until=until_str), reply_markup=_main_kb(lang))
                _log(f"⏸️ Paused\n👤 {participant} → {label}")
            return

        # Sweat notify callbacks
        if data.startswith("sweat_notify:"):
            _tg("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": msg_id, "reply_markup": {}})
            parts = data.split(":", 2)
            if parts[1] == "yes" and len(parts) == 3:
                target_name = parts[2]
                cur.execute("SELECT chat_id, telegram_user_id, language_code FROM telegram_bot_users WHERE participant_name = %s", (target_name,))
                target_row = cur.fetchone()
                if target_row:
                    tlang = _norm_lang(target_row["language_code"])
                    cur.execute(
                        "SELECT 1 FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s "
                        "UNION "
                        "SELECT 1 FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s",
                        (target_row["telegram_user_id"], participant, target_row["telegram_user_id"], participant),
                    )
                    already_connected = cur.fetchone() is not None
                    if already_connected:
                        _send(target_row["chat_id"], _t("sweat_added_you", tlang, name=participant))
                    else:
                        _send(target_row["chat_id"],
                            _t("sweat_added_you_ask", tlang, name=participant),
                            reply_markup={"inline_keyboard": [[
                                {"text": _t("kb_yes", tlang), "callback_data": f"sweat_add_back:yes:{participant}"},
                                {"text": _t("kb_no", tlang),  "callback_data": "sweat_add_back:no"},
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
                _send(chat_id, _t("cancelled", lang), reply_markup=_main_kb(lang))
                return
            now = datetime.now(timezone.utc)
            if action == "unmute":
                cur.execute(
                    "DELETE FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s",
                    (tg_id, name),
                )
                conn.commit()
                _send(chat_id, _t("sweat_unmuted", lang, name=name), reply_markup=_main_kb(lang))
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
                _send(chat_id, _t("sweat_muted", lang, name=name, until=until.strftime('%b %d')), reply_markup=_main_kb(lang))
                _log(f"🔕 Sweat muted\n👤 {participant} muted {name} for {label}")
            elif action == "remove":
                cur.execute("DELETE FROM telegram_bot_notify WHERE telegram_user_id = %s AND notify_participant = %s", (tg_id, name))
                cur.execute("DELETE FROM telegram_bot_receive WHERE telegram_user_id = %s AND receive_participant = %s", (tg_id, name))
                cur.execute("DELETE FROM sweat_mute WHERE telegram_user_id = %s AND muted_participant = %s", (tg_id, name))
                conn.commit()
                _send(chat_id, _t("sweat_removed", lang, name=name), reply_markup=_main_kb(lang))
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
                _send(chat_id, _t("sweat_added_back", lang, name=adder_name), reply_markup=_main_kb(lang))
                cur.execute("SELECT chat_id, language_code FROM telegram_bot_users WHERE participant_name = %s", (adder_name,))
                adder_row = cur.fetchone()
                if adder_row:
                    _send(adder_row["chat_id"], _t("sweat_added_you_too", _norm_lang(adder_row["language_code"]), name=participant))
                _log(f"🤝 Sweat add-back\n👤 {participant} → {adder_name}")
            return

        return

    is_edit = "edited_message" in body
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return

    tg_id: int = msg["from"]["id"]
    chat_id: int = msg["chat"]["id"]
    raw_lang: str | None = msg["from"].get("language_code")
    lang: str = _norm_lang(raw_lang)
    text: str = msg.get("text", "").strip()

    # Persist language_code and chat_id so they stay current
    cur.execute(
        "UPDATE telegram_bot_users SET language_code = %s, chat_id = %s WHERE telegram_user_id = %s",
        (raw_lang, chat_id, tg_id),
    )

    # Localized reply-keyboard button tap → canonical slash command
    if text in _BUTTON_TO_CMD:
        text = _BUTTON_TO_CMD[text]
    # Allow plain-text command names (e.g. "pause" → "/pause")
    if text.lower() in _COMMAND_ALIASES:
        text = "/" + text.lower()

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
                _send(chat_id, _t("reps_updated", lang, reps=_reps_e), reply_markup=_main_kb(lang))
        return

    # ── Exercise queue (single admin user) — route before burpee logic ───────
    _ex_admin = os.environ.get("ADMIN_TG_ID", "")
    if _ex_admin and str(tg_id) == _ex_admin:
        from phase_app.exercise_bot import maybe_handle_exercise
        if maybe_handle_exercise(cur, conn, tg_id, chat_id, text):
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
        link_line = _t("app_link_line", lang, token=token_val) if token_val else _t("app_link_none", lang)
        _log(f"ℹ️ Info viewed\n👤 {info_name or f'unregistered (tg:{tg_id})'}")
        _send(chat_id, _t("info_body", lang, link_line=link_line), reply_markup=_main_kb(lang))
        return

    # ── /start ───────────────────────────────────────────────────────────────
    if text.startswith("/start"):
        existing = _lookup_user(cur, tg_id)
        if existing:
            cur.execute("SELECT token FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
            row = cur.fetchone()
            token_val = row["token"] if row and row["token"] else None
            app_url = f"https://phase-app-yf5x.vercel.app/?token={token_val}" if token_val else "(no link yet)"
            _send(chat_id, _t("already_registered", lang, name=existing, url=app_url), reply_markup=_main_kb(lang))
            return
        _set_state(cur, tg_id, "awaiting_name")
        conn.commit()
        _send(chat_id, _t("start_body", lang))
        return

    participant = _lookup_user(cur, tg_id)
    state = _get_state(cur, tg_id)

    # ── /rename ──────────────────────────────────────────────────────────────
    if text.startswith("/rename") or text == "✏️ Rename":
        if not participant:
            _send(chat_id, _t("register_first", lang))
            return
        _set_state(cur, tg_id, "awaiting_rename")
        conn.commit()
        _send(chat_id, _t("ask_rename", lang, greet=_greet(cur, tg_id, participant)))
        return

    # ── /secret ──────────────────────────────────────────────────────────────
    if text.startswith("/secret") or text == "🔑 Secret":
        if not participant:
            _send(chat_id, _t("register_first", lang))
            return
        _set_state(cur, tg_id, "awaiting_secret_update")
        conn.commit()
        _send(chat_id, _t("ask_secret", lang))
        return

    # Any command or main keyboard button cancels a pending state
    if text.startswith("/") and state:
        _clear_state(cur, tg_id)
        conn.commit()
        state = None

    # ── Awaiting name input (registration or rename) ─────────────────────────
    if state in ("awaiting_name", "awaiting_rename") and text:
        name = text.strip()
        if len(name) > 32 or not name.replace(" ", "").isalpha():
            _send(chat_id, _t("letters_32", lang))
            return
        cur.execute(
            "SELECT 1 FROM telegram_bot_users WHERE LOWER(participant_name) = LOWER(%s) AND telegram_user_id != %s",
            (name, tg_id),
        )
        if cur.fetchone():
            _send(chat_id, _t("name_taken", lang, name=name))
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
            _send(chat_id, _t("renamed_done", lang, name=name, url=app_url), reply_markup=_main_kb(lang))
        else:
            # New registration — store name in state, ask for secret next
            _set_state(cur, tg_id, f"awaiting_secret:{name}")
            conn.commit()
            _send(chat_id, _t("ask_secret", lang))
        return

    # ── Awaiting secret (new registration) ───────────────────────────────────
    if state and state.startswith("awaiting_secret:") and text:
        name = state[len("awaiting_secret:"):]
        secret = text.strip()
        if len(secret) > 64 or not secret.replace(" ", "").replace("'", "").replace("-", "").isalpha():
            _send(chat_id, _t("letters_64", lang))
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
        _send(chat_id, _t("welcome_registered", lang, name=name, url=app_url), reply_markup=_main_kb(lang))
        # Kick off radar setup
        _set_state(cur, tg_id, "awaiting_radar_freq_setup")
        conn.commit()
        _send(chat_id, _t("radar_setup_freq", lang), reply_markup=_radar_keyboard("never", lang))
        return

    # ── Awaiting secret update (existing user via /secret) ───────────────────
    if state == "awaiting_secret_update" and text:
        secret = text.strip()
        if len(secret) > 64 or not secret.replace(" ", "").replace("'", "").replace("-", "").isalpha():
            _send(chat_id, _t("letters_64", lang))
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
        _send(chat_id, _t("secret_done", lang, url=app_url), reply_markup=_main_kb(lang))
        return

    # ── /radar ───────────────────────────────────────────────────────────────
    if text.startswith("/radar") or text == "📡 Radar":
        if not participant:
            _send(chat_id, _t("register_first", lang))
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
        kb = _radar_keyboard(current, lang, radar_send=radar_send if radar_asked else None)
        _send(chat_id, _t("radar_menu", lang, current=_radar_label(current, lang)), reply_markup=kb)
        return

    # ── /pause ───────────────────────────────────────────────────────────────
    if text.startswith("/pause") or text == "⏸️ Pause":
        if not participant:
            _send(chat_id, _t("register_first", lang))
            return
        _log(f"⏸️ Pause menu opened\n👤 {participant}")
        cur.execute("SELECT paused_until FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        now = datetime.now(timezone.utc)
        paused_until = row["paused_until"] if row else None
        is_paused = bool(paused_until and paused_until > now)
        if is_paused:
            until_str = paused_until.strftime("%b %d, %H:%M")
            _send(chat_id, _t("pause_menu_active", lang, until=until_str), reply_markup=_pause_keyboard(True, lang))
        else:
            _send(chat_id, _t("pause_menu_inactive", lang), reply_markup=_pause_keyboard(False, lang))
        return

    # ── /sweat ───────────────────────────────────────────────────────────────
    if text.startswith("/sweat") or text == "🤝 Sweat with":
        if not participant:
            _send(chat_id, _t("register_first", lang))
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
            partner_list = _t("sweat_nobody", lang)
        _set_state(cur, tg_id, "awaiting_sweat_name")
        conn.commit()
        _send(chat_id, _t("sweat_menu", lang, partners=partner_list))
        return

    # ── Awaiting sweat partner name ───────────────────────────────────────────
    # Skip sweat name handling if text looks like reps and there's a pending video
    _pre_reps, _pre_comment = _parse_reps_comment(text) if text else (None, None)
    _has_pending_video = False
    if _pre_reps is not None and state == "awaiting_sweat_name":
        cur.execute("SELECT message_id FROM telegram_bot_pending WHERE telegram_user_id = %s AND message_id IS NOT NULL", (tg_id,))
        _has_pending_video = cur.fetchone() is not None

    if state == "awaiting_sweat_name" and text and not text.isdigit() and not _has_pending_video:
        name = text.strip()
        cur.execute(
            "SELECT participant_name FROM telegram_bot_users WHERE LOWER(participant_name) = LOWER(%s) AND telegram_user_id != %s",
            (name, tg_id),
        )
        row = cur.fetchone()
        if not row:
            _log(f"🔍 Sweat name not found\n👤 {participant} searched: {name}")
            _send(chat_id, _t("sweat_name_not_found", lang, name=name))
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
            status = _t("sweat_already_muted_until", lang, until=muted_until.strftime('%b %d')) if muted_until else ""
            _send(chat_id,
                _t("sweat_already_in_list", lang, name=matched_name, status=status),
                reply_markup=_sweat_manage_keyboard(matched_name, lang, muted_until),
            )
            return
        else:
            cur.execute("INSERT INTO telegram_bot_notify (telegram_user_id, notify_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, matched_name))
            cur.execute("INSERT INTO telegram_bot_receive (telegram_user_id, receive_participant) VALUES (%s, %s) ON CONFLICT DO NOTHING", (tg_id, matched_name))
            _log(f"🤝 Sweat added\n👤 {participant} → {matched_name}")
            _clear_state(cur, tg_id)
            conn.commit()
            _send(chat_id,
                _t("sweat_added_notify", lang, name=matched_name),
                reply_markup={"inline_keyboard": [
                    [{"text": _t("kb_yes", lang), "callback_data": f"sweat_notify:yes:{matched_name}"},
                     {"text": _t("kb_no", lang), "callback_data": "sweat_notify:no"}]
                ]},
            )
            return

    # ── Radar setup nudge (one-time for existing users) ─────────────────────
    _reps, _comment = _pre_reps, _pre_comment
    if participant and not state and text and _reps is None:
        cur.execute("SELECT radar_asked FROM telegram_bot_users WHERE telegram_user_id = %s", (tg_id,))
        row = cur.fetchone()
        if row and not row["radar_asked"]:
            _set_state(cur, tg_id, "awaiting_radar_freq_setup")
            conn.commit()
            _send(chat_id, _t("radar_nudge_freq", lang), reply_markup=_radar_keyboard("never", lang))
            return

    # ── Plain number (+ optional comment) → reps for pending video or bare log ─
    if _reps is not None and participant:
        reps, comment = _reps, _comment
        _log_entry(cur, participant, reps, comment)

        # Upsert the reps WITHOUT touching message_id, so a video that was stored
        # first (or lands concurrently) is preserved. RETURNING tells us whether a
        # video is already waiting — if so, forward now instead of asking twice.
        cur.execute(
            "INSERT INTO telegram_bot_pending (telegram_user_id, chat_id, message_id, reps, comment) "
            "VALUES (%s, %s, NULL, %s, %s) ON CONFLICT (telegram_user_id) "
            "DO UPDATE SET reps = EXCLUDED.reps, comment = EXCLUDED.comment, chat_id = EXCLUDED.chat_id, "
            "    created_at = NOW() "
            "RETURNING message_id",
            (tg_id, chat_id, reps, comment),
        )
        row = cur.fetchone()
        if row and row["message_id"] is not None:
            # Video was already pending → pair them and forward.
            pending_msg = row["message_id"]
            cur.execute("DELETE FROM telegram_bot_pending WHERE telegram_user_id = %s", (tg_id,))
            _do_forward(cur, conn, tg_id, participant, chat_id, pending_msg, reps, comment)
        else:
            # No video yet — keep reps pending so the next video (within 1h) binds.
            conn.commit()
            _log(f"💪 Reps logged (no video)\n👤 {participant}: {reps} reps")
            _send(chat_id, _t("reps_logged", lang, reps=reps), reply_markup=_main_kb(lang))
        return

    has_video = "video" in msg
    has_video_note = "video_note" in msg
    has_photo = "photo" in msg

    if not (has_video or has_video_note or has_photo):
        if text:
            name_label = participant or f"unregistered (tg:{tg_id})"
            _log(f"❓ Unhandled message\n👤 {name_label}\n💬 {text[:200]}")
            _send(chat_id, _t("unknown_msg", lang), reply_markup=_main_kb(lang))
        return

    if not participant:
        _send(chat_id, _t("register_first", lang))
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
