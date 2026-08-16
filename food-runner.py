#!/usr/bin/env python3
"""Loopback HTTP bridge so n8n (node-only container) can run the food scripts.

Listens on 127.0.0.1:8731 inside the shared tailscale network namespace.
Not exposed anywhere — only the other containers in this netns can reach it.

POST /run  {"cmd": "sync" | "cart", "args": [...]}
 -> {"exit_code": int, "stdout": "combined output"}
"""
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

SCRIPTS = {
    "sync": ["python3", "/opt/food/tandoor/sync_tandoor.py", "--json"],
    "cart": ["python3", "/opt/food/kroger/cart.py", "--json"],
}

PORT = 8731
TIMEOUT_S = 900


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            req = {}
        cmd = req.get("cmd", "")
        if cmd not in SCRIPTS:
            self._send(400, {"exit_code": 2,
                             "stdout": f"unknown cmd {cmd!r}; use {sorted(SCRIPTS)}"})
            return
        try:
            proc = subprocess.run(
                SCRIPTS[cmd],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            self._send(200, {"exit_code": proc.returncode, "stdout": out})
        except subprocess.TimeoutExpired:
            self._send(500, {"exit_code": 124, "stdout": f"timed out after {TIMEOUT_S}s"})

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # keep logs quiet
        pass


if __name__ == "__main__":
    print(f"food-runner listening on 127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
