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
    except Exception:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = get_connection()
    return PhaseApi(_conn)


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
    return jsonify({"ok": True}), 200


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
def handle(path: str):
    if request.method == "OPTIONS":
        return make_response("", 204)
    query_params = {k: v for k, v in request.args.items()}
    body = request.get_json(silent=True) or {}
    try:
        resp = _get_api().handle(request.method, "/" + path, body, query_params)
    except Exception:
        # Roll back any aborted transaction so the connection is reusable.
        global _conn
        try:
            if _conn and not _conn.closed:
                _conn.rollback()
        except Exception:
            pass
        raise
    return jsonify(resp.body), resp.status
