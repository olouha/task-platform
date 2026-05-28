# TaskPlatform 腾讯云部署指南

## 概述

本文档介绍如何在腾讯云轻量应用服务器上部署 TaskPlatform。

## 快速部署

### 1. 打包项目（本地执行）

```bash
cd e:/E/任务/task-platform

# 打包（不含 node_modules 和缓存）
tar -czvf task-platform.tar.gz \
  --exclude='web/frontend/node_modules' \
  --exclude='web/frontend/.next' \
  --exclude='web/backend/__pycache__' \
  --exclude='.git' \
  web/
```

### 2. 上传到服务器

```bash
scp task-platform.tar.gz root@服务器IP:/root/
```

### 3. 一键部署（服务器执行）

```bash
cd /root
tar -xzvf task-platform.tar.gz
cd web/backend/deploy/tencent_cloud
chmod +x deploy.sh backup.sh
./deploy.sh
```

脚本会自动：
1. 创建目录结构 (`/opt/taskplatform`)
2. 安装系统依赖 (nginx, redis)
3. 创建 Python 虚拟环境
4. 安装 Python 依赖
5. 配置 Nginx 反向代理
6. 配置 systemd 服务
7. 启动服务并检查状态

---

## 手动部署步骤

### 1. 服务器环境准备

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础软件
apt install -y python3 python3-venv python3-pip nginx redis-server curl
```

### 2. 创建目录结构

```bash
mkdir -p /opt/taskplatform/{app,frontend/dist,venv,logs}
```

### 3. 部署后端

```bash
cd /opt/taskplatform/app

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install fastapi uvicorn[standard] python-dotenv pydantic

# 复制项目文件
# (从 tar 包解压或直接复制)

# 创建环境变量
cat > .env << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key
LOG_LEVEL=INFO
EOF
```

### 4. 配置 Nginx

```bash
# 复制 Nginx 配置
cp /opt/taskplatform/app/web/backend/deploy/tencent_cloud/nginx.conf \
   /etc/nginx/sites-available/taskplatform

# 启用站点
ln -sf /etc/nginx/sites-available/taskplatform /etc/nginx/sites-enabled/

# 测试并重载
nginx -t && systemctl reload nginx
```

### 5. 配置 systemd 服务

```bash
# 复制服务文件
cp /opt/taskplatform/app/web/backend/deploy/tencent_cloud/task-platform.service \
   /etc/systemd/system/taskplatform.service

# 重载并启动
systemctl daemon-reload
systemctl enable taskplatform
systemctl start taskplatform
```

### 6. 部署前端

```bash
# 构建前端
cd /opt/taskplatform/app/web/frontend
npm install
npm run build

# 复制到部署目录
cp -r dist/* /opt/taskplatform/frontend/dist/
```

---

## 验证部署

### 健康检查

```bash
# 检查服务状态
systemctl status taskplatform

# 健康检查端点
curl http://localhost:8001/health

# Nginx 状态
systemctl status nginx
```

### 访问测试

- 访问地址: `http://服务器IP`
- API 文档: `http://服务器IP/docs`
- 健康检查: `http://服务器IP/health`

### 日志查看

```bash
# systemd 日志
journalctl -u taskplatform -f

# Nginx 日志
tail -f /var/log/nginx/taskplatform_access.log
tail -f /var/log/nginx/taskplatform_error.log

# 应用日志
tail -f /opt/taskplatform/logs/stdout.log
tail -f /opt/taskplatform/logs/stderr.log
```

---

## 常用命令

### 服务管理

```bash
# 启动服务
systemctl start taskplatform

# 停止服务
systemctl stop taskplatform

# 重启服务
systemctl restart taskplatform

# 查看状态
systemctl status taskplatform

# 重载配置
systemctl reload taskplatform
```

### Nginx 管理

```bash
# 检查配置
nginx -t

# 重载配置
systemctl reload nginx

# 重启 Nginx
systemctl restart nginx
```

### 日志管理

```bash
# 查看实时日志
journalctl -u taskplatform -f

# 查看最近 100 行
journalctl -u taskplatform -n 100

# 查看错误日志
journalctl -u taskplatform -p err -n 50
```

---

## 定时备份配置

### 创建定时任务

```bash
# 编辑 crontab
crontab -e

# 添加每日凌晨 2 点执行备份
0 2 * * * /opt/taskplatform/app/web/backend/deploy/tencent_cloud/backup.sh >> /opt/taskplatform/logs/backup.log 2>&1
```

### 手动执行备份

```bash
# 运行备份脚本
/opt/taskplatform/app/web/backend/deploy/tencent_cloud/backup.sh

# 查看备份文件
ls -lh /opt/taskplatform/backups/
```

### 备份内容

- 所有 `.db` 数据库文件
- `.env` 环境变量文件
- `config.json` 配置文件
- `services/data/*.json` 数据文件

### 备份保留策略

- 自动清理 7 天前的备份
- 可在 `backup.sh` 中修改 `RETENTION_DAYS` 变量调整

---

## 故障排查

| 问题 | 解决方法 |
|------|----------|
| 服务启动失败 | `journalctl -u taskplatform -n 50` 查看日志 |
| 端口被占用 | `lsof -i:8001` 查看占用进程 |
| 数据库连接失败 | 检查 `SUPABASE_URL` 和 `SUPABASE_KEY` |
| AI 服务无法调用 | 检查 `AI_API_URL` 和 `AI_API_KEY` |
| Nginx 502 错误 | 检查后端服务是否运行 `systemctl status taskplatform` |
| 前端 404 | 检查 `/opt/taskplatform/frontend/dist` 目录是否存在 |

### 快速修复

```bash
# 重启所有服务
systemctl restart taskplatform && systemctl reload nginx

# 检查端口监听
netstat -tlnp | grep -E '8001|80'

# 检查防火墙
ufw status
```

---

## 目录结构

```
/opt/taskplatform/
├── app/                    # 应用代码
│   ├── main.py            # FastAPI 入口
│   ├── .env               # 环境变量
│   └── web/
│       ├── backend/       # 后端代码
│       └── frontend/      # 前端代码
├── frontend/dist/         # 前端构建产物
├── venv/                  # Python 虚拟环境
├── logs/                  # 日志目录
│   ├── stdout.log
│   └── stderr.log
└── backups/               # 数据库备份
    └── taskplatform_backup_YYYYMMDD_HHMMSS.tar.gz
```
