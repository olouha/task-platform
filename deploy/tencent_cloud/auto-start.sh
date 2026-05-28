#!/bin/bash
#
# TaskPlatform 启动脚本
# 自动启动 Docker 容器或直接运行服务
#

set -e

PROJECT_NAME="task-platform"
IMAGE_NAME="task-platform:latest"
CONTAINER_NAME="task-platform"
PORT=8000
PROJECT_DIR="/root/task-platform"

echo "========================================"
echo "  TaskPlatform 自动启动"
echo "========================================"

# 检查 Docker 是否可用
check_docker() {
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        return 0
    fi
    return 1
}

# 启动 Docker 容器
start_docker() {
    echo "[Docker 模式]"

    # 检查镜像是否存在
    if docker image inspect $IMAGE_NAME &> /dev/null; then
        echo "使用现有镜像启动..."

        # 停止旧容器
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true

        # 启动新容器
        docker run -d \
            --name $CONTAINER_NAME \
            -p $PORT:8000 \
            --env-file $PROJECT_DIR/web/backend/.env \
            -v $PROJECT_DIR/web/backend/services/data:/app/services/data \
            -v $PROJECT_DIR/web/backend/services/logs:/app/services/logs \
            --restart unless-stopped \
            $IMAGE_NAME

        echo "容器已启动: $CONTAINER_NAME"
    else
        echo "Docker 镜像不存在，请先构建镜像"
        exit 1
    fi
}

# 直接运行 Python 服务
start_python() {
    echo "[Python 模式]"

    cd $PROJECT_DIR/web/backend

    # 检查虚拟环境
    if [ -d "$PROJECT_DIR/venv" ]; then
        source $PROJECT_DIR/venv/bin/activate
    fi

    # 创建 systemd 服务
    cat > /etc/systemd/system/$PROJECT_NAME.service << EOF
[Unit]
Description=TaskPlatform FastAPI Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR/web/backend
Environment="PATH=$PROJECT_DIR/venv/bin"
EnvironmentFile=$PROJECT_DIR/web/backend/.env
ExecStart=$PROJECT_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 启用服务
    systemctl daemon-reload
    systemctl enable $PROJECT_NAME
    systemctl start $PROJECT_NAME

    echo "服务已启用: $PROJECT_NAME"
}

# 主逻辑
main() {
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        echo "错误: 项目目录不存在 $PROJECT_DIR"
        exit 1
    fi

    # 检查 .env 文件
    if [ ! -f "$PROJECT_DIR/web/backend/.env" ]; then
        echo "警告: .env 文件不存在，创建默认配置..."
        cat > $PROJECT_DIR/web/backend/.env << 'EOF'
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-key
AI_API_URL=https://api.openai.com/v1
AI_API_KEY=sk-your-key
PORT=8000
LOG_LEVEL=INFO
EOF
    fi

    # 根据环境选择启动方式
    if check_docker; then
        start_docker
    else
        start_python
    fi

    echo ""
    echo "========================================"
    echo "  启动完成！"
    echo "========================================"
    echo "访问地址: http://localhost:$PORT"
    echo "API文档:   http://localhost:$PORT/docs"
    echo ""
    echo "查看状态: systemctl status $PROJECT_NAME"
    echo "查看日志: journalctl -u $PROJECT_NAME -f"
}

main
