@echo off
chcp 65001 > nul
title TaskPlatform 启动

echo ========================================
echo   TaskPlatform 启动
echo ========================================
echo.

PowerShell.exe -ExecutionPolicy Bypass -File "%~dp0start.ps1"

pause
