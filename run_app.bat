
@echo off
title AttendWise AI 2026 - Launcher
echo ========================================================
echo   ATTENDWISE AI 2026 - AUTONOMOUS ATTENDANCE OS
echo ========================================================
echo.
echo Launching Backend and Frontend in separate windows...
powershell -ExecutionPolicy Bypass -File scripts\start_dev.ps1
echo.
echo Launch commands dispatched. You can close this window.
pause

