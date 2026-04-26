from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from phase_app.api import PhaseApi
from phase_app.db import get_connection, init_db, seed_minimal_bench_data

FRONTEND_ROOT = Path(__file__).resolve().parent.parent / "frontend"


class AppHandler(BaseHTTPRequestHandler):
    api: PhaseApi

    def _send_json(self, status: int, payload: dict):
        blob = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(blob)))
        self.end_headers()
        self.wfile.write(blob)

    def _send_file(self, file_path: Path, content_type: str):
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            return self._send_file(FRONTEND_ROOT / "index.html", "text/html; charset=utf-8")
        if path == "/app.js":
            return self._send_file(FRONTEND_ROOT / "app.js", "text/javascript; charset=utf-8")

        response = self.api.handle("GET", path)
        self._send_json(response.status, response.body)

    def do_POST(self):
        parsed = urlparse(self.path)
        content_len = int(self.headers.get("Content-Length", "0"))
        body_blob = self.rfile.read(content_len) if content_len else b"{}"
        try:
            payload = json.loads(body_blob.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "invalid_json"})
        response = self.api.handle("POST", parsed.path, payload)
        self._send_json(response.status, response.body)



def run_server(host: str = "127.0.0.1", port: int = 8000):
    conn = get_connection("phase_app.db")
    init_db(conn)
    seed_minimal_bench_data(conn)
    AppHandler.api = PhaseApi(conn)
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
