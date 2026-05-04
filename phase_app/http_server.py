from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from phase_app.api import PhaseApi
from phase_app.db_pg import get_connection, seed_minimal_bench_data

FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"

CORS_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://phase-app-yf5x.vercel.app",
}


class AppHandler(BaseHTTPRequestHandler):
    api: PhaseApi

    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if origin in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status: int, payload: dict):
        blob = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(blob)

    def _send_file(self, file_path: Path, content_type: str):
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path == "/" or path == "/index.html":
            return self._send_file(FRONTEND_ROOT / "index.html", "text/html; charset=utf-8")
        if path == "/app.js":
            return self._send_file(FRONTEND_ROOT / "app.js", "text/javascript; charset=utf-8")

        response = self.api.handle("GET", path, query_params=query)
        self._send_json(response.status, response.body)

    def _parse_json_body(self) -> dict | None:
        content_len = int(self.headers.get("Content-Length", "0"))
        body_blob = self.rfile.read(content_len) if content_len else b"{}"
        try:
            return json.loads(body_blob.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return None

    def do_POST(self):
        parsed = urlparse(self.path)
        payload = self._parse_json_body()
        if payload is None:
            return
        response = self.api.handle("POST", parsed.path, payload)
        self._send_json(response.status, response.body)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        payload = self._parse_json_body()
        if payload is None:
            return
        response = self.api.handle("PATCH", parsed.path, payload)
        self._send_json(response.status, response.body)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        response = self.api.handle("DELETE", parsed.path)
        self._send_json(response.status, response.body)



def run_server(host: str = "0.0.0.0", port: int | None = None):
    port = port or int(os.environ.get("PORT", 8000))
    conn = get_connection()
    seed_minimal_bench_data(conn)
    AppHandler.api = PhaseApi(conn)
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
