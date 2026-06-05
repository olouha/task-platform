# 价格监控数据持久化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将烟台钢筋价格数据从 SQLite 迁移到 Supabase，完成数据持久化改造。

**Architecture:** 采用双写策略：爬虫写 SQLite，新增 `/yantai-rebar/` API 路由走 Supabase，前端切换到新路由，一次性迁移历史数据。

**Tech Stack:** FastAPI, Supabase (REST API), SQLite, TypeScript/React, Recharts

---

## Task 1: 创建 Supabase 建表 SQL

**Files:**
- Create: `scripts/create_rebar_prices_table.sql`

- [ ] **Step 1: 创建建表 SQL 文件**

```sql
-- Supabase SQL: 创建 rebar_prices 表
-- 在 Supabase SQL Editor 中执行此脚本

CREATE TABLE IF NOT EXISTS public.rebar_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date TEXT NOT NULL,
    fetch_time TEXT,
    material_name TEXT NOT NULL,
    spec TEXT,
    material_type TEXT,
    brand TEXT,
    price INTEGER NOT NULL,
    region TEXT DEFAULT '山东烟台',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 防重复唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_rebar_uniq
    ON public.rebar_prices(date, material_name, spec, brand, price);

-- 查询索引
CREATE INDEX IF NOT EXISTS idx_rebar_date ON public.rebar_prices(date);
CREATE INDEX IF NOT EXISTS idx_rebar_material ON public.rebar_prices(material_name);
CREATE INDEX IF NOT EXISTS idx_rebar_spec ON public.rebar_prices(spec);

-- RLS 策略
ALTER TABLE public.rebar_prices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous access" ON public.rebar_prices
    FOR ALL USING (true) WITH CHECK (true);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/create_rebar_prices_table.sql
git commit -m "feat: 添加 rebar_prices Supabase 建表 SQL"
```

---

## Task 2: 新增 SupabaseService rebar CRUD 方法

**Files:**
- Modify: `web/backend/services/supabase_service.py`（在文件末尾 `class PriceScraper` 之前插入新方法）

- [ ] **Step 1: 添加 rebar CRUD 方法**

在 `supabase_service.py` 的 `class SupabaseService` 中找到 `list_kb_documents` 方法，在它之前插入以下方法（紧跟 `import_indicator_projects` 之后）：

```python
    # ========== 烟台钢筋价格 ==========

    def get_rebar_prices(
        self,
        date: str = None,
        start_date: str = None,
        end_date: str = None,
        material_name: str = None,
        spec: str = None,
        brand: str = None,
        limit: int = 500
    ) -> List[Dict]:
        """获取钢筋价格列表"""
        query = f'/rebar_prices?select=*&order=date.desc,fetch_time.desc&limit={limit}'
        if date:
            query += f'&date=eq.{date}'
        if start_date:
            query += f'&date=gte.{start_date}'
        if end_date:
            query += f'&date=lte.{end_date}'
        if material_name:
            query += f'&material_name=ilike.%25{material_name}%25'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if brand:
            query += f'&brand=ilike.%25{brand}%25'
        result = self._request('GET', query)
        return result if result else []

    def get_rebar_latest(self, limit: int = 500) -> Dict:
        """获取最新价格（按最新日期）"""
        result = self._request('GET', f'/rebar_prices?select=*&order=date.desc,fetch_time.desc&limit={limit}')
        if not result:
            return {'success': True, 'count': 0, 'prices': []}
        latest_date = result[0].get('date') if result else None
        filtered = [r for r in result if r.get('date') == latest_date]
        return {'success': True, 'count': len(filtered), 'prices': filtered}

    def get_rebar_trend(
        self,
        material_name: str = None,
        spec: str = None,
        days: int = 365,
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """获取价格趋势（日均价的 max/min/avg）"""
        from datetime import datetime, timedelta
        query = '/rebar_prices?select=date,material_name,spec,brand,price&order=date.asc'
        if material_name:
            query += f'&material_name=ilike.%25{material_name}%25'
        if spec:
            query += f'&spec=ilike.%25{spec}%25'
        if start_date:
            query += f'&date=gte.{start_date}'
        elif end_date:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            query += f'&date=gte.{cutoff}'
        if end_date:
            query += f'&date=lte.{end_date}'
        result = self._request('GET', query)
        if not result:
            return {'success': True, 'count': 0, 'data': []}
        # 按日期聚合
        daily: Dict[str, Dict] = {}
        for r in result:
            d = r.get('date')
            if d not in daily:
                daily[d] = {'date': d, 'prices': []}
            daily[d]['prices'].append(r.get('price', 0))
        trend = []
        for date_str, item in sorted(daily.items()):
            prices = item['prices']
            trend.append({
                'date': date_str,
                'avg_price': round(sum(prices) / len(prices), 2) if prices else 0,
                'min_price': min(prices) if prices else 0,
                'max_price': max(prices) if prices else 0,
                'cnt': len(prices)
            })
        return {'success': True, 'count': len(trend), 'data': trend}

    def get_rebar_stats(self) -> Dict:
        """获取钢筋价格统计"""
        result = self._request('GET', '/rebar_prices?select=date,material_name,spec,brand,price&limit=10000')
        if not result:
            return {'total_count': 0, 'dates_count': 0, 'date_range': {}, 'materials': {}, 'specs': {}}
        dates = set(r.get('date') for r in result if r.get('date'))
        materials: Dict[str, int] = {}
        specs: Dict[str, int] = {}
        for r in result:
            mn = r.get('material_name')
            if mn:
                materials[mn] = materials.get(mn, 0) + 1
            sp = r.get('spec')
            if sp:
                specs[sp] = specs.get(sp, 0) + 1
        sorted_dates = sorted(dates)
        return {
            'total_count': len(result),
            'dates_count': len(dates),
            'date_range': {'start': sorted_dates[0] if sorted_dates else None, 'end': sorted_dates[-1] if sorted_dates else None},
            'materials': dict(sorted(materials.items(), key=lambda x: -x[1])[:20]),
            'specs': dict(sorted(specs.items(), key=lambda x: -x[1])[:20])
        }

    def insert_rebar_prices(self, prices: List[Dict]) -> Dict:
        """批量插入钢筋价格数据"""
        imported = 0
        errors = []
        for i, p in enumerate(prices):
            data = {
                'date': p.get('date', ''),
                'fetch_time': p.get('fetch_time') or None,
                'material_name': p.get('material_name', ''),
                'spec': p.get('spec') or None,
                'material_type': p.get('material_type') or None,
                'brand': p.get('brand') or None,
                'price': p.get('price', 0),
                'region': p.get('region', '山东烟台'),
            }
            try:
                resp = self._request('POST', '/rebar_prices', json=data)
                if resp:
                    imported += 1
                else:
                    errors.append({'index': i, 'error': '插入失败'})
            except Exception as e:
                errors.append({'index': i, 'error': str(e)})
        return {'imported': imported, 'total': len(prices), 'errors': errors}
```

- [ ] **Step 2: Commit**

```bash
git add web/backend/services/supabase_service.py
git commit -m "feat: SupabaseService 新增 rebar_prices CRUD 方法"
```

---

## Task 3: 新增 /yantai-rebar/ API 路由

**Files:**
- Modify: `web/backend/api/yantai_db.py`（在文件末尾 `</module>` 之前插入新路由组）

- [ ] **Step 1: 添加 /yantai-rebar/ 路由**

在 `yantai_db.py` 末尾（第490行之后）添加新路由组：

```python
# ============================================================
# 烟台钢筋价格 — Supabase 版本
# ============================================================
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from services.supabase_service import SupabaseService

rebar_router = APIRouter(prefix="/yantai-rebar", tags=["烟台钢筋价格-Supabase"])
_rebar_logger = logging.getLogger(__name__)


def get_supabase():
    return SupabaseService()


class RebarPriceRecord(BaseModel):
    date: str
    fetch_time: Optional[str] = None
    material_name: str
    spec: Optional[str] = None
    material_type: Optional[str] = None
    brand: Optional[str] = None
    price: int
    region: str = '山东烟台'


@rebar_router.get("/stats")
async def get_rebar_stats(supabase: SupabaseService = Depends(get_supabase)):
    """获取数据库统计信息"""
    _rebar_logger.info("[get_rebar_stats] 查询统计")
    result = supabase.get_rebar_stats()
    _rebar_logger.info(f"[get_rebar_stats] 完成 | total={result.get('total_count')}")
    return result


@rebar_router.get("/latest")
async def get_rebar_latest(
    date: str = Query(None, description="指定日期 YYYY-MM-DD"),
    limit: int = Query(500, description="返回数量"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取最新价格数据"""
    _rebar_logger.info(f"[get_rebar_latest] 查询 | date={date} | limit={limit}")
    result = supabase.get_rebar_latest(limit=limit)
    _rebar_logger.info(f"[get_rebar_latest] 完成 | count={result.get('count')}")
    return result


@rebar_router.get("/range")
async def get_rebar_by_range(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    material: str = Query(None, description="品名筛选"),
    spec: str = Query(None, description="规格筛选"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取日期范围内的价格数据"""
    _rebar_logger.info(f"[get_rebar_by_range] 查询 | start={start_date} | end={end_date}")
    prices = supabase.get_rebar_prices(
        start_date=start_date, end_date=end_date,
        material_name=material, spec=spec, limit=5000
    )
    dates_data: Dict[str, List[Dict]] = {}
    for p in prices:
        d = p.get('date', '')
        if d not in dates_data:
            dates_data[d] = []
        dates_data[d].append(p)
    _rebar_logger.info(f"[get_rebar_by_range] 完成 | total={len(prices)} | dates={len(dates_data)}")
    return {
        'success': True,
        'start_date': start_date,
        'end_date': end_date,
        'total_count': len(prices),
        'dates_count': len(dates_data),
        'data': dates_data
    }


@rebar_router.get("/trend")
async def get_rebar_trend(
    material: str = Query(None, description="品名"),
    spec: str = Query(None, description="规格"),
    days: int = Query(365, description="天数"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取价格趋势数据"""
    _rebar_logger.info(f"[get_rebar_trend] 查询 | material={material} | days={days}")
    result = supabase.get_rebar_trend(
        material_name=material, spec=spec,
        days=days, start_date=start_date, end_date=end_date
    )
    _rebar_logger.info(f"[get_rebar_trend] 完成 | count={result.get('count')}")
    return result


@rebar_router.get("/materials")
async def get_rebar_materials(supabase: SupabaseService = Depends(get_supabase)):
    """获取所有品名"""
    _rebar_logger.info("[get_rebar_materials] 查询品名")
    stats = supabase.get_rebar_stats()
    materials = [{'name': k, 'count': v} for k, v in stats.get('materials', {}).items()]
    _rebar_logger.info(f"[get_rebar_materials] 完成 | count={len(materials)}")
    return {'success': True, 'materials': materials}


@rebar_router.get("/specs")
async def get_rebar_specs(
    material: str = Query(None, description="品名筛选"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取所有规格"""
    _rebar_logger.info(f"[get_rebar_specs] 查询 | material={material}")
    stats = supabase.get_rebar_stats()
    specs = [{'spec': k, 'count': v} for k, v in stats.get('specs', {}).items()]
    _rebar_logger.info(f"[get_rebar_specs] 完成 | count={len(specs)}")
    return {'success': True, 'specs': specs}


@rebar_router.get("/dates")
async def get_rebar_dates(
    start_date: str = Query(None),
    end_date: str = Query(None),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取所有可用日期"""
    _rebar_logger.info("[get_rebar_dates] 查询可用日期")
    prices = supabase.get_rebar_prices(start_date=start_date, end_date=end_date, limit=10000)
    date_periods = []
    for p in prices:
        d = p.get('date', '')
        ft = p.get('fetch_time', '')
        if ft in ('09:00', 'AM'):
            date_periods.append(f"{d} 上午")
        elif ft == 'PM':
            date_periods.append(f"{d} 下午（较晚）")
        else:
            date_periods.append(d)
    unique = []
    seen = set()
    for dp in reversed(date_periods):
        if dp not in seen:
            seen.add(dp)
            unique.append(dp)
    unique.reverse()
    _rebar_logger.info(f"[get_rebar_dates] 完成 | count={len(unique)}")
    return {'success': True, 'count': len(unique), 'dates': unique}


@rebar_router.post("/prices")
async def insert_rebar_prices(
    prices: List[RebarPriceRecord],
    supabase: SupabaseService = Depends(get_supabase)
):
    """批量插入价格数据"""
    _rebar_logger.info(f"[insert_rebar_prices] 插入 | count={len(prices)}")
    data = [p.model_dump() for p in prices]
    result = supabase.insert_rebar_prices(data)
    _rebar_logger.info(f"[insert_rebar_prices] 完成 | imported={result['imported']}")
    return result


@rebar_router.get("/search")
async def search_rebar_prices(
    keyword: str = Query(..., description="搜索关键词"),
    date: str = Query(None),
    limit: int = Query(100),
    supabase: SupabaseService = Depends(get_supabase)
):
    """搜索价格数据"""
    _rebar_logger.info(f"[search_rebar_prices] 搜索 | keyword={keyword}")
    prices = supabase.get_rebar_prices(
        date=date if date else None,
        limit=limit
    )
    kw = keyword.lower()
    filtered = [
        p for p in prices
        if kw in str(p.get('material_name', '')).lower()
        or kw in str(p.get('spec', '')).lower()
        or kw in str(p.get('brand', '')).lower()
        or kw in str(p.get('material_type', '')).lower()
    ]
    _rebar_logger.info(f"[search_rebar_prices] 完成 | found={len(filtered)}")
    return {'success': True, 'count': len(filtered), 'prices': filtered}
```

- [ ] **Step 2: 在 main.py 注册路由**

找到 `web/backend/main.py` 中 `yantai_db` 路由注册的地方，添加新路由：

```python
from api.yantai_db import router as yantai_db_router
from api.yantai_db import rebar_router as yantai_rebar_router  # 新增
```

找到 `app.include_router` 的 yantai_db 行，在其后添加：

```python
app.include_router(yantai_rebar_router)
```

- [ ] **Step 3: Commit**

```bash
git add web/backend/api/yantai_db.py web/backend/main.py
git commit -m "feat: 新增 /yantai-rebar/ Supabase API 路由组"
```

---

## Task 4: 前端 API 和 PriceMonitor 切换

**Files:**
- Modify: `web/frontend/src/services/api.ts`（在文件末尾 `indicatorDatabaseApi` 之后添加新 API）
- Modify: `web/frontend/src/pages/PriceMonitor.tsx`（替换 API 调用）

- [ ] **Step 1: 添加 yantaiRebarApi**

在 `api.ts` 末尾（`indicatorDatabaseApi` 最后一个括号之后）添加：

```ts
// 烟台钢筋价格 API (Supabase)
export const yantaiRebarApi = {
  getStats: async () => {
    const response = await fetch(`${config.apiUrl}/yantai-rebar/stats`);
    return response.json();
  },
  getLatest: async (date?: string, limit = 500) => {
    const url = date
      ? `${config.apiUrl}/yantai-rebar/latest?date=${encodeURIComponent(date)}&limit=${limit}`
      : `${config.apiUrl}/yantai-rebar/latest?limit=${limit}`;
    const response = await fetch(url);
    return response.json();
  },
  getByRange: async (start_date: string, end_date: string, material?: string, spec?: string) => {
    const params = new URLSearchParams({ start_date, end_date });
    if (material) params.append('material', material);
    if (spec) params.append('spec', spec);
    const response = await fetch(`${config.apiUrl}/yantai-rebar/range?${params}`);
    return response.json();
  },
  getTrend: async (material?: string, spec?: string, days = 365, start_date?: string, end_date?: string) => {
    const params = new URLSearchParams({ days: String(days) });
    if (material) params.append('material', material);
    if (spec) params.append('spec', spec);
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    const response = await fetch(`${config.apiUrl}/yantai-rebar/trend?${params}`);
    return response.json();
  },
  getMaterials: async () => {
    const response = await fetch(`${config.apiUrl}/yantai-rebar/materials`);
    return response.json();
  },
  getSpecs: async (material?: string) => {
    const url = material
      ? `${config.apiUrl}/yantai-rebar/specs?material=${encodeURIComponent(material)}`
      : `${config.apiUrl}/yantai-rebar/specs`;
    const response = await fetch(url);
    return response.json();
  },
  getDates: async (start_date?: string, end_date?: string) => {
    const params = new URLSearchParams();
    if (start_date) params.append('start_date', start_date);
    if (end_date) params.append('end_date', end_date);
    const url = `${config.apiUrl}/yantai-rebar/dates${params.toString() ? '?' + params : ''}`;
    const response = await fetch(url);
    return response.json();
  },
  search: async (keyword: string, date?: string, limit = 100) => {
    const params = new URLSearchParams({ keyword, limit: String(limit) });
    if (date) params.append('date', date);
    const response = await fetch(`${config.apiUrl}/yantai-rebar/search?${params}`);
    return response.json();
  },
};
```

- [ ] **Step 2: 替换 PriceMonitor.tsx 中的 API 调用**

打开 `PriceMonitor.tsx`，搜索以下模式并替换：

| 旧调用 | 新调用 |
|--------|--------|
| `fetch('/stats')` | `yantaiRebarApi.getStats()` |
| `fetch('/latest')` | `yantaiRebarApi.getLatest()` |
| `fetch('/range')` | `yantaiRebarApi.getByRange()` |
| `fetch('/trend')` | `yantaiRebarApi.getTrend()` |
| `fetch('/materials')` | `yantaiRebarApi.getMaterials()` |
| `fetch('/specs')` | `yantaiRebarApi.getSpecs()` |
| `fetch('/dates')` | `yantaiRebarApi.getDates()` |
| `fetch('/search')` | `yantaiRebarApi.search()` |

在文件顶部的 import 部分添加：
```ts
import { yantaiRebarApi } from '../services/api';
```

**关键变更位置：**
- `loadStats()` 函数中的 stats 加载
- `loadLatestPrices()` 函数中的价格加载
- `loadTrendData()` 函数中的趋势加载
- `loadFilters()` 函数中的材料/规格加载
- `loadAvailableDates()` 函数中的日期加载
- `handleSearch()` 函数中的搜索调用

- [ ] **Step 3: Commit**

```bash
git add web/frontend/src/services/api.ts web/frontend/src/pages/PriceMonitor.tsx
git commit -m "feat: PriceMonitor 切换到 /yantai-rebar/ Supabase API"
```

---

## Task 5: 创建历史数据迁移脚本

**Files:**
- Create: `scripts/migrate_rebar_to_supabase.py`

- [ ] **Step 1: 编写迁移脚本**

```python
"""
将 SQLite yantai_rebar.db 迁移到 Supabase
运行: python scripts/migrate_rebar_to_supabase.py
"""
import sys
sys.path.insert(0, 'web/backend')

import logging
from pathlib import Path
from services.supabase_service import SupabaseService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent.parent / 'web' / 'backend' / 'data' / 'yantai_rebar.db'


def migrate():
    import sqlite3
    logger.info(f"[migrate] 开始迁移 | DB={DB_FILE}")

    if not DB_FILE.exists():
        logger.error(f"[migrate] 数据库文件不存在: {DB_FILE}")
        return

    supabase = SupabaseService()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有数据
    cursor.execute('SELECT date, fetch_time, material_name, spec, material_type, brand, price, region FROM rebar_prices ORDER BY date')
    rows = cursor.fetchall()
    conn.close()

    logger.info(f"[migrate] 读取到 {len(rows)} 条记录")

    # 批量插入
    BATCH = 100
    total_imported = 0
    total_errors = 0

    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        prices = [dict(row) for row in batch]
        result = supabase.insert_rebar_prices(prices)
        total_imported += result['imported']
        total_errors += len(result['errors'])
        logger.info(f"[migrate] 批次 {i//BATCH+1} | imported={result['imported']} | errors={len(result['errors'])}")

    logger.info(f"[migrate] 迁移完成 | 成功={total_imported} | 总数={len(rows)} | 失败={total_errors}")


if __name__ == '__main__':
    migrate()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrate_rebar_to_supabase.py
git commit -m "feat: 添加 SQLite → Supabase 钢筋价格迁移脚本"
```

---

## Task 6: 自检

执行以下检查：

- [ ] 确认 `scripts/create_rebar_prices_table.sql` 已提交
- [ ] 确认 `supabase_service.py` 中 `get_rebar_prices`、`get_rebar_latest`、`get_rebar_trend`、`get_rebar_stats`、`insert_rebar_prices` 五个方法均已添加
- [ ] 确认 `yantai_db.py` 中 `rebar_router` 已定义并导出
- [ ] 确认 `main.py` 中 `app.include_router(yantai_rebar_router)` 已添加
- [ ] 确认 `api.ts` 中 `yantaiRebarApi` 包含 8 个方法
- [ ] 确认 `PriceMonitor.tsx` 顶部 import 了 `yantaiRebarApi`
- [ ] 确认 `PriceMonitor.tsx` 中所有 `/yantai-db/` 替换为 `/yantai-rebar/`
- [ ] 确认 `migrate_rebar_to_supabase.py` 已提交
- [ ] 运行 `python -m py_compile web/backend/services/supabase_service.py`
- [ ] 运行 `python -m py_compile web/backend/api/yantai_db.py`
- [ ] 运行 `python -m py_compile scripts/migrate_rebar_to_supabase.py`