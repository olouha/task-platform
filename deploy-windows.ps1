# ============================================
# TaskPlatform Windows 自动部署脚本
# ============================================

# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TaskPlatform Windows 部署脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "请以管理员身份运行此脚本！" -ForegroundColor Red
    pause
    exit 1
}

# 项目配置
$PROJECT_DIR = "C:\taskplatform"
$BACKEND_DIR = "$PROJECT_DIR\web\backend"
$FRONTEND_DIR = "$PROJECT_DIR\web\frontend"
$VENV_DIR = "$PROJECT_DIR\venv"

# ============================================
# 步骤1：安装 Python
# ============================================
Write-Host "步骤1：检查 Python..." -ForegroundColor Yellow

$pythonVersion = python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 未安装，正在下载安装..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" -OutFile "$env:TEMP\python-installer.exe"
    Start-Process -FilePath "$env:TEMP\python-installer.exe" -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "Python 安装完成！" -ForegroundColor Green
} else {
    Write-Host "Python 已安装：$pythonVersion" -ForegroundColor Green
}

# ============================================
# 步骤2：安装 Node.js
# ============================================
Write-Host ""
Write-Host "步骤2：检查 Node.js..." -ForegroundColor Yellow

$nodeVersion = node --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Node.js 未安装，正在下载安装..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://nodejs.org/dist/v20.10.0/node-v20.10.0-x64.msi" -OutFile "$env:TEMP\nodejs-installer.msi"
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "$env:TEMP\nodejs-installer.msi", "/quiet", "/norestart" -Wait
    Write-Host "Node.js 安装完成！" -ForegroundColor Green
} else {
    Write-Host "Node.js 已安装：$nodeVersion" -ForegroundColor Green
}

# ============================================
# 步骤3：创建项目目录
# ============================================
Write-Host ""
Write-Host "步骤3：创建项目目录..." -ForegroundColor Yellow

if (!(Test-Path $PROJECT_DIR)) {
    New-Item -ItemType Directory -Path $PROJECT_DIR -Force | Out-Null
    Write-Host "项目目录已创建：$PROJECT_DIR" -ForegroundColor Green
} else {
    Write-Host "项目目录已存在：$PROJECT_DIR" -ForegroundColor Yellow
}

cd $PROJECT_DIR

# ============================================
# 步骤4：下载代码
# ============================================
Write-Host ""
Write-Host "步骤4：下载代码..." -ForegroundColor Yellow

if (Test-Path ".git") {
    Write-Host "更新现有代码..." -ForegroundColor Yellow
    git fetch origin
    git reset --hard origin/main
} else {
    Write-Host "克隆代码仓库..." -ForegroundColor Yellow
    git clone https://github.com/olouha/task-platform.git .
}

Write-Host "代码下载完成！" -ForegroundColor Green

# ============================================
# 步骤5：安装后端依赖
# ============================================
Write-Host ""
Write-Host "步骤5：安装后端依赖..." -ForegroundColor Yellow

cd $BACKEND_DIR

# 创建虚拟环境
if (!(Test-Path $VENV_DIR)) {
    python -m venv $VENV_DIR
    Write-Host "虚拟环境已创建" -ForegroundColor Green
}

# 激活虚拟环境并安装依赖
& "$VENV_DIR\Scripts\Activate.ps1"

# 使用国内镜像安装
Write-Host "安装 Python 依赖（使用清华镜像）..." -ForegroundColor Yellow
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple fastapi uvicorn[standard] openpyxl pandas pydantic httpx playwright

# 安装 Playwright
Write-Host "安装 Playwright 浏览器..." -ForegroundColor Yellow
python -m playwright install chromium

Write-Host "后端依赖安装完成！" -ForegroundColor Green

# ============================================
# 步骤6：构建前端
# ============================================
Write-Host ""
Write-Host "步骤6：构建前端..." -ForegroundColor Yellow

cd $FRONTEND_DIR

Write-Host "安装 npm 依赖..." -ForegroundColor Yellow
npm install

Write-Host "构建前端..." -ForegroundColor Yellow
npm run build

Write-Host "前端构建完成！" -ForegroundColor Green

# ============================================
# 步骤7：配置防火墙
# ============================================
Write-Host ""
Write-Host "步骤7：配置防火墙..." -ForegroundColor Yellow

try {
    # 检查并添加防火墙规则
    $rule = Get-NetFirewallRule -DisplayName "Allow TaskPlatform API" -ErrorAction SilentlyContinue
    if (-not $rule) {
        New-NetFirewallRule -DisplayName "Allow TaskPlatform API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow | Out-Null
        Write-Host "防火墙规则已添加" -ForegroundColor Green
    } else {
        Write-Host "防火墙规则已存在" -ForegroundColor Green
    }
} catch {
    Write-Host "防火墙配置失败，请手动配置" -ForegroundColor Yellow
}

# ============================================
# 步骤8：创建启动脚本
# ============================================
Write-Host ""
Write-Host "步骤8：创建启动脚本..." -ForegroundColor Yellow

$startScript = @"
cd $BACKEND_DIR
& "$VENV_DIR\Scripts\Activate.ps1"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
"@

$startScript | Out-File "$PROJECT_DIR\start-server.ps1" -Encoding UTF8

Write-Host "启动脚本已创建：$PROJECT_DIR\start-server.ps1" -ForegroundColor Green

# ============================================
# 完成
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "接下来：" -ForegroundColor Yellow
Write-Host "1. 打开 PowerShell，进入项目目录" -ForegroundColor White
Write-Host "   cd $PROJECT_DIR" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 启动服务" -ForegroundColor White
Write-Host "   .\start-server.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 访问：http://140.143.125.234:8000" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  注意：需要在腾讯云控制台添加防火墙规则" -ForegroundColor Yellow
Write-Host "   端口：8000  来源：0.0.0.0/0" -ForegroundColor Gray
Write-Host ""

pause