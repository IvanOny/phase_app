from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from phase_app.api import PhaseApi
from phase_app.db_pg import get_connection

FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"

CORS_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://phase-app-yf5x.vercel.app",
}


class AppHandler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        origin = self.headers.get("Origin", "")
        if origin in CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

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

    def _api(self):
        try:
            conn = get_connection()
        except Exception as exc:
            import traceback
            traceback.print_exc()
            raise
        return PhaseApi(conn)

    def do_GET(self):
        import sys, traceback as _tb
        print(f"[GET] {self.path}", flush=True)
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

            if path == "/" or path == "/index.html":
                return self._send_file(FRONTEND_ROOT / "index.html", "text/html; charset=utf-8")
            if path == "/app.js":
                return self._send_file(FRONTEND_ROOT / "app.js", "text/javascript; charset=utf-8")

            response = self._api().handle("GET", path, query_params=query)
            print(f"[GET] response {response.status}", flush=True)
            self._send_json(response.status, response.body)
        except Exception:
            print("[GET] EXCEPTION:", flush=True)
            _tb.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()

    def _check_auth(self, method: str, path: str) -> bool:
        from phase_app.auth import require_auth
        secret = os.environ.get("TOKEN_SECRET", "")
        auth_header = self.headers.get("Authorization")
        return require_auth(method, path, auth_header, secret)

    def _is_burpee_path(self, path: str) -> bool:
        """Burpee endpoints use token-based auth in query params, not Bearer auth."""
        return path == "/v1/burpee" or path.startswith("/v1/burpee/")

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
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if not self._is_burpee_path(parsed.path) and not self._check_auth("POST", parsed.path):
            return self._send_json(401, {"error": "unauthorized"})
        payload = self._parse_json_body()
        if payload is None:
            return
        response = self._api().handle("POST", parsed.path, payload, query)
        self._send_json(response.status, response.body)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if not self._is_burpee_path(parsed.path) and not self._check_auth("PATCH", parsed.path):
            return self._send_json(401, {"error": "unauthorized"})
        payload = self._parse_json_body()
        if payload is None:
            return
        response = self._api().handle("PATCH", parsed.path, payload, query)
        self._send_json(response.status, response.body)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if not self._is_burpee_path(parsed.path) and not self._check_auth("DELETE", parsed.path):
            return self._send_json(401, {"error": "unauthorized"})
        response = self._api().handle("DELETE", parsed.path, {}, query)
        self._send_json(response.status, response.body)



def run_server(host: str = "0.0.0.0", port: int | None = None):
    port = port or int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
