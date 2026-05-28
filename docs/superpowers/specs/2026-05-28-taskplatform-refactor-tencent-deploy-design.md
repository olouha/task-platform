# TaskPlatform 重构与腾讯云部署设计方案

**日期**: 2026-05-28
**状态**: 待审核
**版本**: v1.0

---

## 1. 项目背景与目标

### 1.1 当前问题

| 问题 | 现状 |
|------|------|
| services 目录臃肿 | 100+ 文件，大量重复的 `fetch_*.py` 变体 |
| 部署问题 | Railway 部署失败（502 错误） |
| 代码组织混乱 | 功能边界不清晰，难以维护 |

### 1.2 目标

1. **代码质量改进**：重组 `web/backend/services/` 目录，删除废弃文件，统一服务入口
2. **迁移部署**：从 Railway 迁移到腾讯云轻量应用服务器
3. **功能不变**：确保重构后所有现有功能正常运行

### 1.3 约束条件

- 功能保持不变
- 使用公网 IP 直接访问（无域名）
- 采用 SQLite 本地存储
- 前端使用 Nginx 静态服务

---

## 2. 代码重构设计

### 2.1 重构原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个服务文件只负责一个功能 |
| **删除废弃** | 移除版本变体文件（如 `*_v2.py`、`*_补充.py`、`*_v3.py`） |
| **统一入口** | 相同功能的服务合并为一个入口文件 |
| **保留可追溯** | 被删文件的关键逻辑确保有替代实现 |

### 2.2 目标目录结构

```
web/backend/
├── main.py                          # FastAPI 应用入口
├── api/                             # API 路由层 (保持不变)
│   ├── __init__.py
│   ├── projects.py
│   ├── materials.py
│   ├── adjustments.py
│   ├── yantai_prices.py
│   ├── adjustment_rules.py
│   ├── cost_reference.py
│   ├── cost_history.py
│   ├── yantai_db.py
│   └── ...
├── services/                        # 业务逻辑层 (重构目标)
│   ├── __init__.py                  # 统一导出
│   ├── config.py                    # 配置管理
│   ├── database.py                  # 数据库连接
│   ├── rate_limiter.py              # 限流器
│   ├── websocket_manager.py         # WebSocket 管理
│   │
│   ├── price/                       # 价格相关服务
│   │   ├── __init__.py
│   │   ├── scraper.py               # 价格抓取主服务
│   │   ├── scheduler.py             # 定时调度
│   │   ├── yantai_db.py             # 烟台钢筋数据库
│   │   └── ocr_parse.py             # OCR 解析
│   │
│   ├── adjustment/                  # 调差计算服务
│   │   ├── __init__.py
│   │   ├── calculator.py            # 调差计算引擎
│   │   ├── engine_v2.py             # 调差引擎 v2 (保留最新版)
│   │   └── rules.py                 # 调差规则
│   │
│   ├── cost/                        # 造价相关服务
│   │   ├── __init__.py
│   │   ├── reference.py             # 造价参考价
│   │   ├── history.py               # 造价历史
│   │   └── import_service.py        # 导入服务
│   │
│   ├── ai/                          # AI 辅助服务
│   │   ├── __init__.py
│   │   ├── chat.py                  # AI 对话
│   │   ├── self_review.py           # AI 自检
│   │   ├── service.py               # AI 服务
│   │   └── rag.py                    # RAG 服务
│   │
│   └── data/                        # 数据存储
│       ├── yantai_rebar.db          # 钢筋价格数据库
│       └── cost_reference.db        # 造价参考数据库
```

### 2.3 废弃文件清单

以下文件将被删除（已确认有替代实现）：

| 文件 | 原因 |
|------|------|
| `services/fetch_yantai_补充.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_yantai_multi.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_yantai_api.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_yantai_history.py` | 功能已合并到 `fetch_yantai.py` |
| `services/daily_fetch*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_month*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_history*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_year_history.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_older_history.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_missing*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_recent*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/fetch_available*.py` | 功能已合并到 `fetch_yantai.py` |
| `services/step1_*.py` | 调试脚本，可删除 |
| `services/step2_*.py` | 调试脚本，可删除 |
| `services/test_*.py` | 测试脚本，可删除 |
| `services/check_*.py` | 调试脚本，可删除 |
| `services/collect_urls*.py` | 调试脚本，可删除 |
| `services/batch_*.py` | 批处理脚本，保留 `batch_ocr.py` 和 `batch_ocr_parse.py` |
| `services/debug_*.py` | 调试脚本，可删除 |
| `services/test_scroll.py` | 测试脚本，可删除 |
| `services/integrate*.py` | 集成脚本，可删除 |
| `services/generate*.py` | 生成脚本，保留 `generate_history_urls.py` |
| `services/merge*.py` | 合并脚本，可删除 |
| `services/import*.py` | 导入脚本，保留 `import_sqlite.py` |
| `services/parse*.py` | 解析脚本，保留 `parse_cost_images.py` |
| `services/yantai_rebar_scraper.py` | 与 `fetch_yantai.py` 重复 |
| `services/adjustment_engine*.py` | 保留 v2 版本 |
| `services/sqlite_service.py` | 与 `database.py` 功能重叠 |

### 2.4 保留文件清单

| 文件 | 说明 |
|------|------|
| `services/fetch_yantai.py` | 烟台价格抓取主服务 |
| `services/price_scraper.py` | 通用价格抓取 |
| `services/authenticated_scraper.py` | 认证抓取 |
| `services/compliant_scraper.py` | 合规爬虫 |
| `services/cloud_scraper.py` | 云端抓取 |
| `services/websocket_manager.py` | WebSocket 管理 |
| `services/rate_limiter.py` | 限流器 |
| `services/adjustment_calculator.py` | 调差计算 |
| `services/adjustment_engine_v2.py` | 调差引擎 v2 |
| `services/cost_reference.py` | 造价参考 |
| `services/ai_chat.py` | AI 对话 |
| `services/ai_service.py` | AI 服务 |
| `services/ai_self_review.py` | AI 自检 |
| `services/rag_service.py` | RAG 服务 |
| `services/secure_storage.py` | 安全存储 |
| `services/supabase_service.py` | Supabase 服务 |
| `services/price_cache.py` | 价格缓存 |
| `services/batch_ocr.py` | 批量 OCR |
| `services/batch_ocr_parse.py` | OCR 批量解析 |
| `services/parse_cost_images.py` | 图片解析 |
| `services/import_cost_reference.py` | 导入造价参考 |
| `services/cost_history.py` | 造价历史 |
| `services/ocr_missing.py` | OCR 缺失数据 |
| `services/yantai_db.py` | 烟台数据库 |

---

## 3. 腾讯云部署设计

### 3.1 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                   腾讯云轻量应用服务器                        │
│                   Ubuntu 22.04 LTS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │              Nginx (端口 80/443)                    │  │
│   │  ┌───────────────┬──────────────┬────────────────┐ │  │
│   │  │ /             │ /api/*        │ /ws            │ │  │
│   │  │ 前端静态文件   │ FastAPI代理   │ WebSocket代理  │ │  │
│   │  └───────────────┴──────────────┴────────────────┘ │  │
│   └─────────────────────────────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│   ┌─────────────────────────────────────────────────────┐  │
│   │       FastAPI 后端 (uvicorn :8001)                 │  │
│   │  ┌─────────────────────────────────────────────┐   │  │
│   │  │  /app                                        │   │  │
│   │  │  ├── main.py                                 │   │  │
│   │  │  ├── api/                                    │   │  │
│   │  │  ├── services/  (重构后)                    │   │  │
│   │  │  └── services/data/*.db                     │   │  │
│   │  └─────────────────────────────────────────────┘   │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐  │
│   │       Systemd Service (自动启动)                    │  │
│   │       日志: /var/log/taskplatform/                  │  │
│   └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
/opt/taskplatform/
├── app/
│   ├── main.py
│   ├── api/
│   ├── services/
│   └── models/
├── frontend/
│   ├── dist/              # npm run build 产物
│   └── ...
├── logs/                  # 应用日志
├── backups/               # 数据库备份
├── requirements.txt
├── nginx.conf
└── taskplatform.service  # systemd 服务文件
```

### 3.3 Nginx 配置

```nginx
server {
    listen 80;
    server_name _;

    # 前端静态文件
    location / {
        root /opt/taskplatform/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
```

### 3.4 systemd 服务配置

```ini
[Unit]
Description=TaskPlatform Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/taskplatform/app
Environment="PATH=/opt/taskplatform/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/taskplatform/venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001 --workers 2
Restart=always
RestartSec=5

# 日志
StandardOutput=append:/opt/taskplatform/logs/stdout.log
StandardError=append:/opt/taskplatform/logs/stderr.log

[Install]
WantedBy=multi-user.target
```

### 3.5 部署脚本

```bash
#!/bin/bash
# deploy.sh - TaskPlatform 部署脚本

set -e

APP_DIR="/opt/taskplatform"
VENV_DIR="$APP_DIR/venv"

echo "=== TaskPlatform 部署开始 ==="

# 1. 创建目录
mkdir -p $APP_DIR/{app,frontend,logs,backups}
mkdir -p /var/log/taskplatform

# 2. 安装 Python 环境
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
fi
source $VENV_DIR/bin/activate

# 3. 安装依赖
pip install --upgrade pip
pip install fastapi uvicorn[standard] sqlalchemy aiosqlite \
    pydantic python-multipart openpyxl pandas \
    beautifulsoup4 requests httpx

# 4. 拉取代码 (Git)
cd $APP_DIR
git pull origin main || echo "Git pull skipped"

# 5. 构建前端
cd $APP_DIR/frontend
npm install
npm run build

# 6. 重启服务
systemctl restart taskplatform
systemctl status taskplatform

echo "=== 部署完成 ==="
```

---

## 4. 数据备份策略

### 4.1 备份方案

| 项目 | 方案 |
|------|------|
| 备份频率 | 每日凌晨 3:00 |
| 保留份数 | 最近 7 天 |
| 备份位置 | 本地 `/opt/taskplatform/backups/` |
| 数据库文件 | `services/data/*.db` |

### 4.2 备份脚本

```bash
#!/bin/bash
# backup.sh - 数据库备份脚本

BACKUP_DIR="/opt/taskplatform/backups"
DATE=$(date +%Y%m%d)
DB_DIR="/opt/taskplatform/app/services/data"

mkdir -p $BACKUP_DIR

# 备份所有数据库文件
for db in $DB_DIR/*.db; do
    if [ -f "$db" ]; then
        filename=$(basename "$db")
        cp "$db" "$BACKUP_DIR/${DATE}_${filename}"
    fi
done

# 删除 7 天前的备份
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $(date)"
```

---

## 5. 安全配置

### 5.1 防火墙规则

| 端口 | 来源 | 说明 |
|------|------|------|
| 80 | 0.0.0.0/0 | HTTP |
| 443 | 0.0.0.0/0 | HTTPS (可选) |
| 22 | 仅管理员 IP | SSH |

### 5.2 环境变量

部署时需设置的环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `SUPABASE_URL` | Supabase 地址 | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase Key | `eyJhbGci...` |
| `AI_API_URL` | AI 服务地址 | `https://api.openai.com/v1` |
| `AI_API_KEY` | AI 服务密钥 | `sk-xxx` |

---

## 6. 实施步骤

### 阶段一：代码重构（第 1-2 天）

1. 备份现有代码
2. 创建新目录结构
3. 合并/重写核心服务
4. 删除废弃文件
5. 测试功能不变

### 阶段二：部署配置（第 3 天）

1. 上传代码到服务器
2. 配置 Nginx
3. 配置 systemd 服务
4. 设置防火墙

### 阶段三：测试验证（第 4 天）

1. 验证 API 可用性
2. 验证前端页面
3. 验证 WebSocket
4. 配置备份脚本

---

## 7. 验收标准

| 功能 | 验收条件 |
|------|----------|
| 价格抓取 | 能成功抓取烟台钢筋价格 |
| 调差计算 | 能正常计算调差结果 |
| 前端页面 | 所有页面正常访问 |
| API 响应 | 响应时间 < 2s |
| 自动启动 | 服务器重启后自动启动服务 |
| 数据持久化 | 数据库文件正确创建和更新 |

---

## 8. 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| 重构后功能异常 | 中 | 高 | 保留原文件，测试通过后再删除 |
| 服务器环境差异 | 低 | 中 | 提供详细的安装依赖列表 |
| 数据库迁移失败 | 低 | 高 | 保留原数据库备份 |

---

**文档版本**: v1.0
**创建日期**: 2026-05-28
**审核状态**: 待审核