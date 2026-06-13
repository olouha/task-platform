@echo off
chcp 65001 > nul
title TaskPlatform 停止

echo ========================================
echo   TaskPlatform 停止
echo ========================================
echo.

PowerShell.exe -ExecutionPolicy Bypass -File "%~dp0stop.ps1"

pause
