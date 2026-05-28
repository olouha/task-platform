"""
价格历史 API
使用 Supabase 数据库支持分时段查阅
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from models.schemas import PriceRecord
from datetime import date, datetime, timedelta
from enum import Enum
import logging

from services.supabase_service import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


def get_supabase():
    return SupabaseService()


class TimeRange(str, Enum):
    """时间范围枚举"""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


def get_date_range(time_range: TimeRange, custom_start: str = None, custom_end: str = None) -> tuple:
    """获取日期范围"""
    today = date.today()

    if custom_start and custom_end:
        return custom_start, custom_end

    if time_range == TimeRange.TODAY:
        return today.isoformat(), today.isoformat()
    elif time_range == TimeRange.WEEK:
        start = today - timedelta(days=7)
        return start.isoformat(), today.isoformat()
    elif time_range == TimeRange.MONTH:
        start = today - timedelta(days=30)
        return start.isoformat(), today.isoformat()
    elif time_range == TimeRange.QUARTER:
        start = today - timedelta(days=90)
        return start.isoformat(), today.isoformat()
    elif time_range == TimeRange.YEAR:
        start = today - timedelta(days=365)
        return start.isoformat(), today.isoformat()

    return (today - timedelta(days=30)).isoformat(), today.isoformat()


@router.get("/", response_model=List[dict])
async def list_price_history(
    material_id: str = None,
    source_id: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(default=100, le=1000),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取价格历史"""
    logger.info(f"[list_price_history] 查询历史 | material_id={material_id}, limit={limit}")
    try:
        records = supabase.get_price_records(
            material_id=material_id,
            source_id=source_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        logger.info(f"[list_price_history] 返回 {len(records)} 条记录")
        return records
    except Exception as e:
        logger.error(f"[list_price_history] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=dict)
async def create_price_record(record: PriceRecord, supabase: SupabaseService = Depends(get_supabase)):
    """添加价格记录"""
    logger.info(f"[create_price_record] 添加记录 | material_id={record.material_id}, price={record.price}")
    try:
        record_data = record.dict(exclude={'id'})
        result = supabase.create_price_record(record_data)
        if result:
            logger.info(f"[create_price_record] 添加成功 | id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="添加失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_price_record] 添加失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="添加记录失败")


@router.get("/latest")
async def get_latest_prices(supabase: SupabaseService = Depends(get_supabase)):
    """获取最新价格（按材料分组）"""
    logger.info("[get_latest_prices] 查询最新价格")
    try:
        records = supabase.get_price_records(limit=1000)
        records.sort(key=lambda x: x.get('recorded_date', ''), reverse=True)

        latest = {}
        for r in records:
            mid = r.get('material_id')
            if mid and mid not in latest:
                latest[mid] = r

        result = list(latest.values())
        logger.info(f"[get_latest_prices] 返回 {len(result)} 个材料最新价格")
        return result
    except Exception as e:
        logger.error(f"[get_latest_prices] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.get("/stats")
async def get_price_stats(
    material_id: str = None,
    start_date: str = None,
    end_date: str = None,
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取价格统计"""
    logger.info(f"[get_price_stats] 统计价格 | material_id={material_id}, time_range={time_range}")
    try:
        if not start_date or not end_date:
            start_date, end_date = get_date_range(time_range)

        records = supabase.get_price_records(
            material_id=material_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

        if not records:
            logger.info("[get_price_stats] 无数据")
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'start_date': start_date,
                'end_date': end_date
            }

        prices = [r.get('price', 0) for r in records if r.get('price')]
        result = {
            'count': len(prices),
            'min': min(prices) if prices else 0,
            'max': max(prices) if prices else 0,
            'avg': sum(prices) / len(prices) if prices else 0,
            'start_date': start_date,
            'end_date': end_date
        }
        logger.info(f"[get_price_stats] 统计完成 | count={result['count']}, avg={result['avg']:.2f}")
        return result
    except Exception as e:
        logger.error(f"[get_price_stats] 统计失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="统计失败")


@router.get("/trend")
async def get_price_trend(
    material_id: str = None,
    days: int = Query(default=30, le=365),
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    custom_start: str = Query(default=None),
    custom_end: str = Query(default=None),
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取价格趋势"""
    logger.info(f"[get_price_trend] 获取趋势 | material_id={material_id}, days={days}")
    try:
        start_date, end_date = get_date_range(time_range, custom_start, custom_end)

        records = supabase.get_price_records(
            material_id=material_id,
            start_date=start_date,
            end_date=end_date,
            limit=1000
        )

        records.sort(key=lambda x: x.get('recorded_date', ''))

        daily_prices = {}
        for r in records:
            d = r.get('recorded_date')
            if d:
                if d not in daily_prices:
                    daily_prices[d] = []
                daily_prices[d].append(r.get('price', 0))

        trend_data = [
            {
                'date': d,
                'price': sum(prices) / len(prices),
                'count': len(prices)
            }
            for d, prices in sorted(daily_prices.items())
        ]

        logger.info(f"[get_price_trend] 返回 {len(trend_data)} 天数据")
        return {
            'material_id': material_id,
            'start_date': start_date,
            'end_date': end_date,
            'days': len(trend_data),
            'data': trend_data
        }
    except Exception as e:
        logger.error(f"[get_price_trend] 获取失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取趋势失败")


@router.get("/compare")
async def compare_prices(
    material_id: str = None,
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    supabase: SupabaseService = Depends(get_supabase)
):
    """对比不同时期的价格"""
    logger.info(f"[compare_prices] 对比价格 | material_id={material_id}, time_range={time_range}")
    try:
        today = date.today()

        if time_range == TimeRange.MONTH:
            last_period_start = today - timedelta(days=60)
            last_period_end = today - timedelta(days=30)
        elif time_range == TimeRange.QUARTER:
            last_period_start = today - timedelta(days=180)
            last_period_end = today - timedelta(days=90)
        else:
            last_period_start = today - timedelta(days=60)
            last_period_end = today - timedelta(days=30)

        current_start, current_end = get_date_range(time_range)

        current_records = supabase.get_price_records(
            material_id=material_id,
            start_date=current_start,
            end_date=current_end,
            limit=1000
        )

        last_records = supabase.get_price_records(
            material_id=material_id,
            start_date=last_period_start.isoformat(),
            end_date=last_period_end.isoformat(),
            limit=1000
        )

        current_prices = [r.get('price', 0) for r in current_records if r.get('price')]
        last_prices = [r.get('price', 0) for r in last_records if r.get('price')]

        current_avg = sum(current_prices) / len(current_prices) if current_prices else 0
        last_avg = sum(last_prices) / len(last_prices) if last_prices else 0

        change = ((current_avg - last_avg) / last_avg * 100) if last_avg > 0 else 0

        result = {
            'current_period': {
                'start': current_start,
                'end': current_end,
                'avg_price': round(current_avg, 2),
                'count': len(current_records)
            },
            'last_period': {
                'start': last_period_start.isoformat(),
                'end': last_period_end.isoformat(),
                'avg_price': round(last_avg, 2),
                'count': len(last_records)
            },
            'change_rate': round(change, 2)
        }
        logger.info(f"[compare_prices] 对比完成 | change_rate={result['change_rate']}%")
        return result
    except Exception as e:
        logger.error(f"[compare_prices] 对比失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="对比失败")