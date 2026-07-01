"""
烟台钢筋价格统一 API
整合所有烟台钢筋价格相关的接口，使用统一的路由前缀 /api/rebar

功能模块：
- 状态与凭据管理
- 数据抓取
- 数据查询（SQLite/Supabase）
- 报告分析
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 数据库配置
DB_FILE = 'data/yantai_rebar.db'

# ============================================================
# 路由定义
# ============================================================

router = APIRouter(prefix="/api/rebar", tags=["烟台钢筋价格"])

# ============================================================
# 数据模型
# ============================================================

class MaterialPriceResponse(BaseModel):
    material_id: str
    material_name: str
    spec: str
    material_type: str
    brand: str
    price: float
    price_max: float = 0.0
    unit: str = "元/吨"
    price_change: str = ""
    remark: str = ""
    steel_code: str = ""
    region: str = "山东烟台"


class FetchResultResponse(BaseModel):
    success: bool
    source_name: str
    fetched_at: str
    prices: List[MaterialPriceResponse]
    error_message: str = ""
    is_mock: bool = False


class PriceRecord(BaseModel):
    date: str
    time: Optional[str] = None
    material_name: str
    spec: str
    material_type: str
    brand: str
    price: int
    region: str = '山东烟台'
    fetch_time: Optional[str] = None


class PriceSummary(BaseModel):
    total_count: int
    dates_count: int
    date_range: dict
    materials: dict
    specs: dict


class RebarPriceRecord(BaseModel):
    date: str
    fetch_time: Optional[str] = None
    material_name: str
    spec: Optional[str] = None
    material_type: Optional[str] = None
    brand: Optional[str] = None
    price: int
    region: str = '山东烟台'


# ============================================================
# 辅助函数
# ============================================================

def get_db_connection():
    """获取SQLite数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_supabase_service():
    """获取Supabase服务（如果配置）"""
    try:
        from services.supabase_service import SupabaseService
        return SupabaseService()
    except:
        return None


def _get_configured_credentials():
    """获取配置的凭据（支持加密存储）"""
    try:
        from services.secure_storage import get_credential
        cred = get_credential('mysteel')
        if cred:
            return cred.get('username'), cred.get('password')
    except ImportError:
        pass

    # 回退：尝试从配置文件读取
    try:
        config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('username'), config.get('password')
    except:
        pass

    return None, None


def _parse_date_period(date: str) -> tuple:
    """
    解析日期和时段

    Returns:
        (date_str, period): period = 'AM', 'PM', or None
    """
    if not date:
        return None, None

    if '上午' in date:
        return date.replace(' 上午', '').strip(), 'AM'
    elif '下午' in date:
        return date.replace(' 下午（较晚）', '').replace(' 下午', '').strip(), 'PM'
    else:
        return date, None


def _format_time_period(fetch_time: str) -> str:
    """根据fetch_time返回时段"""
    if fetch_time == '09:00' or fetch_time == 'AM':
        return '上午'
    elif fetch_time == 'PM':
        return '下午'
    else:
        return '全天'


# ============================================================
# 模块1: 状态与凭据管理
# ============================================================

@router.get("/status")
async def get_fetch_status():
    """
    获取抓取状态

    返回最近一次抓取的时间、结果和数据条数
    """
    logger.info("[get_fetch_status] 获取抓取状态")
    last_fetch_file = Path(__file__).parent.parent / 'services' / 'logs' / 'yantai_last_fetch.json'

    if last_fetch_file.exists():
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "last_fetch": data.get('last_fetch'),
                "success": data.get('success'),
                "prices_count": data.get('prices_count'),
                "region": data.get('region')
            }

    return {
        "last_fetch": None,
        "success": None,
        "prices_count": 0,
        "region": "山东烟台"
    }


@router.get("/check")
async def check_fetch_status():
    """
    检查今日是否已抓取

    返回布尔值表示今日是否已完成抓取
    """
    logger.info("[check_fetch_status] 检查今日抓取状态")
    last_fetch_file = Path(__file__).parent.parent / 'services' / 'logs' / 'yantai_last_fetch.json'
    today = datetime.now().date().isoformat()

    if last_fetch_file.exists():
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_fetch_date = data.get('last_fetch', '')[:10]

            if last_fetch_date == today:
                return {
                    "fetched_today": True,
                    "last_fetch": data.get('last_fetch'),
                    "success": data.get('success'),
                    "prices_count": data.get('prices_count', 0),
                    "message": f"今日({today})已抓取，共{data.get('prices_count', 0)}条记录"
                }

    return {
        "fetched_today": False,
        "last_fetch": None,
        "message": "今日尚未抓取，可以执行抓取"
    }


@router.post("/credentials")
async def update_credentials(username: str, password: str):
    """
    更新登录凭据（使用加密存储）

    - username: 我的钢铁网用户名
    - password: 我的钢铁网密码

    更新后会自动删除旧Cookie，下次抓取会重新登录
    """
    logger.info(f"[update_credentials] 更新凭据 | username={username[:3]}***")
    try:
        # 优先使用加密存储
        try:
            from services.secure_storage import save_credential
            save_credential('mysteel', username, password)
            logger.info("[update_credentials] 凭据已加密保存")
        except ImportError:
            # 回退：保存到配置文件
            config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({'username': username, 'password': password}, f, ensure_ascii=False, indent=2)
            logger.warning("[update_credentials] 凭据保存到未加密文件")

        # 删除旧Cookie，强制重新登录
        cookie_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_cookies.json'
        if cookie_file.exists():
            cookie_file.unlink()
            logger.info("[update_credentials] 已删除旧Cookie")

        return {
            "success": True,
            "message": "凭据已更新，请重新抓取以验证"
        }

    except Exception as e:
        logger.error(f"[update_credentials] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def get_credentials_status():
    """
    获取当前凭据状态（不返回密码）

    返回是否已配置凭据
    """
    logger.info("[get_credentials_status] 获取凭据状态")
    username, _ = _get_configured_credentials()

    return {
        "has_username": bool(username),
        "username": username[:3] + '***' if username else None,
        "has_password": True,
        "storage_type": "encrypted"
    }


# ============================================================
# 模块2: 数据抓取
# ============================================================

@router.post("/fetch")
async def fetch_prices(force: bool = False):
    """
    抓取山东烟台钢筋价格

    - force: 是否强制抓取（忽略每天一次的限制）

    返回抓取结果，包含价格列表
    """
    logger.info(f"[fetch_prices] 开始抓取 | force={force}")
    try:
        from services.fetch_yantai import run_fetch

        result = await run_fetch()

        if result['success']:
            is_mock = "模拟" in result.get('source_name', '')
            logger.info(f"[fetch_prices] 抓取成功 | count={len(result.get('prices', []))}")

            return FetchResultResponse(
                success=True,
                source_name=result.get('source_name', '我的钢铁网-山东烟台'),
                fetched_at=result.get('fetched_at', ''),
                prices=[
                    MaterialPriceResponse(
                        material_id=f"yt_{p['material_name']}_{p['spec']}_{p['brand']}",
                        material_name=p['material_name'],
                        spec=p['spec'],
                        material_type=p['material_type'],
                        brand=p['brand'],
                        price=p['price'],
                        price_max=0,
                        unit='元/吨',
                        price_change='',
                        remark='',
                        steel_code='',
                        region='山东烟台'
                    )
                    for p in result.get('prices', [])
                ],
                is_mock=is_mock
            )
        else:
            logger.error(f"[fetch_prices] 抓取失败 | error={result.get('error')}")
            return FetchResultResponse(
                success=False,
                source_name='我的钢铁网-山东烟台',
                fetched_at="",
                prices=[],
                error_message=result.get('error', '未知错误')
            )

    except Exception as e:
        logger.error(f"[fetch_prices] 抓取异常 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-historical")
async def fetch_historical_prices(days: int = 7):
    """
    抓取历史价格数据（最近N天）

    - days: 抓取最近几天的数据，默认7天

    返回每天的抓取结果和数据统计
    """
    logger.info(f"[fetch_historical_prices] 抓取历史数据 | days={days}")
    try:
        from services.fetch_yantai_api import fetch_historical_prices

        result = await fetch_historical_prices(days=days)

        logger.info(f"[fetch_historical_prices] 完成 | dates={result.get('dates_fetched', 0)}, prices={result.get('total_prices', 0)}")

        return {
            "success": result['success'],
            "dates_fetched": result.get('dates_fetched', 0),
            "total_prices": result.get('total_prices', 0),
            "data": result.get('data', {}),
            "error": result.get('error', '')
        }

    except Exception as e:
        logger.error(f"[fetch_historical_prices] 抓取失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 模块3: 统计信息
# ============================================================

@router.get("/stats")
async def get_stats():
    """
    获取数据库统计信息

    返回总记录数、日期数、日期范围、材料统计、规格统计
    """
    logger.info("[get_stats] 获取统计信息")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            result = supabase.get_rebar_stats()
            if result.get('total_count', 0) > 0:
                logger.info(f"[get_stats] Supabase | total={result.get('total_count')}")
                return result
        except Exception as e:
            logger.warning(f"[get_stats] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute('SELECT COUNT(*) FROM rebar_prices')
        total = c.fetchone()[0]

        c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
        dates = c.fetchone()[0]

        c.execute('SELECT MIN(date), MAX(date) FROM rebar_prices')
        range_row = c.fetchone()

        c.execute('SELECT material_name, COUNT(*) as cnt FROM rebar_prices GROUP BY material_name ORDER BY cnt DESC')
        materials = {row[0]: row[1] for row in c.fetchall()}

        c.execute('SELECT spec, COUNT(*) as cnt FROM rebar_prices GROUP BY spec ORDER BY cnt DESC LIMIT 20')
        specs = {row[0]: row[1] for row in c.fetchall()}

        conn.close()

        result = PriceSummary(
            total_count=total,
            dates_count=dates,
            date_range={'start': range_row[0], 'end': range_row[1]},
            materials=materials,
            specs=specs
        )
        logger.info(f"[get_stats] SQLite | total={total}")
        return result

    except Exception as e:
        conn.close()
        logger.error(f"[get_stats] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 模块4: 数据查询
# ============================================================

@router.get("/latest")
async def get_latest(
    date: str = Query(None, description="指定日期 YYYY-MM-DD 或 YYYY-MM-DD 上午/下午"),
    limit: int = Query(500, description="返回数量")
):
    """
    获取最新价格数据

    参数：
    - date: 可选日期
      - "2026-05-27" - 获取该日期所有数据
      - "2026-05-27 上午" - 获取上午数据
      - "2026-05-27 下午" - 获取下午数据
      - 不指定则获取最新日期数据
    - limit: 返回记录数
    """
    logger.info(f"[get_latest] 查询 | date={date} | limit={limit}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            result = supabase.get_rebar_latest(limit=limit)
            if result.get('count', 0) > 0:
                logger.info(f"[get_latest] Supabase | count={result.get('count')}")
                return result
        except Exception as e:
            logger.warning(f"[get_latest] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
        date_str, period = _parse_date_period(date)

        if date_str:
            if period == 'AM':
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ? AND (fetch_time = '09:00' OR fetch_time = 'AM')
                    ORDER BY material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
            elif period == 'PM':
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ? AND fetch_time = 'PM'
                    ORDER BY material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
            else:
                c.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ?
                    ORDER BY CASE WHEN fetch_time = '09:00' OR fetch_time = 'AM' THEN 1 ELSE 2 END, material_name, spec
                    LIMIT ?
                ''', (date_str, limit))
        else:
            c.execute('''
                SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = (SELECT MAX(date) FROM rebar_prices)
                ORDER BY CASE WHEN fetch_time = '09:00' OR fetch_time = 'AM' THEN 1 ELSE 2 END, material_name, spec
                LIMIT ?
            ''', (limit,))

        rows = c.fetchall()
        conn.close()

        prices = []
        for row in rows:
            d = dict(row)
            d['time'] = _format_time_period(d.get('fetch_time', ''))
            prices.append(d)

        logger.info(f"[get_latest] SQLite | count={len(prices)}")
        return {
            'success': True,
            'count': len(prices),
            'prices': prices
        }

    except Exception as e:
        conn.close()
        logger.error(f"[get_latest] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range")
async def get_by_range(
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    material: str = Query(None, description="品名筛选"),
    spec: str = Query(None, description="规格筛选")
):
    """
    获取日期范围内的价格数据

    返回按日期分组的价格数据
    """
    logger.info(f"[get_by_range] 查询 | start={start_date} | end={end_date}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            prices = supabase.get_rebar_prices(
                start_date=start_date, end_date=end_date,
                material_name=material, spec=spec, limit=5000
            )
            if prices:
                dates_data: Dict[str, List[Dict]] = {}
                for p in prices:
                    d = p.get('date', '')
                    if d not in dates_data:
                        dates_data[d] = []
                    dates_data[d].append(p)
                logger.info(f"[get_by_range] Supabase | total={len(prices)}")
                return {
                    'success': True,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_count': len(prices),
                    'dates_count': len(dates_data),
                    'data': dates_data
                }
        except Exception as e:
            logger.warning(f"[get_by_range] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
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
        conn.close()

        dates_data = {}
        for row in rows:
            d = dict(row)
            d['time'] = _format_time_period(d.get('fetch_time', ''))
            date_str = d['date']
            if date_str not in dates_data:
                dates_data[date_str] = []
            dates_data[date_str].append(d)

        logger.info(f"[get_by_range] SQLite | total={len(rows)}")
        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'total_count': len(rows),
            'dates_count': len(dates_data),
            'data': dates_data
        }

    except Exception as e:
        conn.close()
        logger.error(f"[get_by_range] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_trend(
    material: str = Query(None, description="品名"),
    spec: str = Query(None, description="规格"),
    days: int = Query(365, description="天数"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """
    获取价格趋势数据

    返回按日期聚合的均价、最高价、最低价
    """
    logger.info(f"[get_trend] 查询 | material={material} | days={days}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            result = supabase.get_rebar_trend(
                material_name=material, spec=spec,
                days=days, start_date=start_date, end_date=end_date
            )
            if result.get('count', 0) > 0:
                return result
        except Exception as e:
            logger.warning(f"[get_trend] Supabase查询失败，回退SQLite | {e}")

    # 计算日期范围
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    conn = get_db_connection()
    c = conn.cursor()

    try:
        sql = '''
            SELECT date, AVG(price) as avg_price, MIN(price) as min_price,
                   MAX(price) as max_price, COUNT(*) as cnt
            FROM rebar_prices
            WHERE date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]

        if material:
            sql += ' AND material_name = ?'
            params.append(material)

        if spec:
            sql += ' AND spec = ?'
            params.append(spec)

        sql += ' GROUP BY date ORDER BY date'

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        trend_data = [
            {'date': row['date'], 'avg_price': row['avg_price'],
             'min_price': row['min_price'], 'max_price': row['max_price'],
             'count': row['cnt']}
            for row in rows
        ]

        logger.info(f"[get_trend] SQLite | count={len(trend_data)}")
        return {
            'success': True,
            'count': len(trend_data),
            'data': trend_data
        }

    except Exception as e:
        conn.close()
        logger.error(f"[get_trend] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/materials")
async def get_materials():
    """
    获取所有品名类型

    返回品名列表及数量统计
    """
    logger.info("[get_materials] 获取品名")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            stats = supabase.get_rebar_stats()
            materials = [{'name': k, 'count': v} for k, v in stats.get('materials', {}).items()]
            if materials:
                return {'success': True, 'materials': materials}
        except Exception as e:
            logger.warning(f"[get_materials] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute('''
            SELECT DISTINCT material_name, COUNT(*) as cnt
            FROM rebar_prices
            GROUP BY material_name
            ORDER BY cnt DESC
        ''')

        rows = c.fetchall()
        conn.close()

        materials = [{'name': row['material_name'], 'count': row['cnt']} for row in rows]
        logger.info(f"[get_materials] SQLite | count={len(materials)}")
        return {'success': True, 'materials': materials}

    except Exception as e:
        conn.close()
        logger.error(f"[get_materials] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs")
async def get_specs(material: str = Query(None, description="品名筛选")):
    """
    获取所有规格

    返回规格列表及数量统计
    """
    logger.info(f"[get_specs] 获取规格 | material={material}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            stats = supabase.get_rebar_stats()
            specs = [{'spec': k, 'count': v} for k, v in stats.get('specs', {}).items()]
            if specs:
                return {'success': True, 'specs': specs}
        except Exception as e:
            logger.warning(f"[get_specs] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
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

        specs = [{'spec': row['spec'], 'count': row['cnt']} for row in rows]
        logger.info(f"[get_specs] SQLite | count={len(specs)}")
        return {'success': True, 'specs': specs}

    except Exception as e:
        conn.close()
        logger.error(f"[get_specs] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dates")
async def get_available_dates(
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """
    获取所有可用日期

    返回日期列表，包含上午/下午标识
    - "2026-05-27 上午" 表示上午数据
    - "2026-05-27 下午" 表示下午数据
    """
    logger.info("[get_dates] 获取可用日期")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            prices = supabase.get_rebar_prices(start_date=start_date, end_date=end_date, limit=10000)
            if prices:
                date_periods = []
                for p in prices:
                    d = p.get('date', '')
                    ft = p.get('fetch_time', '')
                    if ft in ('09:00', 'AM'):
                        date_periods.append(f"{d} 上午")
                    elif ft == 'PM':
                        date_periods.append(f"{d} 下午")
                    else:
                        date_periods.append(d)

                # 去重并保持顺序
                unique = []
                seen = set()
                for dp in date_periods:
                    if dp not in seen:
                        seen.add(dp)
                        unique.append(dp)

                logger.info(f"[get_dates] Supabase | count={len(unique)}")
                return {'success': True, 'count': len(unique), 'dates': unique}
        except Exception as e:
            logger.warning(f"[get_dates] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
        if start_date and end_date:
            c.execute('''
                SELECT date,
                       SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count,
                       SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count
                FROM rebar_prices
                WHERE date BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date DESC
            ''', (start_date, end_date))
        elif start_date:
            c.execute('''
                SELECT date,
                       SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count,
                       SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count
                FROM rebar_prices
                WHERE date >= ?
                GROUP BY date
                ORDER BY date DESC
            ''', (start_date,))
        elif end_date:
            c.execute('''
                SELECT date,
                       SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count,
                       SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count
                FROM rebar_prices
                WHERE date <= ?
                GROUP BY date
                ORDER BY date DESC
            ''', (end_date,))
        else:
            c.execute('''
                SELECT date,
                       SUM(CASE WHEN fetch_time = "09:00" OR fetch_time = "AM" THEN 1 ELSE 0 END) as am_count,
                       SUM(CASE WHEN fetch_time = "PM" THEN 1 ELSE 0 END) as pm_count
                FROM rebar_prices
                GROUP BY date
                ORDER BY date DESC
            ''')

        rows = c.fetchall()
        conn.close()

        dates = []
        for row in rows:
            date_str = row['date']
            am_count = row['am_count']
            pm_count = row['pm_count']

            if am_count > 0 and pm_count > 0:
                dates.append(f"{date_str} 上午")
                dates.append(f"{date_str} 下午")
            elif am_count > 0:
                dates.append(f"{date_str} 上午")
            elif pm_count > 0:
                dates.append(f"{date_str} 下午")
            else:
                dates.append(date_str)

        # SQL查询已经是 ORDER BY date DESC，所以列表已经是最新的在前
        # 无需反转

        logger.info(f"[get_dates] SQLite | count={len(dates)}")
        return {'success': True, 'count': len(dates), 'dates': dates}

    except Exception as e:
        conn.close()
        logger.error(f"[get_dates] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_prices(
    keyword: str = Query(..., description="搜索关键词"),
    date: str = Query(None, description="指定日期"),
    limit: int = Query(100, description="返回数量")
):
    """
    搜索价格数据

    支持按品名、规格、品牌、材质搜索
    """
    logger.info(f"[search] 搜索 | keyword={keyword}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            prices = supabase.get_rebar_prices(date=date, limit=limit)
            kw = keyword.lower()
            filtered = [
                p for p in prices
                if kw in str(p.get('material_name', '')).lower()
                or kw in str(p.get('spec', '')).lower()
                or kw in str(p.get('brand', '')).lower()
                or kw in str(p.get('material_type', '')).lower()
            ]
            logger.info(f"[search] Supabase | found={len(filtered)}")
            return {'success': True, 'count': len(filtered), 'prices': filtered}
        except Exception as e:
            logger.warning(f"[search] Supabase查询失败，回退SQLite | {e}")

    # SQLite回退
    conn = get_db_connection()
    c = conn.cursor()

    try:
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

        prices = []
        for row in rows:
            d = dict(row)
            d['time'] = _format_time_period(d.get('fetch_time', ''))
            prices.append(d)

        logger.info(f"[search] SQLite | found={len(prices)}")
        return {'success': True, 'count': len(prices), 'prices': prices}

    except Exception as e:
        conn.close()
        logger.error(f"[search] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 模块5: 报告分析
# ============================================================

@router.get("/report/summary")
async def get_report_summary(
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    material_type: str = Query(None, description="品名筛选")
):
    """
    获取价格报告摘要数据

    包含价格统计、品名分析、品牌分析、规格分析
    """
    logger.info(f"[get_report_summary] 查询 | start={start_date} | end={end_date} | type={material_type}")

    # 默认日期范围：最近30天
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    conn = get_db_connection()
    c = conn.cursor()

    try:
        sql = '''SELECT material_name, spec, brand, price FROM rebar_prices WHERE date BETWEEN ? AND ?'''
        params = [start_date, end_date]

        if material_type:
            sql += ' AND material_name = ?'
            params.append(material_type)

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            logger.warning(f"[get_report_summary] 无数据")
            return {'success': False, 'error': '指定日期范围内暂无数据'}

        prices = [{'material_name': r['material_name'], 'spec': r['spec'], 'brand': r['brand'], 'price': r['price']} for r in rows]
        price_values = [p['price'] for p in prices if p['price'] > 0]

        if not price_values:
            return {'success': False, 'error': '数据中无有效价格'}

        # 计算统计
        avg_price = sum(price_values) / len(price_values)
        min_price = min(price_values)
        max_price = max(price_values)
        variance = sum((p - avg_price) ** 2 for p in price_values) / len(price_values)
        std_deviation = variance ** 0.5

        # 按品名分组
        material_stats: Dict[str, Dict] = {}
        for p in prices:
            name = p['material_name']
            if name not in material_stats:
                material_stats[name] = {'count': 0, 'prices': []}
            material_stats[name]['count'] += 1
            if p['price'] > 0:
                material_stats[name]['prices'].append(p['price'])

        material_summary = []
        for name, info in material_stats.items():
            if info['prices']:
                material_summary.append({
                    'name': name,
                    'count': info['count'],
                    'avg_price': round(sum(info['prices']) / len(info['prices'])),
                    'min_price': min(info['prices']),
                    'max_price': max(info['prices'])
                })
        material_summary.sort(key=lambda x: x['count'], reverse=True)

        # 按品牌分组
        brand_stats: Dict[str, Dict] = {}
        for p in prices:
            brand = p['brand']
            if brand not in brand_stats:
                brand_stats[brand] = {'count': 0, 'prices': []}
            brand_stats[brand]['count'] += 1
            if p['price'] > 0:
                brand_stats[brand]['prices'].append(p['price'])

        brand_summary = []
        for name, info in brand_stats.items():
            if info['prices']:
                brand_summary.append({
                    'name': name,
                    'count': info['count'],
                    'avg_price': round(sum(info['prices']) / len(info['prices'])),
                    'min_price': min(info['prices']),
                    'max_price': max(info['prices'])
                })
        brand_summary.sort(key=lambda x: x['avg_price'], reverse=True)

        # 按规格分组
        spec_stats: Dict[str, Dict] = {}
        for p in prices:
            spec = p['spec']
            if spec not in spec_stats:
                spec_stats[spec] = {'count': 0, 'prices': []}
            spec_stats[spec]['count'] += 1
            if p['price'] > 0:
                spec_stats[spec]['prices'].append(p['price'])

        spec_summary = []
        for name, info in spec_stats.items():
            if info['prices']:
                spec_summary.append({
                    'spec': name,
                    'count': info['count'],
                    'avg_price': round(sum(info['prices']) / len(info['prices'])),
                    'min_price': min(info['prices']),
                    'max_price': max(info['prices'])
                })
        # 按规格数字排序
        spec_summary.sort(key=lambda x: int(''.join(filter(str.isdigit, x['spec'])) or '0'))

        logger.info(f"[get_report_summary] 完成 | prices={len(prices)}")

        return {
            'success': True,
            'data': {
                'total_count': len(prices),
                'date_range': {'start': start_date, 'end': end_date},
                'price_stats': {
                    'avg_price': round(avg_price),
                    'min_price': min_price,
                    'max_price': max_price,
                    'std_deviation': round(std_deviation),
                    'price_range': max_price - min_price
                },
                'material_summary': material_summary,
                'brand_summary': brand_summary[:10],
                'spec_summary': spec_summary
            }
        }

    except Exception as e:
        conn.close()
        logger.error(f"[get_report_summary] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/influencing-factors")
async def get_influencing_factors():
    """
    获取价格影响因素分析

    基于最近7天和30天的价格变化分析市场趋势
    """
    logger.info("[get_influencing_factors] 获取影响因素分析")

    # 获取最近30天的数据
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    conn = get_db_connection()
    c = conn.cursor()

    try:
        # 最近7天均价
        c.execute('SELECT price FROM rebar_prices WHERE date >= ? AND price > 0', [week_ago])
        prices_7d = [r['price'] for r in c.fetchall()]
        avg_7d = round(sum(prices_7d) / len(prices_7d)) if prices_7d else 0

        # 最近30天均价
        c.execute('SELECT price FROM rebar_prices WHERE date >= ? AND price > 0', [start_date])
        prices_30d = [r['price'] for r in c.fetchall()]
        avg_30d = round(sum(prices_30d) / len(prices_30d)) if prices_30d else 0

        # 计算波动性
        if prices_30d:
            avg = sum(prices_30d) / len(prices_30d)
            variance = sum((p - avg) ** 2 for p in prices_30d) / len(prices_30d)
            volatility = round((variance ** 0.5) / avg * 100, 2)
        else:
            volatility = 0

        conn.close()

        # 判断趋势
        if avg_7d > avg_30d:
            trend = '上涨'
            change_rate = round((avg_7d - avg_30d) / avg_30d * 100, 2) if avg_30d > 0 else 0
        elif avg_7d < avg_30d:
            trend = '下跌'
            change_rate = round((avg_7d - avg_30d) / avg_30d * 100, 2) if avg_30d > 0 else 0
        else:
            trend = '平稳'
            change_rate = 0

        # 成本支撑评估
        cost_support = '较强' if volatility < 3 else '一般' if volatility < 6 else '较弱'

        logger.info(f"[get_influencing_factors] 完成 | trend={trend} | change={change_rate}%")

        return {
            'success': True,
            'data': {
                'period_comparison': {
                    'avg_7d': avg_7d,
                    'avg_30d': avg_30d,
                    'change_rate': change_rate,
                    'trend': trend
                },
                'supply_analysis': {
                    'market_volatility': volatility,
                    'cost_support': cost_support,
                    'assessment': f'近期市场价格{trend}，成本支撑{cost_support}'
                }
            }
        }

    except Exception as e:
        conn.close()
        logger.error(f"[get_influencing_factors] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prices")
async def insert_prices(prices: List[RebarPriceRecord]):
    """
    批量插入价格数据

    用于批量导入价格数据到数据库
    """
    logger.info(f"[insert_prices] 插入 | count={len(prices)}")

    # 先尝试Supabase
    supabase = get_supabase_service()
    if supabase and supabase.url:
        try:
            data = [p.model_dump() for p in prices]
            result = supabase.insert_rebar_prices(data)
            logger.info(f"[insert_prices] Supabase | imported={result['imported']}")
            return result
        except Exception as e:
            logger.warning(f"[insert_prices] Supabase插入失败，回退SQLite | {e}")

    # SQLite回退
    from services.price.yantai_db_service import YantaiDBService
    service = YantaiDBService()

    data = [p.model_dump() for p in prices]
    result = service.insert_prices(data)

    logger.info(f"[insert_prices] SQLite | inserted={result['inserted']}")
    return result
