# 价格监控数据持久化设计方案

> **创建日期**: 2026-06-05
> **目标**: 将价格监控数据从 SQLite 迁移到 Supabase

## 1. 目标

将烟台钢筋价格数据持久化到 Supabase，支持多端访问、权限控制和历史数据查询。

## 2. 架构策略

采用 **双写 + 读 Supabase** 策略，平稳过渡：

- **爬虫端**：抓取数据仍写入 SQLite（保持原有逻辑不变）
- **API 端**：新增 `/yantai-rebar/` 路由走 Supabase；原有 `/yantai-db/` 路由保留
- **迁移**：一次性将 SQLite 历史数据迁移到 Supabase
- **长期**：爬虫完成双写后，完全切换到 Supabase

## 3. 数据表设计

Supabase 表 `public.rebar_prices`：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键，自动生成 |
| date | TEXT | 日期 (YYYY-MM-DD) |
| fetch_time | TEXT | 时段 (09:00/PM) |
| material_name | TEXT | 品名 |
| spec | TEXT | 规格 |
| material_type | TEXT | 材质 |
| brand | TEXT | 品牌/钢厂 |
| price | INTEGER | 价格(元/吨) |
| region | TEXT | 地区，默认'山东烟台' |
| created_at | TIMESTAMPTZ | 创建时间 |

**索引**：
- `idx_rebar_uniq`: UNIQUE(date, material_name, spec, brand, price) — 防重复
- `idx_rebar_date`: date — 按日期查询
- `idx_rebar_material`: material_name — 按品名筛选

**RLS**：启用，允许匿名读写

## 4. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/create_rebar_prices_table.sql` | 新建 | Supabase 建表 SQL |
| `web/backend/services/supabase_service.py` | 修改 | 新增 rebar CRUD 方法 |
| `web/backend/api/yantai_db.py` | 修改 | 保留原路由 + 新增 `/yantai-rebar/` 路由 |
| `web/frontend/src/services/api.ts` | 修改 | 新增 `yantaiRebarApi` |
| `web/frontend/src/pages/PriceMonitor.tsx` | 修改 | 改用新 API |
| `scripts/migrate_rebar_to_supabase.py` | 新建 | SQLite → Supabase 迁移脚本 |

## 5. API 设计

新增 `/yantai-rebar/` 路由组：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/yantai-rebar/stats` | 数据库统计 |
| GET | `/yantai-rebar/latest` | 最新价格 |
| GET | `/yantai-rebar/range` | 日期范围数据 |
| GET | `/yantai-rebar/trend` | 价格趋势 |
| GET | `/yantai-rebar/materials` | 品名列表 |
| GET | `/yantai-rebar/specs` | 规格列表 |
| GET | `/yantai-rebar/dates` | 可用日期列表 |
| POST | `/yantai-rebar/prices` | 批量插入价格 |
| GET | `/yantai-rebar/search` | 搜索价格 |

## 6. 前端改动

新增 `yantaiRebarApi`：

```ts
export const yantaiRebarApi = {
  getLatest: (date?: string, limit?: number) => fetch(`/yantai-rebar/latest`),
  getByRange: (start_date, end_date, material?, spec?) => fetch(`/yantai-rebar/range`),
  getTrend: (material?, spec?, days?, start_date?, end_date?) => fetch(`/yantai-rebar/trend`),
  getStats: () => fetch(`/yantai-rebar/stats`),
  insertPrices: (prices: any[]) => fetch(`/yantai-rebar/prices`, { method: 'POST' }),
};
```

`PriceMonitor.tsx` 替换原有 API 调用，其余 UI 逻辑不变。

## 7. 迁移流程

1. 用户在 Supabase SQL Editor 执行 `create_rebar_prices_table.sql`
2. 运行 `scripts/migrate_rebar_to_supabase.py` 一次性迁移历史数据
3. 部署后端更改
4. 前端切换到新 API

## 8. 兼容性

- 保留 `/yantai-db/` 路由供旧客户端使用
- 新建 `/yantai-rebar/` 路由走 Supabase
- 迁移完成后可考虑废弃 SQLite 数据文件