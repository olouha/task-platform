#!/bin/bash
#
# TaskPlatform 一键部署脚本
# 适用于腾讯云轻量应用服务器
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
APP_DIR="/opt/taskplatform"
SERVICE_NAME="taskplatform"
BACKEND_PORT=8001
NGINX_CONFIG="/etc/nginx/sites-available/${SERVICE_NAME}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   TaskPlatform 部署脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 1. 创建目录结构
echo -e "${YELLOW}[1/7] 创建目录结构...${NC}"
mkdir -p "${APP_DIR}/app"
mkdir -p "${APP_DIR}/frontend/dist"
mkdir -p "${APP_DIR}/venv"
mkdir -p "${APP_DIR}/logs"
echo "目录创建完成: ${APP_DIR}"

# 2. 检测Python并安装系统依赖
echo -e "${YELLOW}[2/7] 检测Python环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "Python版本: $PYTHON_VERSION"
else
    echo -e "${RED}错误: 未找到 python3，请先安装${NC}"
    echo "Ubuntu/Debian: apt install python3 python3-venv python3-pip"
    echo "CentOS: yum install python3 python3-pip"
    exit 1
fi

echo -e "${YELLOW}[3/7] 安装系统依赖...${NC}"
if command -v apt &> /dev/null; then
    apt update -qq
    apt install -y -qq nginx redis-server curl
elif command -v yum &> /dev/null; then
    yum install -y nginx redis curl
fi
echo "系统依赖安装完成"

# 3. 创建Python虚拟环境
echo -e "${YELLOW}[4/7] 创建Python虚拟环境...${NC}"
if [ ! -f "${APP_DIR}/venv/bin/python" ]; then
    python3 -m venv "${APP_DIR}/venv"
    echo "虚拟环境创建完成"
else
    echo "虚拟环境已存在"
fi

# 4. 复制项目文件
echo -e "${YELLOW}[5/7] 复制项目文件...${NC}"
if [ -f "/root/task-platform.tar.gz" ]; then
    echo "解压项目文件..."
    tar -xzvf /root/task-platform.tar.gz -C "${APP_DIR}/app" --strip-components=1
elif [ -d "/root/web" ]; then
    echo "复制web目录..."
    cp -r /root/web/* "${APP_DIR}/app/"
else
    echo -e "${YELLOW}警告: 未找到项目文件，请手动复制到 ${APP_DIR}/app${NC}"
fi

# 5. 安装Python依赖
echo -e "${YELLOW}[6/7] 安装Python依赖...${NC}"
cd "${APP_DIR}/app"
source "${APP_DIR}/venv/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install gunicorn -q
deactivate
echo "Python依赖安装完成"

# 6. 创建环境变量文件
echo -e "${YELLOW}[7/7] 配置环境变量...${NC}"
if [ ! -f "${APP_DIR}/app/.env" ]; then
    cat > "${APP_DIR}/app/.env" << 'EOF'
# 数据库
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# AI服务
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key

# 应用配置
LOG_LEVEL=INFO
EOF
    echo "环境变量文件已创建: ${APP_DIR}/app/.env"
    echo -e "${YELLOW}请编辑 ${APP_DIR}/app/.env 配置实际值${NC}"
fi

# 配置Nginx
echo -e "${YELLOW}配置Nginx...${NC}"
cp "deploy/tencent_cloud/nginx.conf" "${NGINX_CONFIG}"
ln -sf "${NGINX_CONFIG}" /etc/nginx/sites-enabled/
nginx -t

# 配置systemd服务
echo -e "${YELLOW}配置systemd服务...${NC}"
cp "deploy/tencent_cloud/task-platform.service" "/etc/systemd/system/${SERVICE_NAME}.service"

# 创建日志目录
mkdir -p "${APP_DIR}/logs"
chmod 755 "${APP_DIR}/logs"

# 启动服务
echo -e "${YELLOW}启动服务...${NC}"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl enable nginx
systemctl restart ${SERVICE_NAME}
systemctl reload nginx

# 检查状态
sleep 3
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "服务状态:"
    systemctl status ${SERVICE_NAME} --no-pager
    echo ""
    echo "访问地址: http://服务器IP"
    echo "API文档: http://服务器IP/docs"
    echo ""
    echo "常用命令:"
    echo "  查看状态: systemctl status ${SERVICE_NAME}"
    echo "  查看日志: journalctl -u ${SERVICE_NAME} -f"
    echo "  重启服务: systemctl restart ${SERVICE_NAME}"
else
    echo -e "${RED}服务启动失败，请检查日志：${NC}"
    journalctl -u ${SERVICE_NAME} --no-pager -n 30
    exit 1
fi
