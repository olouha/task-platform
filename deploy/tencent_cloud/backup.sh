#!/bin/bash
#
# TaskPlatform 数据库备份脚本
# 自动备份所有 .db 文件和配置文件
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
BACKUP_DIR="/opt/taskplatform/backups"
DATA_DIR="/opt/taskplatform/app"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   TaskPlatform 备份脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 创建本次备份目录
BACKUP_SUBDIR="${BACKUP_DIR}/${TIMESTAMP}"
mkdir -p "${BACKUP_SUBDIR}"

echo -e "${YELLOW}[1/4] 备份数据库文件...${NC}"
DB_COUNT=0
for db_file in "${DATA_DIR}"/*.db "${DATA_DIR}"/services/data/*.db; do
    if [ -f "$db_file" ]; then
        FILENAME=$(basename "$db_file")
        echo "备份: $FILENAME"
        cp "$db_file" "${BACKUP_SUBDIR}/"
        DB_COUNT=$((DB_COUNT + 1))
    fi
done
echo "已备份 ${DB_COUNT} 个数据库文件"

echo -e "${YELLOW}[2/4] 备份配置文件...${NC}"
if [ -f "${DATA_DIR}/.env" ]; then
    cp "${DATA_DIR}/.env" "${BACKUP_SUBDIR}/.env"
    echo "备份: .env"
fi

if [ -f "${DATA_DIR}/config.json" ]; then
    cp "${DATA_DIR}/config.json" "${BACKUP_SUBDIR}/config.json"
    echo "备份: config.json"
fi

if [ -d "${DATA_DIR}/services/data" ]; then
    mkdir -p "${BACKUP_SUBDIR}/services_data"
    cp -r "${DATA_DIR}/services/data"/*.json "${BACKUP_SUBDIR}/services_data/" 2>/dev/null || true
    echo "备份: services/data/*.json"
fi

echo -e "${YELLOW}[3/4] 创建压缩包...${NC}"
cd "${BACKUP_DIR}"
tar -czvf "taskplatform_backup_${TIMESTAMP}.tar.gz" "${TIMESTAMP}/"
rm -rf "${BACKUP_SUBDIR}"
echo "压缩包: taskplatform_backup_${TIMESTAMP}.tar.gz"

echo -e "${YELLOW}[4/4] 清理过期备份...${NC}"
find "${BACKUP_DIR}" -name "taskplatform_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete
echo "已清理 ${RETENTION_DAYS} 天前的备份文件"

# 显示备份统计
TOTAL_SIZE=$(du -h "${BACKUP_DIR}/taskplatform_backup_${TIMESTAMP}.tar.gz" | cut -f1)
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "taskplatform_backup_*.tar.gz" | wc -l)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   备份完成${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "备份文件: ${BACKUP_DIR}/taskplatform_backup_${TIMESTAMP}.tar.gz"
echo "文件大小: ${TOTAL_SIZE}"
echo "总备份数: ${BACKUP_COUNT}"
echo ""
