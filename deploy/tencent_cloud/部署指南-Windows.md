# TaskPlatform Windows 生产部署指南

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [配置说明](#配置说明)
4. [启动服务](#启动服务)
5. [日常维护](#日常维护)
6. [故障排除](#故障排除)

---

## 系统要求

- Windows 10/11 或 Windows Server 2016+
- Python 3.8 或更高版本
- 至少 2GB RAM
- 至少 5GB 可用磁盘空间

---

## 安装步骤

### 步骤 1: 安装 Python

1. 下载 Python: https://www.python.org/downloads/
2. 运行安装程序，**务必勾选 "Add Python to PATH"**
3. 验证安装：打开 PowerShell 运行 `python --version`

### 步骤 2: 安装 Nginx（可选但推荐）

1. 下载 nginx for Windows: http://nginx.org/en/download.html
2. 解压到 `C:\nginx`
3. 验证安装：`C:\nginx\nginx.exe -v`

### 步骤 3: 部署项目

将项目文件复制到服务器：

```powershell
# 创建部署目录
mkdir C:\taskplatform

# 复制项目文件到 C:\taskplatform
# 方式1：使用 Git（推荐）
cd C:\taskplatform
git clone https://gitee.com/olouha/task-platform.git .

# 方式2：直接复制文件
# 将项目文件直接复制到 C:\taskplatform
```

### 步骤 4: 配置环境变量

1. 复制环境变量模板：
```powershell
copy C:\taskplatform\web\backend\.env.example C:\taskplatform\web\backend\.env
```

2. 编辑 `.env` 文件，填写实际配置：

```env
# 数据库配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI服务配置
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key

# 应用配置
LOG_LEVEL=INFO
```

### 步骤 5: 配置 Nginx（如果安装了 nginx）

1. 复制 nginx 配置：
```powershell
copy deploy\tencent_cloud\nginx-windows.conf C:\nginx\conf\nginx.conf
```

2. 测试 nginx 配置：
```powershell
C:\nginx\nginx.exe -t
```

---

## 配置说明

### 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 8000 | FastAPI 后端服务 |
| Nginx | 80 | HTTP 反向代理 |

### 目录结构

```
C:\taskplatform\
├── web\
│   └── backend\           # 后端代码
│       ├── main.py       # 入口文件
│       ├── .env          # 环境配置
│       └── requirements.txt
├── logs\                 # 日志目录
│   ├── backend.log       # 后端标准日志
│   └── backend-error.log # 后端错误日志
├── pids\                 # 进程 ID 文件
│   └── backend.pid
└── deploy\               # 部署脚本
    ├── start.ps1         # 启动脚本
    ├── stop.ps1          # 停止脚本
    ├── restart.ps1       # 重启脚本
    └── view-logs.ps1     # 查看日志
```

---

## 启动服务

### 一键启动

在 PowerShell 中运行：

```powershell
cd C:\taskplatform\deploy\tencent_cloud
.\start.ps1
```

启动成功后会显示：

```
========================================
  启动成功！
========================================

访问地址:
  后端 API: http://localhost:8000
  API 文档: http://localhost:8000/docs

日志位置:
  标准日志: C:\taskplatform\logs\backend.log
  错误日志: C:\taskplatform\logs\backend-error.log
```

### 验证服务

打开浏览器访问：
- http://localhost:8000 - API 根路径
- http://localhost:8000/docs - Swagger API 文档

---

## 日常维护

### 启动服务

```powershell
cd C:\taskplatform\deploy\tencent_cloud
.\start.ps1
```

### 停止服务

```powershell
cd C:\taskplatform\deploy\tencent_cloud
.\stop.ps1
```

### 重启服务

```powershell
cd C:\taskplatform\deploy\tencent_cloud
.\restart.ps1
```

### 查看日志

```powershell
cd C:\taskplatform\deploy\tencent_cloud
.\view-logs.ps1
```

选项：
1. 实时查看标准日志
2. 实时查看错误日志
3. 查看全部标准日志
4. 查看全部错误日志

### 更新代码

```powershell
cd C:\taskplatform
git pull

# 重启服务使更新生效
.\deploy\tencent_cloud\restart.ps1
```

---

## 故障排除

### 问题：服务启动失败

1. 检查日志：
```powershell
.\view-logs.ps1
# 选择 "4. 查看全部错误日志"
```

2. 常见原因：
   - 端口被占用：检查 8000 端口是否被其他程序占用
   - Python 依赖缺失：运行 `pip install -r requirements.txt`
   - 环境变量未配置：检查 `.env` 文件是否存在且配置正确

### 问题：端口被占用

查找占用端口的进程：
```powershell
netstat -ano | findstr :8000
```

终止占用端口的进程：
```powershell
taskkill /PID <进程ID> /F
```

### 问题：Nginx 无法启动

1. 检查 nginx 配置：
```powershell
C:\nginx\nginx.exe -t
```

2. 查看 nginx 错误日志：
```powershell
type C:\nginx\logs\error.log
```

### 问题：API 无法访问

1. 检查后端服务是否运行：
```powershell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

2. 测试本地连接：
```powershell
curl http://localhost:8000/health
```

3. 检查防火墙设置

---

## 安全建议

1. **修改默认端口**：生产环境建议使用非标准端口
2. **配置防火墙**：只开放必要的端口
3. **使用 HTTPS**：配置 SSL 证书（使用 Let's Encrypt 或其他）
4. **定期备份**：定期备份数据库和配置文件
5. **更新依赖**：定期更新 Python 依赖包

---

## 联系支持

如有问题，请联系：
- Gitee Issues: https://gitee.com/olouha/task-platform/issues
- 项目负责人: [填写联系人]
