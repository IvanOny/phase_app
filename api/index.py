from __future__ import annotations

import os
import re as _re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, make_response
import psycopg2

from phase_app.api import PhaseApi
from phase_app.db_pg import get_connection

app = Flask(__name__)

_CORS_EXACT = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://phase-app-yf5x.vercel.app",
    "https://phase-app-ivory.vercel.app",
}
_CORS_PATTERN = _re.compile(r"^https://phase-app(-[a-z0-9]+)*\.vercel\.app$")


def _cors_allowed(origin: str) -> bool:
    return origin in _CORS_EXACT or bool(_CORS_PATTERN.match(origin))


_conn: psycopg2.extensions.connection | None = None


def _get_api() -> PhaseApi:
    global _conn
    if _conn is None or _conn.closed:
        _conn = get_connection()
        return PhaseApi(_conn)
    # Ping to catch connections silently dropped by Supabase idle timeout.
    # psycopg2 reports closed=0 even when the server has closed the socket,
    # so we need an explicit round-trip to detect stale warm instances.
    try:
        _conn.cursor().execute("SELECT 1")
        # Close the transaction the ping just opened. psycopg2 is not in
        # autocommit, so SELECT 1 starts one and nothing here ends it -- the
        # instance then sits "idle in transaction" holding AccessShareLock on
        # every table it has touched, for as long as Vercel keeps it warm.
        # That blocks any ALTER TABLE until it hits statement_timeout, and
        # piles up lock contention for everything else.
        _conn.rollback()
    except Exception:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = get_connection()
    return PhaseApi(_conn)


def _release(conn) -> None:
    """End whatever transaction this request left open.

    Every write handler commits for itself, so anything still open here is a
    read -- metrics.py never commits. Left alone it keeps the instance "idle in
    transaction", holding AccessShareLock on the tables it touched for as long
    as Vercel keeps the instance warm. Rolling back is therefore safe and is
    what stops the locks accumulating.
    """
    try:
        if conn and not conn.closed:
            conn.rollback()
    except Exception:
        pass


@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if _cors_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/bot", methods=["POST"])
def telegram_bot():
    secret = os.environ.get("TELEGRAM_BOT_SECRET", "")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return jsonify({"error": "unauthorized"}), 403
    from phase_app.bot import handle_webhook
    import traceback
    try:
        handle_webhook(request.get_json(force=True) or {}, _get_api().conn)
    except Exception:
        traceback.print_exc()
    _release(_conn)
    return jsonify({"ok": True}), 200


@app.route("/api/move", methods=["POST"])
def move_bot():
    secret = os.environ.get("MOVE_BOT_SECRET", "")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        return jsonify({"error": "unauthorized"}), 403
    from phase_app.move_bot import handle_move_webhook, report_webhook_error
    import traceback
    body = request.get_json(force=True) or {}
    try:
        handle_move_webhook(body, _get_api().conn)
    except Exception:
        # Printing to stdout put the traceback in Vercel's logs and nowhere else,
        # so a crash looked exactly like the bot ignoring you — twice now we've
        # had to reconstruct one from the database. Tell the person something
        # went wrong, and put the traceback where it's actually read.
        traceback.print_exc()
        try:
            report_webhook_error(body, traceback.format_exc())
        except Exception:
            traceback.print_exc()
    _release(_conn)
    return jsonify({"ok": True}), 200


def _run_daily_jobs(conn) -> dict:
    """Every scheduled job for every bot, in one place.

    Vercel Hobby caps the number of cron jobs, so all three products share a
    single daily trigger (/api/cron/move, 06:00 UTC = 08:00 Europe/Berlin).
    Each job carries its own cron_log dedup guard, so re-running is harmless.

    Jobs are isolated: one failing must not stop the rest. They used to run
    bare and in sequence, so an exception in an early job silently skipped
    everything after it. A failed statement also leaves Postgres in an aborted
    transaction, so we roll back before continuing or every later job dies too.
    """
    from phase_app.bot import (
        process_radar_candidates, send_daily_report, check_milestones, send_monthly_summaries,
    )
    from phase_app.exercise_bot import send_exercise_overview
    from phase_app.move_bot import (
        send_move_zap_reports, process_move_radar, send_move_monthly_summaries,
        send_move_nudges, purge_move_transient,
    )
    import traceback

    jobs = [
        ("burpee_radar", process_radar_candidates),
        ("burpee_report", send_daily_report),
        ("burpee_milestones", check_milestones),
        ("burpee_monthly", send_monthly_summaries),
        ("snacks_overview", send_exercise_overview),
        ("move_zaps", send_move_zap_reports),
        ("move_radar", process_move_radar),
        ("move_monthly", send_move_monthly_summaries),
        ("move_nudges", send_move_nudges),
        ("move_sweep", purge_move_transient),
    ]
    failed = []
    for name, fn in jobs:
        try:
            fn(conn)
        except Exception:
            failed.append(name)
            traceback.print_exc()
            try:
                conn.rollback()
            except Exception:
                pass
    if failed:
        # Surface it in the log channel — a silently skipped job is how the Move
        # zap report went missing while the burpee report arrived fine.
        try:
            from phase_app.bot import _log
            _log("⚠️ Cron: job(s) failed\n• " + ", ".join(failed))
        except Exception:
            pass
    return {"ok": not failed, "failed": failed}


@app.route("/api/cron/move", methods=["GET", "POST"])
@app.route("/api/cron/radar", methods=["GET", "POST"])   # legacy alias / manual trigger
def cron_daily():
    import traceback
    global _conn
    try:
        result = _run_daily_jobs(_get_api().conn)
    except Exception:
        traceback.print_exc()
        _release(_conn)
        return jsonify({"ok": False, "failed": ["*"]}), 500
    # 200 even with partial failures — the body names them, and Vercel retrying
    # the whole batch would just re-skip everything via cron_log anyway.
    _release(_conn)
    return jsonify(result), 200


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
def handle(path: str):
    if request.method == "OPTIONS":
        return make_response("", 204)
    query_params = {k: v for k, v in request.args.items()}
    body = request.get_json(silent=True) or {}
    global _conn
    try:
        resp = _get_api().handle(request.method, "/" + path, body, query_params)
    except Exception:
        # Roll back any aborted transaction so the connection is reusable.
        _release(_conn)
        raise
    _release(_conn)
    return jsonify(resp.body), resp.status
