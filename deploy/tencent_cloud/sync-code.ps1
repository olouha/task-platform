# TaskPlatform 同步脚本
# 将本地代码同步到腾讯云服务器并重启服务

param(
    [switch]$SkipRestart
)

$ErrorActionPreference = "Stop"

# 配置
$LocalFiles = @(
    "web\backend\api\indicator_report.py"
)

$ServerBase = "C:\taskplatform\task-platform-main"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform 代码同步" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查本地文件
Write-Host "[1/4] 检查本地文件..." -ForegroundColor Yellow
foreach ($file in $LocalFiles) {
    $fullPath = Join-Path $PSScriptRoot "..\.." $file
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        Write-Host "  ✓ $file ($size bytes)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file 不存在" -ForegroundColor Red
        exit 1
    }
}

# 检查服务器路径
Write-Host "[2/4] 检查服务器路径..." -ForegroundColor Yellow
if (Test-Path $ServerBase) {
    Write-Host "  ✓ 服务器路径存在: $ServerBase" -ForegroundColor Green
} else {
    Write-Host "  ✗ 服务器路径不存在: $ServerBase" -ForegroundColor Red
    Write-Host "  请确认服务器已挂载或修改 ServerBase 路径" -ForegroundColor Yellow
    exit 1
}

# 同步文件
Write-Host "[3/4] 同步文件..." -ForegroundColor Yellow
foreach ($file in $LocalFiles) {
    $localPath = Join-Path $PSScriptRoot "..\.." $file
    $serverPath = Join-Path $ServerBase $file
    $serverDir = Split-Path $serverPath -Parent

    # 确保目录存在
    if (-not (Test-Path $serverDir)) {
        $null = New-Item -Path $serverDir -ItemType Directory -Force
    }

    # 备份旧文件
    if (Test-Path $serverPath) {
        $backupPath = "$serverPath.backup"
        Copy-Item $serverPath $backupPath -Force
        Write-Host "  备份: $file -> $file.backup" -ForegroundColor Cyan
    }

    # 复制新文件
    Copy-Item $localPath $serverPath -Force
    Write-Host "  同步: $file" -ForegroundColor Green
}

# 重启服务
if (-not $SkipRestart) {
    Write-Host "[4/4] 重启服务..." -ForegroundColor Yellow
    $restartScript = Join-Path $PSScriptRoot "restart.ps1"
    if (Test-Path $restartScript) {
        & $restartScript
    } else {
        Write-Host "  ⚠ 重启脚本不存在，请手动重启服务" -ForegroundColor Yellow
    }
} else {
    Write-Host "[4/4] 跳过重启" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  同步完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "访问 http://140.143.125.234:8080/api/indicator-report/database/init-sample 初始化数据" -ForegroundColor Cyan