# TaskPlatform Windows 部署脚本
# 使用 PowerShell 运行: .\deploy-windows.ps1

Write-Host "========================================" -ForegroundColor Green
Write-Host "  TaskPlatform Windows 部署脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 配置
$AppDir = "C:\taskplatform"
$Archive = Join-Path $PSScriptRoot "task-platform-deploy.tar.gz"

# 检查压缩包
if (-not (Test-Path $Archive)) {
    Write-Host "错误: 找不到 task-platform-deploy.tar.gz" -ForegroundColor Red
    Write-Host "请将压缩包放在当前目录: $PSScriptRoot"
    Read-Host "按回车键退出"
    exit 1
}

# 创建目录结构
Write-Host "[1/6] 创建目录结构..." -ForegroundColor Yellow
$null = New-Item -Path $AppDir -ItemType Directory -Force
$null = New-Item -Path "$AppDir\backend" -ItemType Directory -Force
$null = New-Item -Path "$AppDir\frontend" -ItemType Directory -Force
$null = New-Item -Path "$AppDir\logs" -ItemType Directory -Force
Write-Host "目录创建完成: $AppDir"

# 解压文件
Write-Host "[2/6] 解压文件..." -ForegroundColor Yellow
try {
    tar -xzvf $Archive -C $AppDir --strip-components=1
    Write-Host "文件解压完成"
} catch {
    Write-Host "错误: 解压失败，请确保安装了 tar 工具" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Python
Write-Host "[3/6] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python 版本: $pythonVersion"
} catch {
    Write-Host "错误: 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/"
    Read-Host "按回车键退出"
    exit 1
}

# 安装 Python 依赖
Write-Host "[4/6] 安装 Python 依赖..." -ForegroundColor Yellow
Set-Location "$AppDir\web\backend"
try {
    pip install -r requirements.txt
    Write-Host "Python 依赖安装完成"
} catch {
    Write-Host "警告: 依赖安装可能有问题，请检查" -ForegroundColor Yellow
}

# 创建环境变量文件
Write-Host "[5/6] 创建环境变量文件..." -ForegroundColor Yellow
$EnvFile = "$AppDir\web\backend\.env"
if (-not (Test-Path $EnvFile)) {
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
    Write-Host "已创建 .env 文件，请配置实际值"
}

# 创建启动脚本
Write-Host "[6/6] 创建启动脚本..." -ForegroundColor Yellow
$StartScript = "$AppDir\start.bat"
@"
@echo off
cd /d $AppDir\web\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
"@ | Out-File -FilePath $StartScript -Encoding ASCII
Write-Host "启动脚本已创建: $StartScript"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "应用目录: $AppDir"
Write-Host "启动方式: 双击运行 $StartScript"
Write-Host ""
Write-Host "或者使用命令:"
Write-Host "  cd $AppDir\web\backend"
Write-Host "  python -m uvicorn main:app --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "访问地址: http://服务器IP:8000"
Write-Host "API文档: http://服务器IP:8000/docs"
Write-Host ""
Read-Host "按回车键退出"
