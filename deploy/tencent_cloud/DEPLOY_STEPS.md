# 腾讯云虚拟桌面部署脚本

## 部署步骤

### 1. 打包本地文件（本地 PowerShell）

```powershell
cd "e:\E\任务\task-platform\web\backend"

# 打包需要同步的目录
Compress-Archive -Path "api\*" -DestinationPath "$env:TEMP\api_files.zip" -Force
Compress-Archive -Path "models\*" -DestinationPath "$env:TEMP\models_files.zip" -Force
Compress-Archive -Path "services\*" -DestinationPath "$env:TEMP\services_files.zip" -Force

# 复制到桌面
Copy-Item -Path "$env:TEMP\api_files.zip" -Destination "$env:USERPROFILE\Desktop\"
Copy-Item -Path "$env:TEMP\models_files.zip" -Destination "$env:USERPROFILE\Desktop\"
Copy-Item -Path "$env:TEMP\services_files.zip" -Destination "$env:USERPROFILE\Desktop\"

Write-Host "打包完成！请复制到腾讯云桌面"
```

### 2. 腾讯云虚拟桌面解压并启动

```powershell
# 解压到对应目录
Expand-Archive -Path "$env:USERPROFILE\Desktop\api_files.zip" -DestinationPath "C:\task-platform-main\backend\api" -Force
Expand-Archive -Path "$env:USERPROFILE\Desktop\models_files.zip" -DestinationPath "C:\task-platform-main\backend\models" -Force
Expand-Archive -Path "$env:USERPROFILE\Desktop\services_files.zip" -DestinationPath "C:\task-platform-main\backend\services" -Force

# 验证文件数量
$api_count = (Get-ChildItem C:\task-platform-main\backend\api\*.py | Measure-Object).Count
$models_count = (Get-ChildItem C:\task-platform-main\backend\models\*.py | Measure-Object).Count
$services_count = (Get-ChildItem C:\task-platform-main\backend\services\*.py | Measure-Object).Count
Write-Host "api: $api_count, models: $models_count, services: $services_count"

# 停止旧进程
$process = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($process) {
    Stop-Process -Id $process.OwningProcess -Force
    Write-Host "已停止旧进程"
}

# 启动后端
cd C:\task-platform-main\backend
Start-Process powershell -ArgumentList "-Command","python -m uvicorn main:app --host 0.0.0.0 --port 8080"
Write-Host "后端启动中..."
Start-Sleep 3

# 启动前端
cd C:\task-platform-main\frontend
Start-Process powershell -ArgumentList "-Command","npm run dev -- --host 0.0.0.0 --port 5173"
Write-Host "前端启动中..."
```

## 需要复制的目录结构

```
backend/
├── api/          # API 路由文件
├── models/       # 数据模型文件
├── services/     # 服务层文件
├── data/         # 数据库文件
├── main.py       # 应用入口
└── requirements.txt
```

## 验证部署成功

```powershell
# 后端健康检查
curl http://localhost:8080/health

# 前端访问
# http://localhost:5173
```

## 常见问题

### 端口被占用
```powershell
netstat -ano | findstr :8080
taskkill /PID <进程ID> /F
```

### 模块找不到
检查文件是否正确解压：
```powershell
Get-ChildItem C:\task-platform-main\backend\api\*.py | Measure-Object
```