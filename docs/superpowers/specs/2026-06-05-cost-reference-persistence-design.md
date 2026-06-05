# 造价参考价数据持久化设计方案

> **创建日期**: 2026-06-05
> **目标**: 将造价参考价从硬编码迁移到 Supabase，支持多时间段数据管理和查询

## 1. 目标

将 `STEEL_REBAR_PRICES`、`CONCRETE_PRICES`、`MORTAR_PRICES` 从硬编码迁移到 Supabase `cost_reference_prices` 表，支持按分类、按季度查询和动态管理。

## 2. 架构策略

- **Supabase 表**：存储可管理的参考价数据
- **历史季度数据**：`cost_history.py` 中的 `CONCRETE_HISTORY` 保持现状，后续迭代迁移
- **API 层**：`cost_reference.py` 从 `SupabaseService` 读取，保留过滤/搜索逻辑

## 3. 数据表设计

```sql
CREATE TABLE public.cost_reference_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    code TEXT,
    name TEXT NOT NULL,
    spec TEXT,
    unit TEXT DEFAULT 't',
    unit_price DOUBLE PRECISION,
    tax_rate DOUBLE PRECISION DEFAULT 13.0,
    pump_price DOUBLE PRECISION,
    non_pump_price DOUBLE PRECISION,
    source TEXT DEFAULT '烟台工程建设标准造价管理',
    period TEXT NOT NULL,
    region TEXT DEFAULT '山东烟台',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_cost_ref_uniq ON cost_reference_prices(category, name, period);
CREATE INDEX idx_cost_ref_category ON cost_reference_prices(category);
CREATE INDEX idx_cost_ref_period ON cost_reference_prices(period);
ALTER TABLE cost_reference_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous" ON cost_reference_prices FOR ALL USING (true) WITH CHECK (true);
```

## 4. API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/cost-reference/steel` | 查询钢筋参考价 |
| GET | `/cost-reference/steel/types` | 查询钢筋类型列表 |
| GET | `/cost-reference/steel/specs` | 查询钢筋规格列表 |
| GET | `/cost-reference/concrete` | 查询混凝土参考价 |
| GET | `/cost-reference/concrete/grades` | 查询混凝土强度等级 |
| GET | `/cost-reference/mortar` | 查询砂浆参考价 |
| GET | `/cost-reference/search` | 综合搜索 |
| GET | `/cost-reference/categories` | 获取分类列表 |
| GET | `/cost-reference/summary` | 获取汇总信息 |
| GET | `/cost-reference/sources` | 获取数据来源 |
| POST | `/cost-reference/prices` | 批量插入参考价 |
| POST | `/cost-reference/import` | 从 Excel 导入 |

**过滤参数**：
- `?period=2024年第一季度` — 按季度筛选
- `?spec=Φ12` — 按规格筛选
- `?steel_type=HRB400` — 按钢筋类型筛选
- `?min_grade=C30&max_grade=C40` — 按强度等级范围筛选

## 5. 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/create_cost_reference_prices_table.sql` | 新建 | Supabase 建表 SQL |
| `web/backend/services/supabase_service.py` | 修改 | 新增 cost_reference CRUD |
| `web/backend/api/cost_reference.py` | 修改 | 改造为 Supabase 驱动 |
| `scripts/migrate_cost_reference_to_supabase.py` | 新建 | 迁移脚本 |

## 6. 迁移流程

1. 用户在 Supabase SQL Editor 执行 `create_cost_reference_prices_table.sql`
2. 运行 `scripts/migrate_cost_reference_to_supabase.py` 迁移当前数据
3. 部署后端

## 7. 兼容性

- API 路径不变（`/cost-reference/`）
- 前端无需修改 API 调用
- 季度数据通过 `period` 参数筛选