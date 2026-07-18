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

    def test_self_check_is_windows_only_and_non_destructive(self):
        batch = (ROOT / "WindowsSelfCheck.bat").read_bytes()
        script = (ROOT / "WindowsSelfCheck.ps1").read_text(encoding="utf-8")
        self.assertTrue(batch.isascii())
        self.assertIn(b"\r\n", batch)
        self.assertIn("WindowsSelfCheck.ps1", batch.decode("ascii"))
        self.assertIn("py.exe", script)
        self.assertIn("Project write access", script)
        self.assertIn("Get-NetTCPConnection", script)
        self.assertIn("/api/dashboard", script)
        self.assertIn("profile.json", script)
        self.assertNotIn("Start-Process", script)
        self.assertNotIn("Stop-Process", script)
        self.assertNotIn("backend\\service.py", script)
        self.assertNotIn("python3", script.lower())
        self.assertNotIn("/mnt/", script.lower())
        self.assertNotIn("wsl", script.lower())

    def test_launcher_uses_script_relative_paths_and_does_not_echo_server_logs(self):
        start_ps = (ROOT / "dashboard-start.ps1").read_text(encoding="utf-8")
        start_bat = (ROOT / "启动减脂仪表盘.bat").read_text(encoding="utf-8")
        self.assertIn("$MyInvocation.MyCommand.Path", start_ps)
        self.assertIn("-WorkingDirectory $root", start_ps)
        self.assertIn('%~dp0', start_bat)
        self.assertNotIn("Get-Content $serverLog -Raw", start_ps)
        self.assertNotIn("Get-Content $serverErrorLog -Raw", start_ps)
        self.assertIn("Review runtime\\logs", start_ps)

    def test_public_windows_entrypoints_have_no_non_windows_runtime_instructions(self):
        public_files = [
            ROOT / "README.md",
            ROOT / "prompt.md",
            ROOT / "skills" / "fat-loss-tracker" / "SKILL.md",
            ROOT / "启动减脂仪表盘.bat",
            ROOT / "停止减脂仪表盘.bat",
            ROOT / "WindowsSelfCheck.bat",
            ROOT / "dashboard-start.ps1",
            ROOT / "dashboard-stop.ps1",
            ROOT / "WindowsSelfCheck.ps1",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in public_files).lower()
        for forbidden in ("python3", "/mnt/", "wsl", "#!/bin/bash"):
            self.assertNotIn(forbidden, text)

    def test_independent_telegram_gateway_is_removed(self):
        self.assertFalse((ROOT / "gateway/telegram_bot.py").exists())
        self.assertFalse((ROOT / ".env.example").exists())
        prompt = (ROOT / "prompt.md").read_text(encoding="utf-8")
        self.assertIn("Hermes Gateway", prompt)
        self.assertIn("不创建项目专属 Telegram Bot", prompt)


if __name__ == "__main__":
    unittest.main()
