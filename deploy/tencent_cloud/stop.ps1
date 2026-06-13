﻿# TaskPlatform 停止脚本
# 一键停止所有服务

Write-Host "========================================" -ForegroundColor Red
Write-Host "  TaskPlatform 停止服务" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Red
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployDir = $ScriptDir
while (-not (Test-Path "$DeployDir\web\backend\main.py") -and (Split-Path -Parent $DeployDir)) {
    $DeployDir = Split-Path -Parent $DeployDir
}
$PidDir = "$DeployDir\pids"

# 停止后端服务
Write-Host "[1/2] 停止后端服务..." -ForegroundColor Yellow
$BackendPidFile = "$PidDir\backend.pid"

if (Test-Path $BackendPidFile) {
    $SavedPid = Get-Content $BackendPidFile -ErrorAction SilentlyContinue
    if ($SavedPid -and $SavedPid -match "^\d+$") {
        $Process = Get-Process -Id ([int]$SavedPid) -ErrorAction SilentlyContinue
        if ($Process) {
            Stop-Process -Id $SavedPid -Force
            Write-Host "  ✓ 后端服务已停止 (PID: $SavedPid)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ 后端进程不存在 (PID: $SavedPid)" -ForegroundColor Yellow
        }
    }
    Remove-Item $BackendPidFile -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  ⚠ 未找到 PID 文件，尝试查找 uvicorn 进程..." -ForegroundColor Yellow
    $UvicornProcesses = Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.CommandLine -like "*uvicorn*" } -ErrorAction SilentlyContinue
    foreach ($proc in $UvicornProcesses) {
        Stop-Process -Id $proc.Id -Force
        Write-Host "  ✓ 已停止 python 进程 (PID: $($proc.Id))" -ForegroundColor Green
    }
}

# 停止 nginx
Write-Host "[2/2] 停止 nginx..." -ForegroundColor Yellow
$NginxExe = "C:\nginx\nginx.exe"
if (Test-Path $NginxExe) {
    & $NginxExe -s stop 2>$null
    Write-Host "  ✓ nginx 已停止" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 未找到 nginx" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  所有服务已停止" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
