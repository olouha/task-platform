# Nginx 安装脚本 - 腾讯云 Windows
# 解决权限问题

Write-Host "========================================" -ForegroundColor Green
Write-Host "  安装 Nginx 到腾讯云服务器" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 停止可能运行的 nginx
Write-Host "[1/4] 停止现有 nginx 进程..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -like "nginx" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 下载 Nginx
Write-Host "[2/4] 下载 Nginx..." -ForegroundColor Yellow
$ZipPath = "$env:USERPROFILE\Desktop\nginx.zip"
$NginxUrl = "http://nginx.org/download/nginx-1.24.0.zip"

if (Test-Path $ZipPath) {
    Write-Host "  文件已存在，跳过下载" -ForegroundColor Green
} else {
    try {
        Invoke-WebRequest -Uri $NginxUrl -OutFile $ZipPath -UseBasicParsing
        Write-Host "  ✓ 下载完成" -ForegroundColor Green
    } catch {
        Write-Host "  ✗ 下载失败: $_" -ForegroundColor Red
        exit 1
    }
}

# 删除旧的 nginx 目录
Write-Host "[3/4] 清理旧目录..." -ForegroundColor Yellow
if (Test-Path "C:\nginx") {
    Write-Host "  删除 C:\nginx..." -ForegroundColor Cyan
    Remove-Item "C:\nginx" -Recurse -Force -ErrorAction SilentlyContinue
}

if (Test-Path "C:\nginx-1.24.0") {
    Write-Host "  删除 C:\nginx-1.24.0..." -ForegroundColor Cyan
    Remove-Item "C:\nginx-1.24.0" -Recurse -Force -ErrorAction SilentlyContinue
}

# 解压到临时目录，然后移动
Write-Host "[4/4] 安装 Nginx..." -ForegroundColor Yellow
$TempDir = "$env:TEMP\nginx_temp"
Expand-Archive $ZipPath -DestinationPath $TempDir -Force

# 找到解压后的目录
$ExtractedDir = Get-ChildItem $TempDir -Directory | Select-Object -First 1

# 移动到 C:\nginx
Write-Host "  移动文件到 C:\nginx..." -ForegroundColor Cyan
Move-Item $ExtractedDir.FullName "C:\nginx" -Force

# 清理临时文件
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Nginx 安装完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 验证安装
$NginxExe = "C:\nginx\nginx.exe"
if (Test-Path $NginxExe) {
    Write-Host "安装路径: C:\nginx" -ForegroundColor Cyan
    & $NginxExe -v
    Write-Host ""
    Write-Host "下一步:" -ForegroundColor Yellow
    Write-Host "  1. 复制配置文件: copy C:\taskplatform\deploy\tencent_cloud\nginx-windows.conf C:\nginx\conf\nginx.conf" -ForegroundColor White
    Write-Host "  2. 测试配置: C:\nginx\nginx.exe -t" -ForegroundColor White
    Write-Host "  3. 启动 nginx: C:\nginx\nginx.exe" -ForegroundColor White
} else {
    Write-Host "安装失败，请检查" -ForegroundColor Red
}
