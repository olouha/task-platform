#!/bin/bash
#
# TaskPlatform Docker 部署脚本
# 适用于腾讯云轻量服务器
#

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_NAME="task-platform"
IMAGE_NAME="task-platform:latest"
CONTAINER_NAME="task-platform"
PORT=8000

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   TaskPlatform Docker 部署${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker 未安装，正在安装...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}Docker 安装完成${NC}"
fi

echo -e "${YELLOW}[1/5] 检查项目目录...${NC}"
if [ ! -d "/root/web/backend" ]; then
    echo -e "${YELLOW}未找到项目，正在解压...${NC}"
    if [ -f "/root/task-platform.tar.gz" ]; then
        cd /root
        tar -xzvf task-platform.tar.gz
    else
        echo -e "${RED}错误: 未找到 task-platform.tar.gz${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}[2/5] 创建 .env 文件...${NC}"
ENV_FILE="/root/web/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'EOF'
# 数据库配置
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-key

# AI服务配置
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-api-key

# 应用配置
PORT=8000
LOG_LEVEL=INFO
EOF
    echo -e "${YELLOW}请编辑 $ENV_FILE 配置环境变量${NC}"
fi

echo -e "${YELLOW}[3/5] 构建 Docker 镜像...${NC}"
cd /root/web/backend
docker build -t $IMAGE_NAME .

echo -e "${YELLOW}[4/5] 停止旧容器...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

echo -e "${YELLOW}[5/5] 启动新容器...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:8000 \
    --env-file $ENV_FILE \
    -v $(pwd)/services/data:/app/services/data \
    -v $(pwd)/services/logs:/app/services/logs \
    --restart unless-stopped \
    $IMAGE_NAME

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "检查服务状态:"
docker ps | grep $CONTAINER_NAME || echo "容器未运行"
echo ""
echo "查看日志:"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo "访问地址: http://localhost:$PORT"
echo "API文档:   http://localhost:$PORT/docs"
