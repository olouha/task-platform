# 腾讯云部署指南

## 方式一：Docker 部署（推荐）

### 1. 服务器安装 Docker

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker
systemctl start docker
systemctl enable docker
```

### 2. 打包项目

本地执行：

```bash
cd e:\E\任务\task-platform

# 复制 Dockerfile 到正确位置（已在项目中）
# 项目结构 web/backend/Dockerfile 已配置

# 打包（不含 node_modules）
tar -czvf task-platform.tar.gz \
  --exclude='web/frontend/node_modules' \
  --exclude='web/backend/__pycache__' \
  --exclude='.git' \
  web/
```

### 3. 上传到服务器

```bash
scp task-platform.tar.gz root@服务器IP:/root/
```

### 4. 服务器执行

```bash
cd /root

# 解压
tar -xzvf task-platform.tar.gz

# 构建 Docker 镜像
cd web/backend
docker build -t task-platform:latest .

# 运行容器
docker run -d \
  --name task-platform \
  -p 8000:8000 \
  -e SUPABASE_URL=https://xxx.supabase.co \
  -e SUPABASE_KEY=your-key \
  -e AI_API_URL=https://api.openai.com/v1 \
  -e AI_API_KEY=sk-your-key \
  -v $(pwd)/services/data:/app/services/data \
  -v $(pwd)/services/logs:/app/services/logs \
  --restart unless-stopped \
  task-platform:latest

# 查看日志
docker logs -f task-platform

# 查看状态
docker ps
```

### 5. 配置 Nginx 反向代理

```bash
# 安装 Nginx
apt install nginx -y

# 复制配置
cp /root/web/backend/deploy/tencent_cloud/nginx.conf /etc/nginx/sites-available/task-platform

# 启用站点
ln -sf /etc/nginx/sites-available/task-platform /etc/nginx/sites-enabled/

# 测试并重载
nginx -t && systemctl reload nginx
```

---

## 方式二：直接运行（无需 Docker）

### 1. 服务器安装 Python 环境

```bash
# 安装 Python 3.11
apt update
apt install -y python3.11 python3.11-venv python3-pip

# 创建虚拟环境
mkdir -p /opt/task-platform
cd /opt/task-platform
python3.11 -m venv venv
```

### 2. 上传并安装

```bash
# 解压项目
tar -xzvf /root/task-platform.tar.gz -C /opt/task-platform

# 安装依赖
cd /opt/task-platform/web/backend
source /opt/task-platform/venv/bin/activate
pip install -r requirements.txt

# 创建 .env 文件
cat > .env << 'EOF'
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-supabase-key
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key
PORT=8000
EOF
```

### 3. 使用 systemd 管理服务

```bash
# 复制服务文件
cp /opt/task-platform/web/backend/deploy/tencent_cloud/task-platform.service /etc/systemd/system/

# 重载 systemd
systemctl daemon-reload

# 启动服务
systemctl start task-platform
systemctl enable task-platform

# 检查状态
systemctl status task-platform
```

---

## 方式三：腾讯云容器部署

### 1. 构建镜像

腾讯云控制台 → 容器镜像服务 → 个人版

```bash
# 登录腾讯云容器镜像
docker login ccr.ccs.tencentyun.com -u your-username

# 打标签
docker tag task-platform:latest ccr.ccs.tencentyun.com/your-namespace/task-platform:v1

# 推送
docker push ccr.ccs.tencentyun.com/your-namespace/task-platform:v1
```

### 2. 创建容器实例

腾讯云控制台 → 容器实例服务

- 镜像：`ccr.ccs.tencentyun.com/your-namespace/task-platform:v1`
- 端口映射：`8000:8000`
- 环境变量：设置 SUPABASE_URL 等

---

## 部署后检查

```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 文档
# 浏览器访问 http://服务器IP:8000/docs

# 查看日志
# Docker 方式
docker logs task-platform

# systemd 方式
journalctl -u task-platform -f
```

---

## 故障排查

| 问题 | 解决方法 |
|------|----------|
| 启动失败 | 检查 `.env` 环境变量配置 |
| 端口被占用 | `lsof -i:8000` 查看占用进程 |
| 数据库连接失败 | 检查 SUPABASE_URL 和 SUPABASE_KEY |
| AI服务无法调用 | 检查 AI_API_URL 和 AI_API_KEY |

---

## 快速部署脚本

服务器上执行：

```bash
cd /root
tar -xzvf task-platform.tar.gz
cd web/backend/deploy/tencent_cloud
chmod +x deploy.sh
./deploy.sh
```

脚本会自动：
1. 安装 Docker
2. 构建镜像
3. 运行容器
4. 配置 Nginx
