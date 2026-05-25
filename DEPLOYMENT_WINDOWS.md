# ============================================
# TaskPlatform Windows 部署方案
# 腾讯云轻量应用服务器（Windows版）
# ============================================

## 前置要求

1. 已安装 Python 3.8+ （如果没有会自动安装）
2. 已安装 Node.js （如果没有会自动安装）

---

## 一、自动部署脚本（推荐）

### 方法1：使用 PowerShell（一键部署）

1. 远程桌面连接到服务器：
   - 打开「运行」→ 输入 `mstsc` → 输入 `140.143.125.234`
   - 用户名：`Administrator`
   - 密码：`Panhui199261*`

2. 在服务器上打开 PowerShell（管理员权限）

3. 复制粘贴以下命令：

```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

# 下载并运行部署脚本
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/olouha/task-platform/main/deploy-windows.ps1" -OutFile "deploy-windows.ps1"
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\deploy-windows.ps1
```

---

## 二、手动部署步骤

### 步骤1：安装 Python

```powershell
# 下载 Python
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" -OutFile "python-installer.exe"

# 静默安装（添加到PATH）
Start-Process -FilePath ".\python-installer.exe" -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
```

验证安装：
```powershell
python --version
pip --version
```

### 步骤2：安装 Node.js

```powershell
# 下载 Node.js
Invoke-WebRequest -Uri "https://nodejs.org/dist/v20.10.0/node-v20.10.0-x64.msi" -OutFile "nodejs-installer.msi"

# 静默安装
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "nodejs-installer.msi", "/quiet", "/norestart" -Wait
```

验证安装：
```powershell
node --version
npm --version
```

### 步骤3：创建项目目录

```powershell
cd C:\
mkdir taskplatform
cd taskplatform
```

### 步骤4：下载代码

```powershell
# 方法A：使用 Git（推荐）
git clone https://github.com/olouha/task-platform.git .

# 方法B：直接下载ZIP
Invoke-WebRequest -Uri "https://github.com/olouha/task-platform/archive/refs/heads/main.zip" -OutFile "code.zip"
Expand-Archive -Path "code.zip" -DestinationPath "." -Force
Move-Item -Path "taskplatform-main\*" -Destination "." -Force
Remove-Item -Path "taskplatform-main", "code.zip" -Recurse -Force
```

### 步骤5：安装后端依赖

```powershell
cd web\backend

# 安装依赖
pip install fastapi uvicorn[standard] openpyxl pandas pydantic httpx playwright

# 安装 Playwright 浏览器
python -m playwright install chromium
```

### 步骤6：构建前端

```powershell
cd ..\frontend

# 安装依赖
npm install

# 构建
npm run build
```

### 步骤7：启动后端服务

```powershell
cd ..\backend

# 启动服务（后台运行）
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" -WindowStyle Hidden

# 或者前台运行（用于测试）
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 步骤8：打开防火墙端口

```powershell
# 允许 HTTP 端口
New-NetFirewallRule -DisplayName "Allow HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow

# 允许 API 端口
New-NetFirewallRule -DisplayName "Allow API" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### 步骤9：配置腾讯云安全组

登录 [腾讯云控制台](https://console.cloud.tencent.com/)：

1. 进入「轻量应用服务器」→「防火墙」
2. 添加规则：
   - 协议：TCP
   - 端口：8000
   - 来源：0.0.0.0/0

---

## 三、验证部署

访问：
- 前端：`http://140.143.125.234:8000`（如果配置了Nginx）
- API：`http://140.143.125.234:8000/api/building-adjustment/rules`

---

## 四、设置为Windows服务（开机自启）

### 使用 NSSM（推荐）

```powershell
# 下载 NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "nssm.zip"
Expand-Archive -Path "nssm.zip" -DestinationPath "C:\nssm" -Force

# 安装服务
C:\nssm\nssm-2.24\win64\nssm install TaskPlatformBackend

# 配置服务
C:\nssm\nssm-2.24\win64\nssm set TaskPlatformBackend Application C:\taskplatform\venv\Scripts\python.exe
C:\nssm\nssm-2.24\win64\nssm set TaskPlatformBackend AppParameters "-m uvicorn main:app --host 0.0.0.0 --port 8000"
C:\nssm\nssm-2.24\win64\nssm set TaskPlatformBackend AppDirectory C:\taskplatform\web\backend

# 启动服务
C:\nssm\nssm-2.24\win64\nssm start TaskPlatformBackend
```

---

## 五、常见问题

### Q1: PowerShell 提示无法执行脚本
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: pip 安装失败
使用国内镜像：
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q3: 端口被占用
```powershell
# 查看端口占用
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

---

## 六、更新代码

```powershell
cd C:\taskplatform
git pull

# 更新后端依赖
cd web\backend
pip install -r requirements.txt

# 更新前端
cd ..\frontend
npm install
npm run build

# 重启服务
net stop TaskPlatformBackend
net start TaskPlatformBackend
```