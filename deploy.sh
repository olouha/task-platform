#!/bin/bash
# ============================================
# 腾讯云自动部署脚本
# TaskPlatform - 工程调差计算系统
# ============================================

set -e

# 配置变量
APP_NAME="taskplatform"
APP_DIR="/opt/taskplatform"
BACKEND_DIR="$APP_DIR/web/backend"
FRONTEND_DIR="$APP_DIR/web/frontend"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log "检测到系统: $OS $OS_VERSION"
    else
        error "无法检测操作系统"
    fi
}

# 安装依赖
install_dependencies() {
    log "安装系统依赖..."

    case $OS in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv nodejs npm nginx git supervisor
            ;;
        centos|rhel|rocky|almalinux)
            sudo yum install -y python3 python3-pip nodejs npm nginx git supervisor
            ;;
        *)
            error "不支持的操作系统: $OS"
            ;;
    esac
}

# 创建目录结构
setup_directories() {
    log "创建目录结构..."
    sudo mkdir -p $APP_DIR $LOG_DIR
    sudo chown -R $USER:$USER $APP_DIR
}

# 克隆或更新代码
setup_code() {
    if [ -d "$APP_DIR/.git" ]; then
        log "更新代码..."
        cd $APP_DIR
        git fetch origin
        git reset --hard origin/main
    else
        log "克隆代码仓库..."
        # 请替换为你的GitHub仓库地址
        read -p "请输入你的Git仓库地址 (例如: https://github.com/username/repo.git): " GIT_REPO
        git clone $GIT_REPO $APP_DIR || {
            # 如果克隆失败，让用户手动上传代码
            warn "克隆失败，请手动上传代码到 $APP_DIR"
        }
    fi
}

# 设置Python虚拟环境
setup_python() {
    log "设置Python虚拟环境..."

    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv $VENV_DIR
    fi

    source $VENV_DIR/bin/activate

    cd $BACKEND_DIR
    pip install --upgrade pip
    pip install -r requirements.txt || pip install fastapi uvicorn[standard] openpyxl pandas pandas pydantic httpx playwright

    # 安装Playwright浏览器
    playwright install chromium
}

# 构建前端
build_frontend() {
    log "构建前端..."
    cd $FRONTEND_DIR

    if [ -f "package.json" ]; then
        npm install
        npm run build
    else
        warn "前端目录不存在或缺少package.json"
    fi
}

# 配置Nginx
setup_nginx() {
    log "配置Nginx..."

    cat > /tmp/taskplatform.conf << 'EOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /opt/taskplatform/web/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    # WebSocket
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

    sudo cp /tmp/taskplatform.conf /etc/nginx/sites-available/taskplatform

    # 创建软链接
    sudo ln -sf /etc/nginx/sites-available/taskplatform /etc/nginx/sites-enabled/

    # 删除默认配置
    sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

    # 测试Nginx配置
    sudo nginx -t
    sudo systemctl reload nginx
}

# 配置Supervisor（进程守护）
setup_supervisor() {
    log "配置Supervisor..."

    cat > /tmp/taskplatform.conf << 'EOF'
[program:taskplatform-backend]
command=/opt/taskplatform/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
directory=/opt/taskplatform/web/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/taskplatform/logs/backend.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/opt/taskplatform/venv/bin"
EOF

    sudo cp /tmp/taskplatform.conf /etc/supervisor/conf.d/taskplatform.conf

    # 重启Supervisor
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl restart taskplatform-backend
}

# 设置防火墙
setup_firewall() {
    log "配置防火墙..."

    if command -v ufw &> /dev/null; then
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
    fi

    if command -v firewall-cmd &> /dev/null; then
        sudo firewall-cmd --permanent --add-service=http
        sudo firewall-cmd --permanent --add-service=https
        sudo firewall-cmd --reload
    fi
}

# 主流程
main() {
    log "========================================"
    log "  TaskPlatform 腾讯云部署脚本"
    log "========================================"

    detect_os
    install_dependencies
    setup_directories
    setup_code
    setup_python
    build_frontend
    setup_nginx
    setup_supervisor
    setup_firewall

    log ""
    log "========================================"
    log "  部署完成！"
    log "========================================"
    log ""
    log "服务地址: http://$(curl -s ifconfig.me)"
    log "后端日志: tail -f $LOG_DIR/backend.log"
    log "重启服务: sudo supervisorctl restart taskplatform-backend"
    log ""
    log "更新代码后执行: bash update.sh"
}

# 执行主流程
main "$@"