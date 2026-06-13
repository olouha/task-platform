# 价格监控API修复部署脚本
# 修复 Supabase 回退逻辑错误处理

$ErrorActionPreference = "Stop"

# 配置
$LocalPath = "e:\E\任务\task-platform\web\backend\api\yantai_db.py"
$ServerPath = "C:\taskplatform\web\backend\api\yantai_db.py"
$BackupPath = "C:\taskplatform\web\backend\api\yantai_db.py.backup"

Write-Host "=== 价格监控API修复部署 ===" -ForegroundColor Cyan
Write-Host ""

# 检查本地文件
if (!(Test-Path $LocalPath)) {
    Write-Host "错误：本地文件不存在: $LocalPath" -ForegroundColor Red
    exit 1
}

Write-Host "1. 本地文件检查完成" -ForegroundColor Green

# 检查服务器路径（假设是本地服务器）
if (Test-Path $ServerPath) {
    Write-Host "2. 备份服务器文件..." -ForegroundColor Yellow
    Copy-Item $ServerPath $BackupPath -Force
    Write-Host "   备份完成: $BackupPath" -ForegroundColor Green
}

# 复制修复文件
Write-Host "3. 复制修复文件到服务器..." -ForegroundColor Yellow
Copy-Item $LocalPath $ServerPath -Force
Write-Host "   复制完成" -ForegroundColor Green

# 重启后端服务
Write-Host "4. 重启后端服务..." -ForegroundColor Yellow
$RestartScript = "C:\taskplatform\deploy\tencent_cloud\restart.ps1"
if (Test-Path $RestartScript) {
    & $RestartScript
} else {
    Write-Host "   警告：重启脚本不存在，请手动重启服务" -ForegroundColor Yellow
    Write-Host "   运行: cd C:\taskplatform && taskkill /F /IM python.exe && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
}

Write-Host ""
Write-Host "=== 部署完成 ===" -ForegroundColor Green
Write-Host "请访问 http://140.143.125.234/ 验证价格监控页面" -ForegroundColor Cyan
