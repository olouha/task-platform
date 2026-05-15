# Railway 部署问题排查日志

## 问题概述
应用部署到 Railway 后返回 502 错误（Application failed to respond）

## 环境信息
- 平台: Railway (https://task-platform-production-a96f.up.railway.app)
- 区域: ap-southeast-1 (新加坡)
- 构建器: NIXPACKS -> DOCKERFILE
- 项目路径: web/backend

## 已尝试的修复

### 尝试 1: 简化 Railway.toml
**时间**: 2025-05-15
**变更**: 移除冗余配置
**结果**: ❌ 502 错误仍然存在

### 尝试 2: 添加 __init__.py
**时间**: 2025-05-15
**变更**: 添加 `api/__init__.py`, `models/__init__.py`, `services/__init__.py`
**原因**: Python 包识别问题
**结果**: ❌ 502 错误仍然存在

### 尝试 3: 构建阶段启动服务器错误
**时间**: 2025-05-15
**错误**: `ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8000)`
**原因**: buildCommand 中包含了启动命令
**结果**: ❌ 构建失败

### 尝试 4: 移除 buildCommand
**时间**: 2025-05-15
**变更**: 让 Nixpacks 自动检测 requirements.txt
**结果**: ❌ 502 错误仍然存在

### 尝试 5: 切换到 Dockerfile 构建器
**时间**: 2025-05-15 16:02
**变更**: 添加 Dockerfile，切换到 DOCKERFILE 构建器
**结果**: ⏳ 待验证

## 项目结构
```
task-platform/
├── Railway.toml          # 根目录配置
├── Dockerfile            # Docker 配置
├── RAILWAY_DEBUG.md      # 本文件
├── web/
│   └── backend/
│       ├── Railway.toml  # 子目录配置（已废弃）
│       ├── main.py       # FastAPI 入口
│       ├── requirements.txt
│       ├── api/          # API 路由
│       ├── models/       # 数据模型
│       └── services/     # 业务逻辑
```

## 当前配置

### Railway.toml (根目录)
```toml
[railway]
name = "task-platform-backend"
region = "ap-southeast-1"

[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python -m uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
```

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app/web/backend

COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web/backend .

EXPOSE $PORT

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

### requirements.txt
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
playwright>=1.40.0
openpyxl>=3.1.0
pydantic>=2.0.0
```

### main.py 健康检查
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## 本地测试结果
- ✅ `import main` - 成功
- ✅ `from api import projects` - 成功
- ✅ `import models.schemas` - 成功
- ✅ `uvicorn main:app` - 启动成功

## 问题排查清单

- [ ] Railway 是否正确识别 web/backend 为工作目录？
- [ ] requirements.txt 是否在正确位置？
- [ ] PORT 环境变量是否正确传递？
- [ ] 是否有网络/防火墙问题？
- [ ] Railway 日志中是否有更多错误信息？
- [x] Dockerfile 配置正确性
- [ ] 需要查看 Build Logs 和 Runtime Logs

## 下一步
1. ⏳ 等待 Railway 使用 Dockerfile 重新部署
2. 查看 Railway 详细部署日志（Build Logs / Runtime Logs）
3. 如果成功，测试健康检查端点
4. 如果失败，根据详细日志调整配置

## 最近提交
- `192f8d7` - Fix Railway deployment - switch to Dockerfile builder