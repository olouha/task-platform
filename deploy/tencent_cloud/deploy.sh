#!/bin/bash
#
# TaskPlatform 一键部署脚本
# 适用于腾讯云虚拟桌面/轻量服务器
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/root/task-platform"
SERVICE_NAME="task-platform"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   TaskPlatform 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检测Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 python3${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/7] 检查Python版本...${NC}"
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "Python版本: $PYTHON_VERSION"

# 创建目录
echo -e "${YELLOW}[2/7] 创建项目目录...${NC}"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 安装系统依赖
echo -e "${YELLOW}[3/7] 安装系统依赖...${NC}"
apt update -qq
apt install -y -qq python3-pip python3-venv nginx redis-server

# 创建虚拟环境
echo -e "${YELLOW}[4/7] 创建Python虚拟环境...${NC}"
python3 -m venv venv
source venv/bin/activate

# 复制项目文件
echo -e "${YELLOW}[5/7] 复制项目文件...${NC}"
# 检查是否已有压缩包
if [ -f /root/task-platform.tar.gz ]; then
    echo "解压项目文件..."
    tar -xzvf /root/task-platform.tar.gz -C "$PROJECT_DIR"
fi

# 安装Python依赖
echo -e "${YELLOW}[6/7] 安装Python依赖...${NC}"
cd "$PROJECT_DIR/web/backend"
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 配置环境变量
echo -e "${YELLOW}[7/7] 配置环境变量...${NC}"
cat > .env << 'EOF'
# 数据库
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI服务
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key

# 应用配置
PORT=8000
LOG_LEVEL=INFO
EOF

echo -e "${GREEN}依赖安装完成！${NC}"
echo ""
echo -e "${YELLOW}请编辑 $PROJECT_DIR/web/backend/.env 文件配置环境变量${NC}"
echo ""

# 创建systemd服务
echo -e "${YELLOW}创建systemd服务...${NC}"
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=TaskPlatform FastAPI Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${PROJECT_DIR}/web/backend
Environment="PATH=${PROJECT_DIR}/venv/bin"
EnvironmentFile=${PROJECT_DIR}/web/backend/.env
ExecStart=${PROJECT_DIR}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

# 检查状态
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "服务状态:"
    systemctl status ${SERVICE_NAME} --no-pager
    echo ""
    echo "访问地址: http://localhost:8000"
    echo "API文档: http://localhost:8000/docs"
else
    echo -e "${RED}服务启动失败，请检查日志：${NC}"
    journalctl -u ${SERVICE_NAME} --no-pager -n 20
fi
