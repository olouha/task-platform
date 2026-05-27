"""
造价管理 - 历史参考价 API
支持按年份、季度查询历史造价参考价数据
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from models.cost_history import (
    get_available_periods,
    get_concrete_prices,
    get_steel_prices,
    CONCRETE_HISTORY,
    STEEL_REBAR_HISTORY
)

router = APIRouter(tags=["造价历史参考价"])


class PeriodInfo(BaseModel):
    year: str
    quarter: str
    label: str
    concrete_count: int = 0
    rebar_count: int = 0


class ConcretePriceItem(BaseModel):
    grade: str
    yantai: Optional[float] = None  # 烟台含税价
    rushan: Optional[float] = None  # 蓬莱含税价


class SteelPriceItem(BaseModel):
    grade: str
    size: str
    price: Optional[float] = None
    spec: str


@router.get("/periods", response_model=List[PeriodInfo])
async def list_available_periods():
    """
    获取所有可用的历史时期列表
    """
    return get_available_periods()


@router.get("/years")
async def list_years():
    """
    获取所有有数据的年份
    """
    years = set(CONCRETE_HISTORY.keys()) | set(STEEL_REBAR_HISTORY.keys())
    return {"years": sorted(years)}


@router.get("/concrete/by-period")
async def get_concrete_by_period(
    year: str = Query(..., description="年份，如 2024"),
    quarter: str = Query(..., description="季度，如 2024年一季度")
):
    """
    按指定时期获取混凝土价格

    示例: /api/cost-history/concrete/by-period?year=2024&quarter=2024年一季度
    """
    prices = get_concrete_prices(year, quarter)
    if not prices:
        raise HTTPException(status_code=404, detail=f"未找到 {year} {quarter} 的混凝土数据")

    return {
        "year": year,
        "quarter": quarter,
        "source": "烟台工程建设标准造价管理",
        "category": "混凝土",
        "items": prices,
        "count": len(prices)
    }


@router.get("/steel/by-period")
async def get_steel_by_period(
    year: str = Query(..., description="年份，如 2024"),
    quarter: str = Query(..., description="季度，如 2024年一季度")
):
    """
    按指定时期获取钢筋价格

    示例: /api/cost-history/steel/by-period?year=2024&quarter=2024年一季度
    """
    prices = get_steel_prices(year, quarter)
    if not prices:
        raise HTTPException(status_code=404, detail=f"未找到 {year} {quarter} 的钢筋数据")

    return {
        "year": year,
        "quarter": quarter,
        "source": "烟台工程建设标准造价管理",
        "category": "钢筋",
        "items": prices,
        "count": len(prices)
    }


@router.get("/concrete/latest")
async def get_latest_concrete(
    year: Optional[str] = Query(None, description="指定年份"),
    limit: int = Query(10, description="返回最新N个季度")
):
    """
    获取最新的混凝土价格（默认最新10个季度）
    """
    # 收集所有数据并按时间排序
    all_data = []
    years = sorted(CONCRETE_HISTORY.keys(), reverse=True)

    for y in years:
        for q in sorted(CONCRETE_HISTORY[y].keys()):
            all_data.append({
                "year": y,
                "quarter": q,
                "label": f"{y}年{q}",
                "items": CONCRETE_HISTORY[y][q]
            })

    # 过滤年份
    if year:
        all_data = [d for d in all_data if d["year"] == year]

    # 返回最新的
    return {
        "items": all_data[:limit],
        "total": len(all_data)
    }


@router.get("/steel/latest")
async def get_latest_steel(
    year: Optional[str] = Query(None, description="指定年份"),
    limit: int = Query(10, description="返回最新N个季度")
):
    """
    获取最新的钢筋价格（默认最新10个季度）
    """
    all_data = []
    years = sorted(STEEL_REBAR_HISTORY.keys(), reverse=True)

    for y in years:
        for q in sorted(STEEL_REBAR_HISTORY[y].keys()):
            all_data.append({
                "year": y,
                "quarter": q,
                "label": f"{y}年{q}",
                "items": STEEL_REBAR_HISTORY[y][q]
            })

    if year:
        all_data = [d for d in all_data if d["year"] == year]

    return {
        "items": all_data[:limit],
        "total": len(all_data)
    }


@router.get("/concrete/grades")
async def get_concrete_grades():
    """
    获取混凝土强度等级列表
    """
    grades = ["C15", "C20", "C25", "C30", "C35", "C40", "C45", "C50", "C55", "C60"]
    return {"grades": grades}


@router.get("/steel/grades")
async def get_steel_grades():
    """
    获取钢筋等级列表
    """
    return {"grades": ["HPB", "HRB", "HRB400", "HRB400E", "HRB500"]}


@router.get("/steel/specs")
async def get_steel_specs():
    """
    获取钢筋规格列表
    """
    specs = set()
    for year_data in STEEL_REBAR_HISTORY.values():
        for quarter_data in year_data.values():
            for item in quarter_data:
                specs.add(item.get('size', ''))

    return {"specs": sorted([s for s in specs if s], key=lambda x: int(x) if x.isdigit() else 0)}


@router.get("/summary")
async def get_summary():
    """
    获取数据汇总信息
    """
    years = set(CONCRETE_HISTORY.keys()) | set(STEEL_REBAR_HISTORY.keys())

    concrete_periods = sum(len(q) for q in CONCRETE_HISTORY.values())
    steel_periods = sum(len(q) for q in STEEL_REBAR_HISTORY.values())

    return {
        "total_years": len(years),
        "years": sorted(years),
        "concrete_periods": concrete_periods,
        "steel_periods": steel_periods,
        "data_range": {
            "start": f"{min(years)}年" if years else None,
            "end": f"{max(years)}年" if years else None
        }
    }
