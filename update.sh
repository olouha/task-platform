#!/bin/bash
# ============================================
# 代码更新脚本
# 用于更新代码后重启服务
# ============================================

set -e

APP_DIR="/opt/taskplatform"
VENV_DIR="/opt/taskplatform/venv"
LOG_DIR="$APP_DIR/logs"

# 颜色输出
GREEN='\033[0;32m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[UPDATE]${NC} $1"
}

cd $APP_DIR

# 1. 拉取最新代码
log "拉取最新代码..."
git fetch origin
git reset --hard origin/main

# 2. 更新后端依赖
log "更新后端依赖..."
source $VENV_DIR/bin/activate
cd web/backend
pip install -r requirements.txt

# 3. 重新构建前端
log "重新构建前端..."
cd ../frontend
npm install
npm run build

# 4. 重启后端服务
log "重启后端服务..."
sudo supervisorctl restart taskplatform-backend

log "更新完成！"
log "查看日志: tail -f $LOG_DIR/backend.log"