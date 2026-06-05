"""
山东烟台钢筋价格数据库API
使用SQLite数据库提供价格查询接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_FILE = 'services/data/yantai_rebar.db'


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


class PriceRecord(BaseModel):
    date: str
    time: Optional[str] = None  # 时段：上午/下午
    material_name: str
    spec: str
    material_type: str
    brand: str
    price: int
    region: str = '山东烟台'
    fetch_time: Optional[str] = None  # 原始抓取时间


class PriceSummary(BaseModel):
    total_count: int
    dates_count: int
    date_range: dict
    materials: dict
    specs: dict


@router.get("/stats", response_model=PriceSummary)
async def get_stats():
    """获取数据库统计信息"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 总记录数
        c.execute('SELECT COUNT(*) FROM rebar_prices')
        total = c.fetchone()[0]

        # 日期数
        c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
        dates = c.fetchone()[0]

        # 日期范围
        c.execute('SELECT MIN(date), MAX(date) FROM rebar_prices')
        range_row = c.fetchone()

        # 材料统计
        c.execute('SELECT material_name, COUNT(*) as cnt FROM rebar_prices GROUP BY material_name ORDER BY cnt DESC')
        materials = {row[0]: row[1] for row in c.fetchall()}

        # 规格统计
        c.execute('SELECT spec, COUNT(*) as cnt FROM rebar_prices GROUP BY spec ORDER BY cnt DESC LIMIT 20')
        specs = {row[0]: row[1] for row in c.fetchall()}

        conn.close()

        return PriceSummary(
            total_count=total,
            dates_count=dates,
            date_range={'start': range_row[0], 'end': range_row[1]},
            materials=materials,
            specs=specs
        )
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    date: str = Query(None, description="指定日期，格式: YYYY-MM-DD, YYYY-MM-DD 上午, YYYY-MM-DD 下午（较晚）"),
    limit: int = Query(500, description="返回记录数")
):
    """
    获取最新价格数据

    参数说明：
    - date: 可选，格式为 "YYYY-MM-DD" 或 "YYYY-MM-DD 上午" 或 "YYYY-MM-DD 下午（较晚）"
      - "2026-05-27" - 获取该日期所有数据
      - "2026-05-27 上午" - 获取上午数据
      - "2026-05-27 下午（较晚）" - 获取下午数据
      - 不指定则获取最新日期的数据
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 解析日期和时段
        period = None
        if date:
            # 支持中文和英文格式
            if '上午' in date:
                period = 'AM'
                date_str = date.replace(' 上午', '').strip()
            elif '下午' in date:
                period = 'PM'
                date_str = date.replace(' 下午（较晚）', '').replace(' 下午', '').strip()
            else:
                date_str = date
        else:
            date_str = None

        # 构建查询
        # fetch_time 格式: "09:00"/"AM" (上午), "PM" (下午)
        if date_str:
            if period == 'AM':
                # 只查询上午数据
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ? AND (fetch_time = '09:00' OR fetch_time = 'AM')
                    ORDER BY material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
            elif period == 'PM':
                # 只查询下午数据
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ? AND fetch_time = 'PM'
                    ORDER BY material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
            else:
                # 查询全天数据，上午优先
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ?
                    ORDER BY CASE WHEN fetch_time = '09:00' OR fetch_time = 'AM' THEN 1 ELSE 2 END, material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
        else:
            # 获取最新日期的数据
            c.execute('''
                SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = (SELECT MAX(date) FROM rebar_prices)
                ORDER BY CASE WHEN fetch_time = '09:00' OR fetch_time = 'AM' THEN 1 ELSE 2 END, material_name, spec
                LIMIT ?
            ''', (limit,))

        rows = c.fetchall()
        conn.close()

        # 处理返回数据，添加时段字段
        prices = []
        for row in rows:
            d = dict(row)
            # 根据 fetch_time 判断时段
            fetch_time = d.get('fetch_time', '')
            if fetch_time == '09:00' or fetch_time == 'AM':
                d['time'] = '上午'
            elif fetch_time == 'PM':
                d['time'] = '下午'
            else:
                d['time'] = '全天'
            prices.append(d)

        return {
            'success': True,
            'count': len(prices),
            'prices': prices
        }
    except Exception as e:
        logger.error(f"获取最新价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range")
async def get_by_range(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    material: str = Query(None, description="品名筛选"),
    spec: str = Query(None, description="规格筛选")
):
    """获取日期范围内的价格数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
            FROM rebar_prices
            WHERE date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]

        if material:
            sql += ' AND material_name LIKE ?'
            params.append(f'%{material}%')

        if spec:
            sql += ' AND spec LIKE ?'
            params.append(f'%{spec}%')

        sql += ' ORDER BY date, CASE WHEN fetch_time = \'09:00\' OR fetch_time = \'AM\' THEN 1 ELSE 2 END, material_name, spec'

        c.execute(sql, params)
        rows = c.fetchall()

        # 按日期分组
        dates_data = {}
        for row in rows:
            d = dict(row)
            # 根据 fetch_time 判断时段
            fetch_time = d.get('fetch_time', '')
            if fetch_time == '09:00' or fetch_time == 'AM':
                d['time'] = '上午'
            elif fetch_time == 'PM':
                d['time'] = '下午'
            else:
                d['time'] = '全天'

            date_str = d['date']
            if date_str not in dates_data:
                dates_data[date_str] = []
            dates_data[date_str].append(d)

        conn.close()

        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'total_count': len(rows),
            'dates_count': len(dates_data),
            'data': dates_data
        }
    except Exception as e:
        logger.error(f"获取日期范围数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_trend(
    material: str = Query(None, description="品名"),
    spec: str = Query(None, description="规格"),
    days: int = Query(365, description="天数"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """获取价格趋势数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 构建查询条件
        sql = '''
            SELECT date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as cnt
            FROM rebar_prices
            WHERE 1=1
        '''
        params = []

        if material:
            sql += ' AND material_name LIKE ?'
            params.append(f'%{material}%')

        if spec:
            sql += ' AND spec LIKE ?'
            params.append(f'%{spec}%')

        if start_date:
            sql += ' AND date >= ?'
            params.append(start_date)
        elif end_date:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            sql += ' AND date >= ?'
            params.append(cutoff)

        if end_date:
            sql += ' AND date <= ?'
            params.append(end_date)

        sql += ' GROUP BY date ORDER BY date'

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'count': len(rows),
            'data': [dict(row) for row in rows]
        }
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/materials")
async def get_materials():
    """获取所有品名类型"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('''
            SELECT DISTINCT material_name, COUNT(*) as cnt
            FROM rebar_prices
            GROUP BY material_name
            ORDER BY cnt DESC
        ''')

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'materials': [{'name': row[0], 'count': row[1]} for row in rows]
        }
    except Exception as e:
        logger.error(f"获取品名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs")
async def get_specs(material: str = Query(None, description="品名筛选")):
    """获取所有规格"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if material:
            c.execute('''
                SELECT DISTINCT spec, COUNT(*) as cnt
                FROM rebar_prices
                WHERE material_name LIKE ?
                GROUP BY spec
                ORDER BY cnt DESC
            ''', (f'%{material}%',))
        else:
            c.execute('''
                SELECT DISTINCT spec, COUNT(*) as cnt
                FROM rebar_prices
                GROUP BY spec
                ORDER BY cnt DESC
            ''')

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'specs': [{'spec': row[0], 'count': row[1]} for row in rows]
        }
    except Exception as e:
        logger.error(f"获取规格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dates")
async def get_available_dates(
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """
    获取所有可用日期（包含上午/下午标识）

    返回格式：如果某天同时有上午和下午数据，会返回两个条目
    - "2026-05-27 AM" 表示上午数据
    - "2026-05-27 PM" 表示下午数据
    """
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 获取每个日期的上午/下午数据分布，按日期降序排列（最新在前）
        # fetch_time 存储格式: "09:00"(AM), "AM", "PM", 或其他时间
        if start_date and end_date:
            c.execute('SELECT date, SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count, SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count FROM rebar_prices WHERE date BETWEEN ? AND ? GROUP BY date ORDER BY date DESC', (start_date, end_date))
        elif start_date:
            c.execute('SELECT date, SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count, SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count FROM rebar_prices WHERE date >= ? GROUP BY date ORDER BY date DESC', (start_date,))
        elif end_date:
            c.execute('SELECT date, SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count, SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count FROM rebar_prices WHERE date <= ? GROUP BY date ORDER BY date DESC', (end_date,))
        else:
            # 不指定范围时，返回所有日期
            c.execute('SELECT date, SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count, SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count FROM rebar_prices GROUP BY date ORDER BY date')

        rows = c.fetchall()
        conn.close()

        # 调试信息
        logger.info(f"[DEBUG] SQL返回了 {len(rows)} 行")
        logger.info(f"[DEBUG] 前5个日期: {[row['date'] for row in rows[:5]]}")

        # 构建日期列表，如果有多个时段则分开
        dates = []
        for row in rows:
            date_str = row['date']
            am_count = row['am_count']
            pm_count = row['pm_count']

            if am_count > 0 and pm_count > 0:
                # 同时有上午和下午，返回两个条目（上午在前，较晚在后）
                dates.append(f"{date_str} 上午")
                dates.append(f"{date_str} 下午（较晚）")
            elif am_count > 0:
                # 只有上午
                dates.append(f"{date_str} 上午")
            elif pm_count > 0:
                # 只有下午
                dates.append(f"{date_str} 下午（较晚）")
            else:
                # 没有时段信息，返回日期本身
                dates.append(date_str)

        # 反转列表，使最新的日期在前
        dates.reverse()

        return {
            'success': True,
            'count': len(dates),
            'dates': dates,
            'test_reversed': True  # 测试字段
        }
    except Exception as e:
        logger.error(f"获取日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_prices(
    keyword: str = Query(..., description="搜索关键词"),
    date: str = Query(None, description="指定日期"),
    limit: int = Query(100, description="返回数量")
):
    """搜索价格数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
            FROM rebar_prices
            WHERE (material_name LIKE ? OR spec LIKE ? OR brand LIKE ? OR material_type LIKE ?)
        '''
        params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

        if date:
            sql += ' AND date = ?'
            params.append(date)

        sql += ' ORDER BY date DESC, CASE WHEN fetch_time = \'09:00\' OR fetch_time = \'AM\' THEN 1 ELSE 2 END, material_name, spec LIMIT ?'
        params.append(limit)

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        # 处理返回数据，添加时段字段
        prices = []
        for row in rows:
            d = dict(row)
            fetch_time = d.get('fetch_time', '')
            if fetch_time == '09:00' or fetch_time == 'AM':
                d['time'] = '上午'
            elif fetch_time == 'PM':
                d['time'] = '下午'
            else:
                d['time'] = '全天'
            prices.append(d)

        return {
            'success': True,
            'count': len(prices),
            'keyword': keyword,
            'prices': prices
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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