"""
山东烟台钢筋价格抓取 API v7.0 - 支持品牌维度
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class MaterialPriceResponse(BaseModel):
    material_id: str
    material_name: str  # 品名：高线、螺纹钢、盘螺、圆钢
    spec: str           # 规格：如 Φ6、Φ8、Φ10
    material_type: str  # 材质：如 HPB300、HRB400E、HRB500E
    brand: str          # 钢厂/产地
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
    fetched_at: str
    source: str
    prices: List[MaterialPriceResponse]


class PriceSummary(BaseModel):
    """价格汇总"""
    total_count: int
    brands: List[str]
    material_types: dict  # {品名: 数量}
    brands_detail: dict   # {品名: [品牌列表]}


@router.get("/status")
async def get_fetch_status():
    """获取抓取状态"""
    from pathlib import Path
    import os

    last_fetch_file = Path(os.path.join(os.path.dirname(__file__), '..', 'services', 'logs', 'yantai_last_fetch.json'))
    if last_fetch_file.exists():
        import json
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


@router.post("/fetch", response_model=FetchResultResponse)
async def fetch_prices(force: bool = False):
    """
    抓取山东烟台钢筋价格（品牌维度）

    - force: 是否强制抓取（忽略每天一次的限制）
    """
    try:
        from services.fetch_yantai import run_fetch

        result = await run_fetch()

        if result['success']:
            # 判断是否是模拟数据
            is_mock = "模拟" in result.get('source_name', '')

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
            return FetchResultResponse(
                success=False,
                source_name='我的钢铁网-山东烟台',
                fetched_at="",
                prices=[],
                error_message=result.get('error', '未知错误')
            )

    except Exception as e:
        logger.error(f"抓取失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-credentials")
async def update_credentials(username: str, password: str):
    """
    更新登录凭据

    - username: 我的钢铁网用户名
    - password: 我的钢铁网密码
    """
    try:
        import json
        from pathlib import Path

        config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
        config_file.parent.mkdir(exist_ok=True)

        config = {
            'username': username,
            'password': password
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 删除旧Cookie，强制重新登录
        cookie_file = config_file.parent / 'mysteel_cookies.json'
        if cookie_file.exists():
            cookie_file.unlink()

        return {
            "success": True,
            "message": "凭据已更新，请重新抓取以验证"
        }

    except Exception as e:
        logger.error(f"更新凭据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def get_credentials_status():
    """
    获取当前凭据状态（不返回密码）
    """
    from services.yantai_rebar_scraper import YantaiRebarScraper
    import os

    scraper = YantaiRebarScraper()
    config_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', 'mysteel_config.json')

    if os.path.exists(config_file):
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return {
                "has_username": bool(config.get('username')),
                "username": config.get('username', '')[:3] + '***' if config.get('username') else None,
                "has_password": bool(config.get('password'))
            }

    return {
        "has_username": False,
        "username": None,
        "has_password": False
    }


@router.get("/summary", response_model=PriceSummary)
async def get_price_summary(include_all: bool = False):
    """
    获取价格汇总（按品名、品牌统计）

    - include_all: 是否包含所有历史天数的数据，默认只返回最新一天
    """
    try:
        from services.yantai_rebar_scraper import read_from_excel
        import os

        # 修正Excel路径：从api目录相对于services目录
        excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

        all_data = read_from_excel(excel_file)
        if not all_data:
            return PriceSummary(
                total_count=0,
                brands=[],
                material_types={},
                brands_detail={}
            )

        # 收集所有日期的数据
        all_prices = []
        if include_all:
            # 包含所有sheet的数据
            for sheet_data in all_data.values():
                all_prices.extend(sheet_data.get('prices', []))
        else:
            # 只获取最新一天的数据
            latest_sheet = sorted(all_data.keys())[-1] if all_data else None
            if not latest_sheet:
                return PriceSummary(
                    total_count=0,
                    brands=[],
                    material_types={},
                    brands_detail={}
                )
            all_prices = all_data[latest_sheet].get('prices', [])

        # 统计
        brands = set()
        material_types = {}
        brands_detail = {}

        for p in all_prices:
            brand = p.get('brand', '')
            material_name = p.get('material_name', '')

            if brand:
                brands.add(brand)

            if material_name:
                material_types[material_name] = material_types.get(material_name, 0) + 1

                if material_name not in brands_detail:
                    brands_detail[material_name] = []
                if brand and brand not in brands_detail[material_name]:
                    brands_detail[material_name].append(brand)

        return PriceSummary(
            total_count=len(all_prices),
            brands=sorted(list(brands)),
            material_types=material_types,
            brands_detail=brands_detail
        )

    except Exception as e:
        logger.error(f"获取汇总失败: {e}")
        return PriceSummary(
            total_count=0,
            brands=[],
            material_types={},
            brands_detail={}
        )


@router.get("/all")
async def get_all_prices():
    """
    获取所有历史价格数据（全部推送到前端）

    返回所有日期的数据，用于前端展示和计算
    """
    from services.yantai_rebar_scraper import read_from_excel

    excel_file = "services/data/山东烟台钢筋价格.xlsx"
    all_data = read_from_excel(excel_file)

    if not all_data:
        return {
            "success": False,
            "data": {},
            "total_sheets": 0,
            "message": "暂无数据"
        }

    # 按日期分组
    date_groups = {}
    for sheet_name, sheet_data in all_data.items():
        date_str = sheet_name[:10]
        if date_str not in date_groups:
            date_groups[date_str] = []
        date_groups[date_str].extend(sheet_data.get('prices', []))

    # 构建结果
    result = {}
    for date_str, prices in date_groups.items():
        result[date_str] = {
            "prices": [
                {
                    "date": date_str,
                    "time": p.get('time', ''),
                    "material_id": f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
                    "material_name": p.get('material_name', ''),
                    "spec": p.get('spec', ''),
                    "material_type": p.get('material_type', ''),
                    "brand": p.get('brand', ''),
                    "price": p.get('price', 0),
                    "price_max": p.get('price_max', 0),
                    "unit": p.get('unit', '元/吨'),
                    "price_change": p.get('price_change', ''),
                    "remark": p.get('remark', ''),
                    "steel_code": p.get('steel_code', ''),
                    "region": p.get('region', '山东烟台')
                }
                for p in prices
            ],
            "count": len(prices)
        }

    return {
        "success": True,
        "data": result,
        "total_dates": len(result),
        "total_prices": sum(len(d['prices']) for d in result.values()),
        "date_range": {
            "start": min(result.keys()) if result else None,
            "end": max(result.keys()) if result else None
        }
    }


@router.get("/latest")
async def get_latest_price(date: str = None, sheet: str = None):
    """
    获取最新价格

    - date: 指定日期（如 2026-05-16），返回该日期最新的数据
    - sheet: 指定具体sheet（如 2026-05-16_PM_211954），优先级高于date
    """
    from services.yantai_rebar_scraper import read_from_excel
    import os

    # 修正Excel路径 - 使用相对路径
    excel_file = "services/data/山东烟台钢筋价格.xlsx"

    all_data = read_from_excel(excel_file)
    if not all_data:
        return {"success": False, "prices": []}

    # 如果指定了sheet，直接使用
    if sheet and sheet in all_data:
        target_sheet = sheet
    # 如果指定了日期，查找包含该日期的sheet
    elif date:
        # 匹配纯日期(2026-05-13)或日期+AM/PM(2026-05-13_AM_210603)
        matching_sheets = [s for s in all_data.keys() if s.startswith(date)]
        if matching_sheets:
            # 按字母排序，AM/PM_开头的自然顺序
            # PM排在AM前面（字母顺序 P < A）
            matching_sheets.sort(reverse=True)
            target_sheet = matching_sheets[0]
        else:
            return {"success": False, "prices": [], "sheet": None}
    else:
        target_sheet = sorted(all_data.keys())[-1] if all_data else None

    if not target_sheet:
        return {"success": False, "prices": [], "sheet": None}

    prices = all_data[target_sheet].get('prices', [])
    if not prices:
        return {"success": False, "prices": [], "sheet": target_sheet}

    return {
        "success": True,
        "sheet": target_sheet,
        "prices": [
            {
                "date": target_sheet[:10],  # 返回纯日期部分
                "time": p.get('time', ''),
                "material_id": f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
                "material_name": p.get('material_name', ''),
                "spec": p.get('spec', ''),
                "material_type": p.get('material_type', ''),
                "brand": p.get('brand', ''),
                "price": p.get('price', 0),
                "price_max": p.get('price_max', 0),
                "unit": p.get('unit', '元/吨'),
                "price_change": p.get('price_change', ''),
                "remark": p.get('remark', ''),
                "steel_code": p.get('steel_code', ''),
                "region": p.get('region', '山东烟台')
            }
            for p in prices
        ]
    }


@router.get("/check")
async def check_fetch_status():
    """检查今日是否已抓取"""
    from pathlib import Path
    import os

    last_fetch_file = Path(os.path.join(os.path.dirname(__file__), '..', 'services', 'logs', 'yantai_last_fetch.json'))
    today = datetime.now().date().isoformat()

    if last_fetch_file.exists():
        import json
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_fetch_date = data.get('last_fetch', '')[:10]

            if last_fetch_date == today:
                return {
                    "fetched_today": True,
                    "last_fetch": data.get('last_fetch'),
                    "success": data.get('success'),
                    "prices_count": data.get('prices_count'),
                    "message": f"今日({today})已抓取，共{data.get('prices_count', 0)}条记录"
                }

    return {
        "fetched_today": False,
        "last_fetch": None,
        "message": "今日尚未抓取，可以执行抓取"
    }


@router.get("/by-brand/{brand}")
async def get_prices_by_brand(brand: str):
    """按品牌筛选价格"""
    from services.yantai_rebar_scraper import read_from_excel
    import os

    excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

    all_data = read_from_excel(excel_file)
    if not all_data:
        return []

    latest_sheet = sorted(all_data.keys())[-1] if all_data else None
    if not latest_sheet:
        return []

    prices = all_data[latest_sheet].get('prices', [])

    # 筛选指定品牌
    filtered = [p for p in prices if brand in p.get('brand', '')]

    return [
        MaterialPriceResponse(
            material_id=f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
            material_name=p.get('material_name', ''),
            spec=p.get('spec', ''),
            material_type=p.get('material_type', ''),
            brand=p.get('brand', ''),
            price=p.get('price', 0),
            unit=p.get('unit', '元/吨'),
            region=p.get('region', '山东烟台')
        )
        for p in filtered
    ]


@router.get("/by-type/{material_type}")
async def get_prices_by_type(material_type: str):
    """按品名筛选价格（高线、螺纹钢、盘螺、圆钢）"""
    from services.yantai_rebar_scraper import read_from_excel
    import os

    excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

    all_data = read_from_excel(excel_file)
    if not all_data:
        return []

    latest_sheet = sorted(all_data.keys())[-1] if all_data else None
    if not latest_sheet:
        return []

    prices = all_data[latest_sheet].get('prices', [])

    # 筛选指定品名
    filtered = [p for p in prices if material_type in p.get('material_name', '')]

    return [
        MaterialPriceResponse(
            material_id=f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
            material_name=p.get('material_name', ''),
            spec=p.get('spec', ''),
            material_type=p.get('material_type', ''),
            brand=p.get('brand', ''),
            price=p.get('price', 0),
            unit=p.get('unit', '元/吨'),
            region=p.get('region', '山东烟台')
        )
        for p in filtered
    ]


@router.post("/fetch-historical")
async def fetch_historical_prices_endpoint(days: int = 7):
    """
    抓取历史价格数据（最近N天）

    - days: 抓取最近几天的数据，默认7天
    """
    try:
        from services.fetch_yantai_api import fetch_historical_prices

        result = await fetch_historical_prices(days=days)

        return {
            "success": result['success'],
            "dates_fetched": result.get('dates_fetched', 0),
            "total_prices": result.get('total_prices', 0),
            "data": result.get('data', {}),
            "error": result.get('error', '')
        }

    except Exception as e:
        logger.error(f"抓取历史数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range")
async def get_prices_by_date_range(start_date: str = None, end_date: str = None):
    """
    获取指定日期区间的价格数据

    - start_date: 开始日期（如 2026-05-01）
    - end_date: 结束日期（如 2026-05-20）
    - 如果都为空，返回所有数据
    """
    from services.yantai_rebar_scraper import read_from_excel
    from datetime import datetime

    excel_file = "services/data/山东烟台钢筋价格.xlsx"
    all_data = read_from_excel(excel_file)

    if not all_data:
        return {
            "success": False,
            "prices": [],
            "dates": [],
            "total_count": 0,
            "message": "暂无数据"
        }

    # 收集所有sheet并按日期筛选
    result_prices = []
    matched_dates = []

    for sheet_name, sheet_data in all_data.items():
        date_str = sheet_name[:10]  # 取前10个字符 YYYY-MM-DD

        # 日期过滤
        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue

        prices = sheet_data.get('prices', [])
        if prices:
            matched_dates.append(date_str)
            for p in prices:
                result_prices.append({
                    "date": date_str,
                    "time": p.get('time', ''),
                    "material_id": f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
                    "material_name": p.get('material_name', ''),
                    "spec": p.get('spec', ''),
                    "material_type": p.get('material_type', ''),
                    "brand": p.get('brand', ''),
                    "price": p.get('price', 0),
                    "price_max": p.get('price_max', 0),
                    "unit": p.get('unit', '元/吨'),
                    "price_change": p.get('price_change', ''),
                    "remark": p.get('remark', ''),
                    "steel_code": p.get('steel_code', ''),
                    "region": p.get('region', '山东烟台')
                })

    # 按日期排序
    matched_dates = sorted(set(matched_dates))

    return {
        "success": True,
        "prices": result_prices,
        "dates": matched_dates,
        "total_count": len(result_prices),
        "date_range": {
            "start": matched_dates[0] if matched_dates else None,
            "end": matched_dates[-1] if matched_dates else None
        }
    }


@router.get("/trend")
async def get_price_trend(material_type: str = None, spec: str = None, brand: str = None, days: int = 365, start_date: str = None, end_date: str = None):
    """
    获取价格走势图数据

    - material_type: 筛选品名（高线、螺纹钢、盘螺、圆钢）
    - spec: 筛选规格（如 Φ8）
    - brand: 筛选品牌
    - days: 返回最近几天的数据，默认365天
    - start_date: 开始日期（如 2026-05-01），优先级高于days
    - end_date: 结束日期（如 2026-05-20）
    """
    from services.yantai_rebar_scraper import read_from_excel
    import os
    from datetime import datetime, timedelta

    excel_file = "services/data/山东烟台钢筋价格.xlsx"
    all_data = read_from_excel(excel_file)

    if not all_data:
        return {"success": False, "data": [], "message": "暂无数据"}

    # 收集所有sheet并按日期排序
    sheet_dates = []
    for sheet_name in all_data.keys():
        # 从sheet名提取日期
        date_str = sheet_name[:10]  # 取前10个字符 YYYY-MM-DD
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d')
            sheet_dates.append((sheet_name, d))
        except:
            continue

    # 按日期排序
    sheet_dates.sort(key=lambda x: x[1])

    # 如果指定了日期范围，使用日期范围过滤
    if start_date or end_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date else datetime.min
        end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.max
        sheet_dates = [(s, d) for s, d in sheet_dates if start_dt <= d <= end_dt]
    else:
        # 只保留最近 days 天的数据
        cutoff = datetime.now() - timedelta(days=days)
        sheet_dates = [(s, d) for s, d in sheet_dates if d >= cutoff]

    # 按日期聚合价格数据（同一个日期可能有多条：AM和PM）
    # 先按日期分组
    date_prices: dict = {}
    for sheet_name, sheet_date in sheet_dates:
        prices = all_data.get(sheet_name, {}).get('prices', [])
        if not prices:
            continue

        date_key = sheet_date.strftime('%Y-%m-%d')

        # 筛选
        filtered = prices
        if material_type:
            filtered = [p for p in filtered if material_type in (p.get('material_name') or '')]
        if spec:
            filtered = [p for p in filtered if spec in (p.get('spec') or '')]
        if brand:
            filtered = [p for p in filtered if brand in (p.get('brand') or '')]

        if not filtered:
            continue

        # 将价格添加到该日期的列表中
        if date_key not in date_prices:
            date_prices[date_key] = {
                'timestamp': int(sheet_date.timestamp() * 1000),
                'prices': [],
                'all_prices': []
            }
        date_prices[date_key]['prices'].extend(filtered)
        date_prices[date_key]['all_prices'].extend([p.get('price', 0) for p in filtered if p.get('price')])

    # 按日期生成趋势数据
    trend_data = []
    for date_str in sorted(date_prices.keys()):
        info = date_prices[date_str]
        all_price_values = [p for p in info['all_prices'] if p > 0]

        if not all_price_values:
            continue

        avg_price = sum(all_price_values) / len(all_price_values)
        min_price = min(all_price_values)
        max_price = max(all_price_values)

        # 按品名统计
        by_type = {}
        for p in info['prices']:
            t = p.get('material_name', '其他')
            if t not in by_type:
                by_type[t] = []
            if p.get('price'):
                by_type[t].append(p.get('price'))

        type_stats = {}
        for t, prices in by_type.items():
            if prices:
                type_stats[t] = {
                    'avg': round(sum(prices) / len(prices), 2),
                    'min': min(prices),
                    'max': max(prices),
                    'count': len(prices)
                }

        trend_data.append({
            'date': date_str,
            'timestamp': info['timestamp'],
            'avg_price': round(avg_price, 2),
            'min_price': min_price,
            'max_price': max_price,
            'count': len(info['prices']),
            'by_type': type_stats
        })

    return {
        "success": True,
        "data": trend_data,
        "total_days": len(trend_data),
        "filters": {
            "material_type": material_type,
            "spec": spec,
            "brand": brand,
            "days": days
        }
    }