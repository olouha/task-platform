# TaskPlatform 一键部署脚本
# 运行前请确保已安装 Railway CLI: npm i -g @railway/cli

param(
    [string]$RailwayToken = "",
    [string]$MySteelUsername = "M6616592358",
    [string]$MySteelPassword = "mysteel573005"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform 部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Railway CLI
Write-Host "检查 Railway CLI..." -ForegroundColor Yellow
$railway = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railway) {
    Write-Host "  未安装 Railway CLI，正在安装..." -ForegroundColor Yellow
    npm install -g @railway/cli
}

# 登录 Railway（如果没有token）
if (-not $RailwayToken) {
    Write-Host ""
    Write-Host "请在浏览器中完成 Railway 登录..." -ForegroundColor Yellow
    railway login
} else {
    railway login --token $RailwayToken
}

# 部署后端
Write-Host ""
Write-Host "开始部署后端到 Railway..." -ForegroundColor Yellow

# 设置环境变量
$env:MYSTEEL_USERNAME = $MySteelUsername
$env:MYSTEEL_PASSWORD = $MySteelPassword

# 切换到后端目录
Push-Location "web/backend"

# 创建新项目或部署已有项目
$projectExists = railway project list 2>$null | Select-String "task-platform"

if ($projectExists) {
    Write-Host "  项目已存在，使用现有项目..." -ForegroundColor Yellow
    railway up --project task-platform
} else {
    Write-Host "  创建新项目..." -ForegroundColor Yellow
    railway init --name task-platform
    railway up
}

# 设置环境变量
Write-Host "  设置环境变量..." -ForegroundColor Yellow
railway variables set MYSTEEL_USERNAME $MySteelUsername
railway variables set MYSTEEL_PASSWORD $MySteelPassword

Pop-Location

# 获取部署URL
Write-Host ""
Write-Host "获取部署URL..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$backendUrl = railway domain 2>$null

if ($backendUrl) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  后端部署成功!" -ForegroundColor Green
    Write-Host "  URL: https://$backendUrl" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "下一步: " -ForegroundColor Yellow
    Write-Host "  1. 修改前端 API 地址为: https://$backendUrl" -ForegroundColor White
    Write-Host "  2. 部署前端到 Vercel" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  无法获取URL，请在 Railway 控制台查看" -ForegroundColor Red
}

Write-Host "部署完成!" -ForegroundColor Cyan