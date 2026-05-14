# TaskPlatform Web 企业级界面

基于 React + Ant Design Pro + FastAPI 的工程调差计算系统。

## 项目结构

```
web/
├── backend/              # FastAPI 后端
│   ├── api/              # API 路由
│   │   ├── projects.py   # 项目管理
│   │   ├── materials.py  # 材料管理
│   │   ├── price_sources.py  # 价格来源
│   │   ├── price_history.py   # 价格历史
│   │   ├── adjustments.py     # 调差计算
│   │   ├── indicators.py     # 指标库
│   │   └── sync.py           # 数据同步
│   ├── services/         # 业务逻辑
│   │   ├── price_scraper.py  # 价格抓取
│   │   └── adjustment_calculator.py  # 调差计算
│   ├── models/           # 数据模型
│   └── main.py           # 入口文件
│
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── pages/        # 页面
│   │   │   ├── Dashboard.tsx   # 仪表盘
│   │   │   ├── Projects.tsx    # 项目管理
│   │   │   ├── Materials.tsx    # 材料管理
│   │   │   ├── PriceMonitor.tsx # 价格监控
│   │   │   ├── Adjustment.tsx   # 调差计算
│   │   │   ├── Indicators.tsx   # 指标库
│   │   │   └── Settings.tsx    # 系统设置
│   │   └── App.tsx       # 应用入口
│   └── package.json
```

## 快速启动

### 1. 启动后端

```bash
cd web/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. 启动前端

```bash
cd web/frontend
npm install
npm run dev
```

访问 http://localhost:3000

## 功能特性

- **项目管理**: 创建、编辑、删除工程项目
- **材料管理**: 钢筋、混凝土、金属、有色金属等材料分类
- **价格监控**: 
  - 我的钢铁网 (钢筋、混凝土)
  - 有色金属网 (铝、铜、锌)
  - 信息价 (地方造价信息网)
- **调差计算**: 自动计算材料价格波动导致的调差
- **指标库**: 施工进度、质量、成本、安全等指标跟踪
- **多人协作**: 支持多用户实时同步 (基于 Supabase Realtime)

## 价格抓取来源

| 来源 | URL | 支持材料 |
|------|-----|---------|
| 我的钢铁网 | https://www.mysteel.com.cn | 钢筋、混凝土、钢材 |
| 有色金属网 | https://www.ccmn.cn | 铝锭、铜锭、锌锭 |
| 信息价 | 各省市造价信息网 | 综合材料 |

## 技术栈

- **前端**: React 18 + TypeScript + Vite + Ant Design 5
- **后端**: FastAPI + Python 3.10+
- **数据库**: Supabase (PostgreSQL)
- **实时同步**: Supabase Realtime