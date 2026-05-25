"""
烟台钢筋价格历史数据 API - 基于SQLite数据库
提供稳定的价格历史查询接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class PriceRecord(BaseModel):
    """价格记录"""
    date: str
    material_name: str
    spec: str
    brand: str
    am_price: Optional[float] = None
    pm_price: Optional[float] = None
    price_change: Optional[float] = None
    region: str = "山东烟台"


class PriceTrend(BaseModel):
    """价格趋势数据"""
    date: str
    timestamp: int
    material_name: str
    spec: str
    brand: str
    am_price: Optional[float] = None
    pm_price: Optional[float] = None
    avg_price: Optional[float] = None


class Statistics(BaseModel):
    """统计信息"""
    total_records: int
    total_dates: int
    date_range: Optional[str]
    total_materials: int


@router.get("/statistics", response_model=Statistics)
async def get_statistics():
    """获取数据库统计信息"""
    try:
        from services.sqlite_service import get_statistics
        stats = get_statistics()
        return Statistics(**stats)
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all", response_model=List[PriceRecord])
async def get_all_prices(limit: int = None):
    """
    获取所有价格数据

    - limit: 限制返回条数，默认返回全部
    """
    try:
        from services.sqlite_service import get_all_prices
        prices = get_all_prices(limit=limit)
        return prices
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date/{date}", response_model=List[PriceRecord])
async def get_prices_by_date(date: str):
    """
    获取指定日期的价格

    - date: 日期，格式 YYYY-MM-DD
    """
    try:
        from services.sqlite_service import get_prices_by_date
        prices = get_prices_by_date(date)
        return prices
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range", response_model=List[PriceRecord])
async def get_prices_by_range(start_date: str, end_date: str):
    """
    获取日期范围内的价格

    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    """
    try:
        from services.sqlite_service import get_prices_by_date_range
        prices = get_prices_by_date_range(start_date, end_date)
        return prices
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=Optional[PriceRecord])
async def get_latest_price():
    """获取最新一条价格记录"""
    try:
        from services.sqlite_service import get_latest_price
        price = get_latest_price()
        return price
    except Exception as e:
        logger.error(f"获取最新价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend", response_model=List[PriceTrend])
async def get_price_trend(
    material: str = None,
    spec: str = None,
    brand: str = None,
    days: int = 365
):
    """
    获取价格趋势

    - material: 品名筛选（高线、螺纹钢、盘螺、圆钢）
    - spec: 规格筛选（如 Φ8）
    - brand: 品牌筛选
    - days: 最近天数，默认365
    """
    try:
        from services.sqlite_service import get_all_prices
        from datetime import timedelta

        all_prices = get_all_prices()
        if not all_prices:
            return []

        # 过滤
        filtered = all_prices
        if material:
            filtered = [p for p in filtered if material in (p.get('material_name') or '')]
        if spec:
            filtered = [p for p in filtered if spec in (p.get('spec') or '')]
        if brand:
            filtered = [p for p in filtered if brand in (p.get('brand') or '')]

        # 按日期排序
        filtered.sort(key=lambda x: x.get('date', ''), reverse=True)

        # 限制天数
        if days:
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            filtered = [p for p in filtered if p.get('date', '') >= cutoff]

        # 转换为趋势格式
        result = []
        for p in filtered:
            am = p.get('am_price')
            pm = p.get('pm_price')
            prices = [x for x in [am, pm] if x]
            avg = sum(prices) / len(prices) if prices else None

            try:
                ts = int(datetime.strptime(p['date'], '%Y-%m-%d').timestamp() * 1000)
            except:
                ts = 0

            result.append(PriceTrend(
                date=p.get('date', ''),
                timestamp=ts,
                material_name=p.get('material_name', ''),
                spec=p.get('spec', ''),
                brand=p.get('brand', ''),
                am_price=am,
                pm_price=pm,
                avg_price=avg
            ))

        return result

    except Exception as e:
        logger.error(f"获取趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/materials")
async def get_available_materials():
    """获取所有可用的材料品名"""
    try:
        from services.sqlite_service import get_all_prices

        materials = set()
        for p in get_all_prices():
            if p.get('material_name'):
                materials.add(p['material_name'])

        return {"materials": sorted(list(materials))}

    except Exception as e:
        logger.error(f"获取材料列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brands")
async def get_available_brands():
    """获取所有可用的品牌"""
    try:
        from services.sqlite_service import get_all_prices

        brands = set()
        for p in get_all_prices():
            if p.get('brand'):
                brands.add(p['brand'])

        return {"brands": sorted(list(brands))}

    except Exception as e:
        logger.error(f"获取品牌列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs")
async def get_available_specs():
    """获取所有可用的规格"""
    try:
        from services.sqlite_service import get_all_prices

        specs = set()
        for p in get_all_prices():
            if p.get('spec'):
                specs.add(p['spec'])

        return {"specs": sorted(list(specs))}

    except Exception as e:
        logger.error(f"获取规格列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison")
async def compare_prices(start_date: str, end_date: str, material: str = None):
    """
    对比两个日期区间的价格变化

    - start_date: 开始日期
    - end_date: 结束日期
    - material: 品名筛选
    """
    try:
        from services.sqlite_service import get_prices_by_date

        start_prices = get_prices_by_date(start_date)
        end_prices = get_prices_by_date(end_date)

        if material:
            start_prices = [p for p in start_prices if material in (p.get('material_name') or '')]
            end_prices = [p for p in end_prices if material in (p.get('material_name') or '')]

        # 构建索引
        start_idx = {(p.get('material_name'), p.get('spec'), p.get('brand')): p for p in start_prices}
        end_idx = {(p.get('material_name'), p.get('spec'), p.get('brand')): p for p in end_prices}

        # 对比
        comparison = []
        for key, end_p in end_idx.items():
            start_p = start_idx.get(key)
            if start_p:
                start_price = start_p.get('pm_price') or start_p.get('am_price')
                end_price = end_p.get('pm_price') or end_p.get('am_price')

                if start_price and end_price:
                    change = end_price - start_price
                    change_pct = (change / start_price) * 100

                    comparison.append({
                        'material_name': key[0],
                        'spec': key[1],
                        'brand': key[2],
                        'start_date': start_date,
                        'end_date': end_date,
                        'start_price': start_price,
                        'end_price': end_price,
                        'change': round(change, 2),
                        'change_pct': round(change_pct, 2)
                    })

        return {
            'start_date': start_date,
            'end_date': end_date,
            'items_count': len(comparison),
            'comparison': comparison
        }

    except Exception as e:
        logger.error(f"价格对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add")
async def add_price_record(record: PriceRecord):
    """添加价格记录"""
    try:
        from services.sqlite_service import add_price_record

        success = add_price_record(
            date=record.date,
            material=record.material_name,
            spec=record.spec,
            brand=record.brand,
            am_price=record.am_price,
            pm_price=record.pm_price
        )

        if success:
            return {"success": True, "message": "添加成功"}
        else:
            return {"success": False, "message": "添加失败"}

    except Exception as e:
        logger.error(f"添加记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))