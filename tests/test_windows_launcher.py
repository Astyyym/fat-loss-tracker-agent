import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class WindowsLauncherTests(unittest.TestCase):
    def test_launchers_exist_and_use_windows_python(self):
        start = (ROOT / "启动减脂仪表盘.bat").read_text(encoding="utf-8")
        stop = (ROOT / "停止减脂仪表盘.bat").read_text(encoding="utf-8")
        start_ps = (ROOT / "dashboard-start.ps1").read_text(encoding="utf-8")
        stop_ps = (ROOT / "dashboard-stop.ps1").read_text(encoding="utf-8")
        self.assertIn("dashboard-start.ps1", start)
        self.assertIn("runtime\\logs", start)
        self.assertIn("py.exe", start_ps)
        self.assertIn("backend\\server.py", start_ps)
        self.assertIn("runtime\\logs", start_ps)
        self.assertIn("127.0.0.1", start_ps)
        self.assertIn("8765", start_ps)
        self.assertNotIn("wsl", (start + start_ps).lower())
        self.assertIn("dashboard-stop.ps1", stop)
        self.assertIn("Get-NetTCPConnection", stop_ps)
        self.assertIn("server\\.py", stop_ps)
        self.assertTrue((ROOT / "启动减脂仪表盘.bat").read_bytes().isascii())
        self.assertIn(b"\r\n", (ROOT / "启动减脂仪表盘.bat").read_bytes())

    def test_independent_telegram_gateway_is_removed(self):
        self.assertFalse((ROOT / "gateway/telegram_bot.py").exists())
        self.assertFalse((ROOT / ".env.example").exists())
        prompt = (ROOT / "prompt.md").read_text(encoding="utf-8")
        self.assertIn("Hermes Gateway", prompt)
        self.assertIn("不创建项目专属 Telegram Bot", prompt)


if __name__ == "__main__":
    unittest.main()
