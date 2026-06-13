# 价格监控一键修复脚本
# 在服务器上运行此脚本

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "价格监控API修复 - 禁用Supabase" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 检查路径
$ConfigPath = "C:\taskplatform\config\cloud.json"
if (-not (Test-Path "C:\taskplatform")) {
    Write-Host "错误：无法访问 C:\taskplatform" -ForegroundColor Red
    Write-Host "请确认你已登录服务器 (140.143.125.234)" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "[1/5] 路径检查完成" -ForegroundColor Green

# 备份配置
if (Test-Path $ConfigPath) {
    Write-Host "[2/5] 备份配置文件..." -ForegroundColor Yellow
    Copy-Item $ConfigPath "$ConfigPath.backup" -Force
    Write-Host "     备份完成" -ForegroundColor Green
} else {
    Write-Host "[2/5] 配置文件不存在，创建新文件" -ForegroundColor Yellow
}

# 写入新配置
Write-Host "[3/5] 更新配置文件..." -ForegroundColor Yellow
@'
{
  "mode": "sqlite",
  "supabase_url": "",
  "supabase_key": "",
  "version": "1.0.0"
}
'@ | Set-Content -Path $ConfigPath -Encoding UTF8
Write-Host "     配置已更新为禁用Supabase" -ForegroundColor Green

# 停止服务
Write-Host "[4/5] 停止后端服务..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "     后端服务已停止" -ForegroundColor Green

# 启动服务
Write-Host "[5/5] 启动后端服务..." -ForegroundColor Yellow
Set-Location "C:\taskplatform"
Start-Process python -ArgumentList "-m", "uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000" -WindowStyle Minimized
Write-Host "     后端服务已启动" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "修复完成！" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "验证步骤：" -ForegroundColor Cyan
Write-Host "1. 等待 5-10 秒让服务完全启动" -ForegroundColor White
Write-Host "2. 访问: http://140.143.125.234/" -ForegroundColor White
Write-Host "3. 应该能看到价格数据（10764条记录，415个交易日）" -ForegroundColor White
Write-Host ""
Write-Host "如需恢复原配置：" -ForegroundColor Yellow
Write-Host "  Copy-Item C:\taskplatform\config\cloud.json.backup C:\taskplatform\config\cloud.json" -ForegroundColor Gray
Write-Host ""
Read-Host "按回车键关闭"
