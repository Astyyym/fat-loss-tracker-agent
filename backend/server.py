#!/usr/bin/env python3
"""仅绑定 localhost 的只读仪表盘服务器。"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.service import CalorieService  # noqa: E402

FRONTEND = PROJECT_ROOT / "frontend"


class DashboardHandler(BaseHTTPRequestHandler):
    service = CalorieService(PROJECT_ROOT)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self._json(self.service.dashboard_payload())
            return
        relative = "index.html" if path in {"/", "/index.html"} else unquote(path.lstrip("/"))
        target = (FRONTEND / relative).resolve()
        if FRONTEND.resolve() not in target.parents and target != FRONTEND.resolve():
            self.send_error(403); return
        if not target.is_file():
            self.send_error(404); return
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(content)

    def _json(self, payload):
        content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(200 if payload.get("ok") else 503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(content)

    def do_POST(self):
        self.send_error(405, "Method Not Allowed")

    def log_message(self, fmt, *args):
        # 不记录 URL 参数、chat_id 或健康内容；仅保留通用 HTTP 状态。
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="启动 localhost 只读减脂仪表盘")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    print(f"Dashboard: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
