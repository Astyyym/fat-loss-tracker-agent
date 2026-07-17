@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0runtime\logs" mkdir "%~dp0runtime\logs"
set "LOG=%~dp0runtime\logs\dashboard-launch.log"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0dashboard-start.ps1" > "%LOG%" 2>&1
if errorlevel 1 (
  echo.
  echo Dashboard failed to start. Log file:
  echo %LOG%
  echo.
  type "%LOG%"
  pause
  exit /b 1
)
exit /b 0
