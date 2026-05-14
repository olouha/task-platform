"""
价格历史 API
支持分时段查阅
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from models.schemas import PriceRecord
from datetime import date, datetime, timedelta
from enum import Enum

router = APIRouter()

# 模拟数据
_price_history_db = {}


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


@router.get("/", response_model=List[PriceRecord])
async def list_price_history(
    material_id: str = None,
    source_id: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(default=100, le=1000)
):
    """获取价格历史"""
    records = list(_price_history_db.values())

    if material_id:
        records = [r for r in records if r.material_id == material_id]
    if source_id:
        records = [r for r in records if r.source_id == source_id]
    if start_date:
        records = [r for r in records if r.recorded_date >= start_date]
    if end_date:
        records = [r for r in records if r.recorded_date <= end_date]

    records.sort(key=lambda x: x.recorded_date, reverse=True)
    return records[:limit]


@router.post("/", response_model=PriceRecord)
async def create_price_record(record: PriceRecord):
    """添加价格记录"""
    import uuid
    record.id = str(uuid.uuid4())
    _price_history_db[record.id] = record
    return record


@router.get("/latest")
async def get_latest_prices():
    """获取最新价格（按材料分组）"""
    records = list(_price_history_db.values())
    records.sort(key=lambda x: x.recorded_date, reverse=True)

    latest = {}
    for r in records:
        mid = r.material_id
        if mid and mid not in latest:
            latest[mid] = r

    return list(latest.values())


@router.get("/stats")
async def get_price_stats(
    material_id: str = None,
    start_date: str = None,
    end_date: str = None,
    time_range: TimeRange = Query(default=TimeRange.MONTH)
):
    """获取价格统计"""
    # 如果没有指定日期范围，使用时间范围
    if not start_date or not end_date:
        start_date, end_date = get_date_range(time_range)

    records = list(_price_history_db.values())

    if material_id:
        records = [r for r in records if r.material_id == material_id]
    if start_date:
        records = [r for r in records if r.recorded_date >= start_date]
    if end_date:
        records = [r for r in records if r.recorded_date <= end_date]

    if not records:
        return {
            'count': 0,
            'min': 0,
            'max': 0,
            'avg': 0,
            'start_date': start_date,
            'end_date': end_date
        }

    prices = [r.price for r in records]

    return {
        'count': len(prices),
        'min': min(prices),
        'max': max(prices),
        'avg': sum(prices) / len(prices),
        'start_date': start_date,
        'end_date': end_date
    }


@router.get("/trend")
async def get_price_trend(
    material_id: str = None,
    days: int = Query(default=30, le=365),
    time_range: TimeRange = Query(default=TimeRange.MONTH),
    custom_start: str = Query(default=None),
    custom_end: str = Query(default=None)
):
    """获取价格趋势"""
    # 获取日期范围
    start_date, end_date = get_date_range(time_range, custom_start, custom_end)

    # 获取该范围内的所有记录
    records = list(_price_history_db.values())

    if material_id:
        records = [r for r in records if r.material_id == material_id]

    filtered = [
        r for r in records
        if start_date <= r.recorded_date <= end_date
    ]
    filtered.sort(key=lambda x: x.recorded_date)

    # 按日期聚合，计算每日平均值
    daily_prices = {}
    for r in filtered:
        d = r.recorded_date
        if d not in daily_prices:
            daily_prices[d] = []
        daily_prices[d].append(r.price)

    trend_data = [
        {
            'date': d,
            'price': sum(prices) / len(prices),
            'count': len(prices)
        }
        for d, prices in sorted(daily_prices.items())
    ]

    return {
        'material_id': material_id,
        'start_date': start_date,
        'end_date': end_date,
        'days': len(trend_data),
        'data': trend_data
    }


@router.get("/compare")
async def compare_prices(
    material_id: str = None,
    time_range: TimeRange = Query(default=TimeRange.MONTH)
):
    """对比不同时期的价格"""
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

    records = list(_price_history_db.values())
    if material_id:
        records = [r for r in records if r.material_id == material_id]

    # 当前周期
    current_records = [r for r in records if current_start <= r.recorded_date <= current_end]
    # 上一个周期
    last_records = [r for r in records if last_period_start <= r.recorded_date <= last_period_end]

    current_avg = sum(r.price for r in current_records) / len(current_records) if current_records else 0
    last_avg = sum(r.price for r in last_records) / len(last_records) if last_records else 0

    change = ((current_avg - last_avg) / last_avg * 100) if last_avg > 0 else 0

    return {
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