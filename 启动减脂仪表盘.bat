@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "LOG=%~dp0dashboard-launch.log"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0启动减脂仪表盘.ps1" > "%LOG%" 2>&1
if errorlevel 1 (
    echo.
    echo 仪表盘启动失败，错误日志：
    echo %LOG%
    echo.
    type "%LOG%"
    pause
    exit /b 1
)
exit /b 0
