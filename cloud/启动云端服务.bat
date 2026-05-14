@echo off
chcp 65001 >nul
title TaskPlatform 云端服务

echo ================================================
echo TaskPlatform 云端服务器
echo ================================================
echo.

python "%~dp0start_server.py"

pause