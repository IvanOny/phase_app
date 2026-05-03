from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, make_response
import psycopg2

from phase_app.api import PhaseApi
from phase_app.db_pg import get_connection, seed_minimal_bench_data

app = Flask(__name__)

CORS_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://phase-app-yf5x.vercel.app",
}

_conn: psycopg2.extensions.connection | None = None


def _get_api() -> PhaseApi:
    global _conn
    if _conn is None or _conn.closed:
        _conn = get_connection()
        seed_minimal_bench_data(_conn)
    return PhaseApi(_conn)


@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin", "")
    if origin in CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "OPTIONS"])
@app.route("/<path:path>", methods=["GET", "POST", "OPTIONS"])
def handle(path: str):
    if request.method == "OPTIONS":
        return make_response("", 204)
    query_params = {k: v for k, v in request.args.items()}
    body = request.get_json(silent=True) or {}
    resp = _get_api().handle(request.method, "/" + path, body, query_params)
    return jsonify(resp.body), resp.status
