"""Reconstruct what happened in one person's Move chat over a period.

    python scripts/replay_move.py Олександра --from 2026-09-08
    python scripts/replay_move.py 479261580 --from 2026-09-01 --to 2026-09-09

What this can and cannot show, stated plainly, because a debugging tool that
overstates its evidence is worse than none:

  * Their actions — every message and every button — are complete. The bot
    already writes them to move_log_summary, one row per person per day, and
    those rows are kept after the Telegram message they were rendered into
    has gone.

  * The bot's own words are kept from 9 September 2026 (move_sent), so from
    that day a chat replays verbatim — sends, edits and deletions alike.
    Before it, only ids and kinds were recorded, and a reply shows as
    "← [confirm] #1398" rather than the sentence the person read. The replay
    log is swept after 30 days.

  * What the bot said is recoverable only where the content is itself data:
    the moves, the comments, the captions. Those are printed in full.

Times are Europe/Berlin, matching the trace the bot writes.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

BERLIN = timezone(timedelta(hours=2))

# What each move_forwards.kind is, in words. The bot names them for its own
# bookkeeping; a person reading a replay needs to know what they saw.
KIND = {
    "move":    "the move itself, copied into this chat",
    "confirm": "the ✓ confirmation",
    "own":     "the ⚙️ line under their own move",
    "talk":    "a comment thread",
    "ask":     "a prompt",
    "pick":    "the audience picker",
    "radar":   "a stranger's move, via radar",
}


def _resolve(cur, who: str) -> tuple[int, str]:
    if who.isdigit():
        cur.execute("SELECT telegram_user_id, participant_name FROM move_users "
                    "WHERE telegram_user_id = %s", (int(who),))
    else:
        cur.execute("SELECT telegram_user_id, participant_name FROM move_users "
                    "WHERE LOWER(participant_name) = LOWER(%s)", (who,))
    row = cur.fetchone()
    if not row:
        sys.exit(f'No Move user matching "{who}".')
    return row["telegram_user_id"], row["participant_name"] or "(unnamed)"


def _events(cur, tg_id: int, day: date) -> list[tuple[str, str, str]]:
    """(HH:MM, direction, text) for one day, in the order they happened."""
    out: list[tuple[str, str, str]] = []

    # 1. Their side, verbatim from the trace the bot kept.
    cur.execute("SELECT body FROM move_log_summary "
                "WHERE telegram_user_id = %s AND log_date = %s", (tg_id, day))
    row = cur.fetchone()
    for line in ((row or {}).get("body") or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        stamp, _, rest = line.partition("  ")
        out.append((stamp.strip(), "→", rest.strip()))

    lo = datetime.combine(day, datetime.min.time(), BERLIN)
    hi = lo + timedelta(days=1)

    # 1b. What the bot actually said, where it was kept.
    cur.execute("SELECT created_at, message_id, method, body FROM move_sent "
                "WHERE chat_id = %s AND created_at >= %s AND created_at < %s "
                "ORDER BY id", (tg_id, lo, hi))
    verbatim = set()
    for r in cur.fetchall():
        stamp = r["created_at"].astimezone(BERLIN).strftime("%H:%M")
        if r["method"] == "deleteMessage":
            out.append((stamp, "✂", f"removed #{r['message_id']}"))
            continue
        verbatim.add(r["message_id"])
        prefix = "edited " if r["method"] == "editMessageText" else ""
        body = (r["body"] or "").replace("\n", " ⏎ ")
        out.append((stamp, "←", f"{prefix}#{r['message_id']}: {body}"))

    # 2. Bot messages placed in this chat, by kind. Only where the text was not
    #    kept — after move_sent exists, printing both would say it all twice.
    cur.execute(
        "SELECT f.created_at, f.message_id, f.kind, f.entry_id, "
        "       u.participant_name AS author "
        "FROM move_forwards f "
        "LEFT JOIN move_entries e ON e.id = f.entry_id "
        "LEFT JOIN move_users u ON u.telegram_user_id = "
        "          COALESCE(f.from_tg_id, e.telegram_user_id) "
        "WHERE f.chat_id = %s AND f.created_at >= %s AND f.created_at < %s "
        "ORDER BY f.created_at", (tg_id, lo, hi))
    for r in cur.fetchall():
        if r["message_id"] in verbatim:
            continue
        what = KIND.get(r["kind"], r["kind"])
        by = f" from {r['author']}" if r["author"] and r["kind"] in ("move", "talk") else ""
        out.append((r["created_at"].astimezone(BERLIN).strftime("%H:%M"), "←",
                    f"[{r['kind']}] #{r['message_id']} — {what}{by}"))

    # 3. Scaffolding the sweep tracks. Overlaps (2) by message id, so anything
    #    already named above is dropped rather than shown twice.
    cur.execute("SELECT created_at, message_id FROM move_transient "
                "WHERE chat_id = %s AND created_at >= %s AND created_at < %s "
                "ORDER BY created_at", (tg_id, lo, hi))
    known = set(verbatim)
    for e in out:
        if "#" in e[2]:
            digits = e[2].split("#", 1)[1].split(" ")[0].rstrip(":")
            if digits.isdigit():
                known.add(int(digits))
    for r in cur.fetchall():
        if r["message_id"] in known:
            continue
        out.append((r["created_at"].astimezone(BERLIN).strftime("%H:%M"), "←",
                    f"[menu/prompt] #{r['message_id']} — text not kept"))

    # 4. The content that is data, printed in full.
    cur.execute("SELECT created_at, id, media_type, text_body, comment, radar_ok, "
                "       is_crew_wide, pending_since "
                "FROM move_entries WHERE telegram_user_id = %s "
                "  AND created_at >= %s AND created_at < %s ORDER BY created_at",
                (tg_id, lo, hi))
    for r in cur.fetchall():
        bits = [f"move #{r['id']} recorded ({r['media_type']})"]
        if r["is_crew_wide"]:
            bits.append("to everyone")
        if r["radar_ok"]:
            bits.append("+ radar")
        if r["pending_since"]:
            bits.append("STILL PENDING")
        if r["text_body"]:
            bits.append(f'text: "{r["text_body"]}"')
        if r["comment"]:
            bits.append(f'caption: "{r["comment"]}"')
        out.append((r["created_at"].astimezone(BERLIN).strftime("%H:%M"), "·",
                    " · ".join(bits)))

    cur.execute(
        "SELECT c.created_at, c.body, c.from_tg_id, c.to_tg_id, "
        "       f.participant_name AS from_name, t.participant_name AS to_name "
        "FROM move_comments c "
        "LEFT JOIN move_users f ON f.telegram_user_id = c.from_tg_id "
        "LEFT JOIN move_users t ON t.telegram_user_id = c.to_tg_id "
        "WHERE (c.from_tg_id = %s OR c.to_tg_id = %s) "
        "  AND c.created_at >= %s AND c.created_at < %s ORDER BY c.created_at",
        (tg_id, tg_id, lo, hi))
    for r in cur.fetchall():
        arrow = "wrote to" if r["from_tg_id"] == tg_id else "received from"
        other = r["to_name"] if r["from_tg_id"] == tg_id else r["from_name"]
        out.append((r["created_at"].astimezone(BERLIN).strftime("%H:%M"), "·",
                    f'comment {arrow} {other}: "{r["body"]}"'))

    cur.execute("SELECT r.created_at, u.participant_name AS who, r.entry_id "
                "FROM move_reactions r "
                "LEFT JOIN move_users u ON u.telegram_user_id = r.reactor_tg_id "
                "JOIN move_entries e ON e.id = r.entry_id "
                "WHERE e.telegram_user_id = %s "
                "  AND r.created_at >= %s AND r.created_at < %s ORDER BY r.created_at",
                (tg_id, lo, hi))
    for r in cur.fetchall():
        out.append((r["created_at"].astimezone(BERLIN).strftime("%H:%M"), "·",
                    f"⚡ from {r['who']} on move #{r['entry_id']}"))

    # Their own lines carry only HH:MM, so a stable sort on the stamp keeps the
    # trace's internal order and slots the timestamped rows around it.
    return sorted(out, key=lambda e: e[0])


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay one person's Move chat.")
    ap.add_argument("who", help="participant name or telegram id")
    ap.add_argument("--from", dest="since", help="YYYY-MM-DD (default: 7 days ago)")
    ap.add_argument("--to", dest="until", help="YYYY-MM-DD (default: today)")
    args = ap.parse_args()

    if not os.environ.get("DATABASE_URL"):
        sys.exit("ERROR: DATABASE_URL is not set.")

    until = date.fromisoformat(args.until) if args.until else date.today()
    since = date.fromisoformat(args.since) if args.since else until - timedelta(days=7)

    conn = psycopg2.connect(os.environ["DATABASE_URL"],
                            cursor_factory=psycopg2.extras.RealDictCursor)
    cur = conn.cursor()
    tg_id, name = _resolve(cur, args.who)

    print(f"Move replay — {name} ({tg_id}) — {since} to {until}")
    print("→ what they did   ← what the bot said   ✂ what it removed   · content")
    print("Verbatim from 9 Sep 2026; before that, kinds and ids only.")

    day = since
    while day <= until:
        events = _events(cur, tg_id, day)
        if events:
            print(f"\n── {day:%a %d %b} " + "─" * 40)
            for stamp, arrow, text in events:
                print(f"  {stamp}  {arrow}  {text}")
        day += timedelta(days=1)
    conn.close()


if __name__ == "__main__":
    main()
