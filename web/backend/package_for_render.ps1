# Render 部署脚本
# 运行此脚本打包后端代码

$backendDir = "e:\E\任务\task-platform\web\backend"
$outputFile = "$backendDir\deploy.zip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  打包后端代码用于部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 要打包的目录和文件
$files = @(
    "main.py",
    "requirements.txt",
    "api",
    "models",
    "services"
)

# 创建临时目录
$tempDir = "$env:TEMP\render_deploy_$([guid]::NewGuid().ToString().Substring(0,8))"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "复制文件到临时目录..." -ForegroundColor Yellow

foreach ($file in $files) {
    $src = Join-Path $backendDir $file
    $dest = Join-Path $tempDir $file

    if (Test-Path $src) {
        if ((Get-Item $src).PSIsContainer) {
            Copy-Item -Path $src -Destination $dest -Recurse -Force
        } else {
            Copy-Item -Path $src -Destination $dest -Force
        }
        Write-Host "  ✓ $file" -ForegroundColor Green
    }
}

# 创建 Render 启动脚本
$startScript = @"
#!/bin/bash
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --host 0.0.0.0 --port `$PORT
"@

$startScript | Out-File -FilePath "$tempDir\start.sh" -Encoding utf8

# 创建 Render 规范文件
$renderYaml = @"
buildCommand: pip install -r requirements.txt && playwright install chromium
startCommand: uvicorn main:app --host 0.0.0.0 --port `$PORT
"@

$renderYaml | Out-File -FilePath "$tempDir\render.yaml" -Encoding utf8

Write-Host ""
Write-Host "创建 zip 文件..." -ForegroundColor Yellow

# 删除旧文件
if (Test-Path $outputFile) {
    Remove-Item $outputFile -Force
}

# 压缩
Compress-Archive -Path "$tempDir\*" -DestinationPath $outputFile -Force

# 清理临时目录
Remove-Item $tempDir -Recurse -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  打包完成!" -ForegroundColor Green
Write-Host "  文件位置: $outputFile" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "  1. 打开 https://render.com" -ForegroundColor White
Write-Host "  2. 登录后点击 New -> Web Service" -ForegroundColor White
Write-Host "  3. 选择最下面的 'Deploy manually'" -ForegroundColor White
Write-Host "  4. 上传 $outputFile 文件" -ForegroundColor White
Write-Host "  5. 环境变量设置:" -ForegroundColor White
Write-Host "     - MYSTEEL_USERNAME = 你的用户名" -ForegroundColor Gray
Write-Host "     - MYSTEEL_PASSWORD = 你的密码" -ForegroundColor Gray
Write-Host "" -ForegroundColor White
