﻿# TaskPlatform 生产部署脚本
# 一键启动所有服务

Write-Host "========================================" -ForegroundColor Green
Write-Host "  TaskPlatform 生产环境启动" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 配置 - 自动检测当前目录（向上查找直到找到 web/backend）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DeployDir = $ScriptDir
while (-not (Test-Path "$DeployDir\web\backend\main.py") -and (Split-Path -Parent $DeployDir)) {
    $DeployDir = Split-Path -Parent $DeployDir
}
$BackendDir = "$DeployDir\web\backend"
$LogDir = "$DeployDir\logs"
$PidDir = "$DeployDir\pids"

Write-Host "检测到项目目录: $DeployDir" -ForegroundColor Cyan

# 创建必要目录
$null = New-Item -Path $PidDir -ItemType Directory -Force
$null = New-Item -Path $LogDir -ItemType Directory -Force

# 检查 Python
Write-Host "[1/5] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    exit 1
}

# 检查依赖
Write-Host "[2/5] 检查依赖..." -ForegroundColor Yellow
if (-not (Test-Path "$BackendDir\requirements.txt")) {
    Write-Host "  ✗ 找不到 requirements.txt" -ForegroundColor Red
    exit 1
}

# 安装依赖（如果需要）
Write-Host "  检查 Python 依赖..." -ForegroundColor Cyan
$needsInstall = $false
try {
    $null = python -c "import fastapi; import uvicorn; import supabase" 2>$null
} catch {
    $needsInstall = $true
}

if ($needsInstall) {
    Write-Host "  安装依赖中..." -ForegroundColor Cyan
    Set-Location $BackendDir
    pip install -r requirements.txt -q
    Write-Host "  ✓ 依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✓ 依赖已安装" -ForegroundColor Green
}

# 检查环境变量
Write-Host "[3/5] 检查环境配置..." -ForegroundColor Yellow
$EnvFile = "$BackendDir\.env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "  ⚠ 未找到 .env 文件，创建模板..." -ForegroundColor Yellow
    @"
# 数据库配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI服务配置
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key

# 应用配置
LOG_LEVEL=INFO
"@ | Out-File -FilePath $EnvFile -Encoding UTF8
    Write-Host "  ⚠ 请编辑 $EnvFile 配置实际值后重试" -ForegroundColor Yellow
    exit 1
}
Write-Host "  ✓ 环境配置已就绪" -ForegroundColor Green

# 停止现有服务
Write-Host "[4/5] 停止现有服务..." -ForegroundColor Yellow
$BackendPidFile = "$PidDir\backend.pid"
if (Test-Path $BackendPidFile) {
    $oldPid = Get-Content $BackendPidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        $oldProcess = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($oldProcess) {
            Stop-Process -Id $oldPid -Force
            Write-Host "  ✓ 已停止旧的后端服务 (PID: $oldPid)" -ForegroundColor Green
        }
    }
}

# 启动 nginx
Write-Host "  启动 nginx..." -ForegroundColor Cyan
$NginxExe = "C:\nginx\nginx.exe"
if (Test-Path $NginxExe) {
    # 停止现有 nginx
    & $NginxExe -s stop 2>$null
    Start-Sleep -Seconds 1
    # 启动 nginx
    & $NginxExe
    Write-Host "  ✓ nginx 已启动" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 未找到 nginx，跳过" -ForegroundColor Yellow
}

# 启动后端服务
Write-Host "[5/5] 启动后端服务..." -ForegroundColor Yellow
$LogFile = "$LogDir\backend.log"
$ErrorLogFile = "$LogDir\backend-error.log"

# 获取当前日期
$Date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# 启动 uvicorn
$Process = Start-Process -FilePath python `
    -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info" `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $LogFile `
    -RedirectStandardError $ErrorLogFile `
    -WindowStyle Hidden `
    -PassThru

# 保存 PID
$Process.Id | Out-File -FilePath $BackendPidFile -Encoding UTF8

# 等待启动
Start-Sleep -Seconds 3

# 检查进程是否运行
$BackendProcess = Get-Process -Id $Process.Id -ErrorAction SilentlyContinue
if ($BackendProcess) {
    Write-Host "  ✓ 后端服务已启动 (PID: $($Process.Id))" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  启动成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "访问地址:" -ForegroundColor Cyan
    Write-Host "  后端 API: http://localhost:8000" -ForegroundColor White
    Write-Host "  API 文档: http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "日志位置:" -ForegroundColor Cyan
    Write-Host "  标准日志: $LogFile" -ForegroundColor White
    Write-Host "  错误日志: $ErrorLogFile" -ForegroundColor White
    Write-Host ""
    Write-Host "管理命令:" -ForegroundColor Cyan
    Write-Host "  停止服务: .\stop.ps1" -ForegroundColor White
    Write-Host "  查看日志: .\view-logs.ps1" -ForegroundColor White
    Write-Host "  重启服务: .\restart.ps1" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  ✗ 后端启动失败，请检查日志" -ForegroundColor Red
    Write-Host "  日志: $ErrorLogFile" -ForegroundColor Yellow
    exit 1
}
