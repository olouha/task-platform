@echo off
chcp 65001 > nul
title TaskPlatform 重启

echo ========================================
echo   TaskPlatform 重启
echo ========================================
echo.

PowerShell.exe -ExecutionPolicy Bypass -File "%~dp0restart.ps1"

pause
