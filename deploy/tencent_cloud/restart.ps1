﻿# TaskPlatform 重启脚本
# 一键重启所有服务

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform 重启服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# 停止服务
Write-Host "步骤 1/2: 停止服务..." -ForegroundColor Yellow
& "$ScriptPath\stop.ps1"

# 等待
Write-Host "等待 3 秒..." -ForegroundColor Cyan
Start-Sleep -Seconds 3

# 启动服务
Write-Host "`n步骤 2/2: 启动服务..." -ForegroundColor Yellow
& "$ScriptPath\start.ps1"
