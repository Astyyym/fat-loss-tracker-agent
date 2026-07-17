import datetime as dt
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.server import DashboardHandler, FRONTEND
from backend.service import CalorieService, TZ_NAME

TZ = ZoneInfo(TZ_NAME)


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        now = dt.datetime(2026, 7, 17, 8, 0, tzinfo=TZ)
        self.service = CalorieService(Path(self.tmp.name), now_fn=lambda: now)
        self.service.handle_message("早餐 标准早餐A", "1")
        handler = type("TestHandler", (DashboardHandler,), {"service": self.service})
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        self.tmp.cleanup()

    def test_api_uses_same_service_summary(self):
        with urllib.request.urlopen(self.base + "/api/dashboard") as response:
            payload = json.loads(response.read().decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(self.service.daily_summary("2026-07-17")["calories"], payload["today"]["calories"])
        self.assertIn("generated_at", payload)
        self.assertIn("source_files", payload)

    def test_frontend_static_files_served(self):
        with urllib.request.urlopen(self.base + "/") as response:
            page = response.read().decode("utf-8")
        self.assertIn("四周减脂记录", page)
        self.assertIn("数据最后更新时间", page)

    def test_server_is_read_only(self):
        request = urllib.request.Request(self.base + "/api/dashboard", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(405, ctx.exception.code)

    def test_frontend_has_no_external_or_localstorage_dependencies(self):
        html_css = "\n".join((FRONTEND / name).read_text(encoding="utf-8") for name in ("index.html", "styles.css"))
        js = (FRONTEND / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("http://", html_css)
        self.assertNotIn("https://", html_css)
        self.assertNotIn("fetch('http", js)
        self.assertNotIn("fetch(\"http", js)
        self.assertNotIn("localStorage", html_css + js)
        self.assertNotIn("cdn", (html_css + js).lower())


if __name__ == "__main__":
    unittest.main()
