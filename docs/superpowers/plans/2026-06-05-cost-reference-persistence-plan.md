# 造价参考价数据持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将造价参考价从硬编码迁移到 Supabase，支持按分类、按季度查询和动态管理。

**Architecture:** 新建 `cost_reference_prices` 表存储可管理的参考价数据，`cost_reference.py` API 从 Supabase 读取，保留过滤/搜索逻辑。

**Tech Stack:** FastAPI, Supabase (REST API), TypeScript/React

---

## Task 1: 创建 Supabase 建表 SQL

**Files:**
- Create: `scripts/create_cost_reference_prices_table.sql`

- [ ] **Step 1: 创建建表 SQL**

```sql
-- Supabase SQL: 创建 cost_reference_prices 表
-- 在 Supabase SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS public.cost_reference_prices (
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_cost_ref_uniq
    ON public.cost_reference_prices(category, name, period);
CREATE INDEX IF NOT EXISTS idx_cost_ref_category ON public.cost_reference_prices(category);
CREATE INDEX IF NOT EXISTS idx_cost_ref_period ON public.cost_reference_prices(period);
ALTER TABLE public.cost_reference_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow anonymous access" ON public.cost_reference_prices
    FOR ALL USING (true) WITH CHECK (true);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/create_cost_reference_prices_table.sql
git commit -m "feat: 添加 cost_reference_prices Supabase 建表 SQL"
```

---

## Task 2: 新增 SupabaseService cost_reference CRUD 方法

**Files:**
- Modify: `web/backend/services/supabase_service.py`

在 `class SupabaseService` 的 `insert_rebar_prices` 方法之后、`class PriceScraper` 之前，插入以下方法：

```python
    # ========== 造价参考价 ==========

    def get_cost_reference_prices(
        self,
        category: str = None,
        period: str = None,
        spec: str = None,
        steel_type: str = None,
        min_grade: str = None,
        max_grade: str = None,
        limit: int = 500
    ) -> List[Dict]:
        """获取造价参考价列表"""
        query = f'/cost_reference_prices?select=*&order=name.asc&limit={limit}'
        if category:
            query += f'&category=eq.{category}'
        if period:
            query += f'&period=eq.{period}'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if min_grade:
            query += f'&grade=gte.{min_grade}'
        if max_grade:
            query += f'&grade=lte.{max_grade}'
        result = self._request('GET', query)
        return result if result else []

    def get_cost_reference_categories(self) -> List[Dict]:
        """获取所有分类及统计"""
        result = self._request('GET', '/cost_reference_prices?select=category,period&limit=10000')
        if not result:
            return []
        cats: Dict[str, Dict] = {}
        for r in result:
            cat = r.get('category', '')
            if cat not in cats:
                cats[cat] = {'id': cat, 'name': f'{cat}价格', 'count': 0}
            cats[cat]['count'] += 1
        return list(cats.values())

    def get_cost_reference_summary(self) -> Dict:
        """获取造价参考价汇总"""
        result = self._request('GET', '/cost_reference_prices?select=category,unit_price,pump_price,non_pump_price&limit=10000')
        if not result:
            return {}
        steel_prices = [r.get('unit_price', 0) for r in result if r.get('category') == '钢筋' and r.get('unit_price')]
        concrete_pump = [r.get('pump_price', 0) for r in result if r.get('category') == '混凝土' and r.get('pump_price')]
        concrete_non = [r.get('non_pump_price', 0) for r in result if r.get('category') == '混凝土' and r.get('non_pump_price')]
        mortar_prices = [r.get('unit_price', 0) for r in result if r.get('category') == '砂浆' and r.get('unit_price')]
        return {
            '钢筋': {'count': len(steel_prices), 'price_range': {'min': min(steel_prices) if steel_prices else 0, 'max': max(steel_prices) if steel_prices else 0}, 'unit': '元/吨'},
            '混凝土': {'count': len(concrete_pump), 'price_range': {'min_pump': min(concrete_pump) if concrete_pump else 0, 'max_pump': max(concrete_pump) if concrete_pump else 0}, 'unit': '元/立方米'},
            '砂浆': {'count': len(mortar_prices), 'price_range': {'min': min(mortar_prices) if mortar_prices else 0, 'max': max(mortar_prices) if mortar_prices else 0}, 'unit': '元/吨'},
        }

    def insert_cost_reference_prices(self, items: List[Dict]) -> Dict:
        """批量插入造价参考价"""
        imported = 0
        errors = []
        for i, item in enumerate(items):
            data = {
                'category': item.get('category', ''),
                'code': item.get('code') or None,
                'name': item.get('name', ''),
                'spec': item.get('spec') or None,
                'unit': item.get('unit', 't'),
                'unit_price': item.get('unit_price') or item.get('pump_price') or 0,
                'tax_rate': item.get('tax_rate', 13.0),
                'pump_price': item.get('pump_price') or None,
                'non_pump_price': item.get('non_pump_price') or None,
                'source': item.get('source', '烟台工程建设标准造价管理'),
                'period': item.get('period', '2024年第一季度'),
                'region': item.get('region', '山东烟台'),
                'notes': item.get('notes') or None,
            }
            try:
                resp = self._request('POST', '/cost_reference_prices', json=data)
                if resp:
                    imported += 1
                else:
                    errors.append({'index': i, 'error': '插入失败'})
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        return {'imported': imported, 'total': len(items), 'errors': errors}

    def get_cost_reference_price(self, item_id: str) -> Optional[Dict]:
        """获取单条造价参考价"""
        result = self._request('GET', f'/cost_reference_prices?id=eq.{item_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None
```

- [ ] **Step 2: Commit**

```bash
git add web/backend/services/supabase_service.py
git commit -m "feat: SupabaseService 新增 cost_reference_prices CRUD 方法"
```

---

## Task 3: 改造 cost_reference.py API

**Files:**
- Modify: `web/backend/api/cost_reference.py`

改造 `cost_reference.py`，将硬编码的 `STEEL_REBAR_PRICES`、`CONCRETE_PRICES`、`MORTAR_PRICES` 替换为从 `SupabaseService` 读取。

**主要改动**：

1. 在文件顶部 import 添加：
```python
from services.supabase_service import SupabaseService
```

2. 在 `router = APIRouter(...)` 之后添加：
```python
def get_supabase():
    return SupabaseService()
```

3. 改造每个 endpoint 函数，从 Supabase 读取数据：

**GET /steel** — 改为调用 `supabase.get_cost_reference_prices(category='钢筋', period=..., spec=..., steel_type=...)`，然后在内存中按 `steel_type` 过滤。

**GET /steel/types** — 改为查询 `category='钢筋'`，从结果中提取类型。

**GET /steel/specs** — 改为查询 `category='钢筋'`，从结果中提取规格。

**GET /concrete** — 改为调用 `supabase.get_cost_reference_prices(category='混凝土', period=...)`，然后在内存中按 `min_grade`/`max_grade` 过滤。

**GET /concrete/grades** — 从混凝土数据中提取 grades。

**GET /mortar** — 改为调用 `supabase.get_cost_reference_prices(category='砂浆', period=...)`。

**GET /search** — 从 Supabase 读取所有数据，然后在内存中按 keyword 过滤。

**GET /categories** — 调用 `supabase.get_cost_reference_categories()`。

**GET /summary** — 调用 `supabase.get_cost_reference_summary()`。

**GET /sources** — 保持不变（返回静态数据）。

**POST /prices** — 添加新端点，接受 `List[Dict]`，调用 `supabase.insert_cost_reference_prices()`。

4. 每个 endpoint 函数签名添加 `supabase: SupabaseService = Depends(get_supabase)` 参数。

- [ ] **Step 2: Commit**

```bash
git add web/backend/api/cost_reference.py
git commit -m "refactor: cost_reference API 改为 Supabase 驱动"
```

---

## Task 4: 创建迁移脚本

**Files:**
- Create: `scripts/migrate_cost_reference_to_supabase.py`

```python
"""
将造价参考价硬编码数据迁移到 Supabase
运行: python scripts/migrate_cost_reference_to_supabase.py
"""
import sys
sys.path.insert(0, 'web/backend')

import logging
from services.supabase_service import SupabaseService
from models.cost_reference import STEEL_REBAR_PRICES, CONCRETE_PRICES, MORTAR_PRICES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PERIOD = '2024年第一季度'
SOURCE = '烟台工程建设标准造价管理'

def migrate():
    logger.info("[migrate] 开始迁移造价参考价数据")
    supabase = SupabaseService()

    # 钢筋
    steel_items = [{'category': '钢筋', 'period': PERIOD, 'source': SOURCE, **item} for item in STEEL_REBAR_PRICES]
    # 混凝土
    concrete_items = [{'category': '混凝土', 'period': PERIOD, 'source': SOURCE, **item} for item in CONCRETE_PRICES]
    # 砂浆
    mortar_items = [{'category': '砂浆', 'period': PERIOD, 'source': SOURCE, **item} for item in MORTAR_PRICES]

    all_items = steel_items + concrete_items + mortar_items
    logger.info(f"[migrate] 共 {len(all_items)} 条数据")

    result = supabase.insert_cost_reference_prices(all_items)
    logger.info(f"[migrate] 迁移完成 | 成功={result['imported']} | 总数={result['total']} | 失败={len(result['errors'])}")


if __name__ == '__main__':
    migrate()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrate_cost_reference_to_supabase.py
git commit -m "feat: 添加造价参考价迁移脚本"
```

---

## Task 5: 自检

- [ ] 确认 `scripts/create_cost_reference_prices_table.sql` 已提交
- [ ] 确认 `supabase_service.py` 中新增了 `get_cost_reference_prices`、`get_cost_reference_categories`、`get_cost_reference_summary`、`insert_cost_reference_prices`、`get_cost_reference_price` 5个方法
- [ ] 确认 `cost_reference.py` 中 `/steel` 等端点从 Supabase 读取而非硬编码
- [ ] 确认 `cost_reference.py` 新增了 `POST /prices` 端点
- [ ] 确认 `migrate_cost_reference_to_supabase.py` 已提交
- [ ] 运行 `python -m py_compile web/backend/services/supabase_service.py`
- [ ] 运行 `python -m py_compile web/backend/api/cost_reference.py`
- [ ] 运行 `python -m py_compile scripts/migrate_cost_reference_to_supabase.py`