"""
造价管理 - 参考价格查询 API
用于查询官方发布的钢筋、混凝土等造价参考价
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel

from models.cost_reference import (
    STEEL_REBAR_PRICES,
    CONCRETE_PRICES,
    MORTAR_PRICES
)

router = APIRouter(tags=["造价参考价"])


class SteelPriceItem(BaseModel):
    """钢筋价格项"""
    code: str
    name: str
    spec: str
    unit: str
    unit_price: float
    tax_rate: float = 13.0


class ConcretePriceItem(BaseModel):
    """混凝土价格项"""
    grade: str
    pump_price: float
    non_pump_price: float


class MortarPriceItem(BaseModel):
    """砂浆价格项"""
    name: str
    code: Optional[str]
    unit_price: float
    unit: str


class CostReferenceResponse(BaseModel):
    """造价参考价响应"""
    source: str
    period: str
    category: str
    items: List


# ============================================================
# 钢筋价格 API
# ============================================================

@router.get("/steel", response_model=CostReferenceResponse)
async def get_steel_prices(
    spec: Optional[str] = Query(None, description="按规格筛选，如 Φ12"),
    steel_type: Optional[str] = Query(None, description="按类型筛选，如 HRB400, HPB300, HRB400E")
):
    """
    获取钢筋参考价格列表

    - 按规格筛选: ?spec=Φ12
    - 按类型筛选: ?steel_type=HRB400
    """
    items = STEEL_REBAR_PRICES

    if spec:
        items = [item for item in items if spec in item["name"]]

    if steel_type:
        items = [item for item in items if steel_type in item["name"]]

    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="钢筋",
        items=items
    )


@router.get("/steel/types")
async def get_steel_types():
    """获取钢筋类型列表"""
    types = set()
    for item in STEEL_REBAR_PRICES:
        name = item["name"]
        if "HPB300" in name:
            types.add("HPB300")
        elif "HRB400E" in name:
            types.add("HRB400E")
        elif "HRB500" in name:
            types.add("HRB500")
        elif "HRB400" in name:
            types.add("HRB400")
        elif "CRB600H" in name:
            types.add("CRB600H")

    return {"types": sorted(list(types))}


@router.get("/steel/specs")
async def get_steel_specs():
    """获取钢筋规格列表"""
    specs = set()
    for item in STEEL_REBAR_PRICES:
        name = item["name"]
        # 提取规格
        import re
        match = re.search(r'Φ[\d<>~]+', name)
        if match:
            specs.add(match.group())

    return {"specs": sorted(list(specs))}


# ============================================================
# 混凝土价格 API
# ============================================================

@router.get("/concrete", response_model=CostReferenceResponse)
async def get_concrete_prices(
    min_grade: Optional[str] = Query(None, description="最小强度等级，如 C30"),
    max_grade: Optional[str] = Query(None, description="最大强度等级，如 C40")
):
    """
    获取混凝土参考价格列表

    - 按强度等级范围筛选: ?min_grade=C30&max_grade=C40
    """
    grades_order = ["C15", "C20", "C25", "C30", "C35", "C40", "C45", "C50", "C55", "C60"]

    items = CONCRETE_PRICES

    if min_grade or max_grade:
        filtered = []
        for item in items:
            grade = item["grade"]
            if min_grade and grades_order.index(grade) < grades_order.index(min_grade):
                continue
            if max_grade and grades_order.index(grade) > grades_order.index(max_grade):
                continue
            filtered.append(item)
        items = filtered

    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="混凝土",
        items=items
    )


@router.get("/concrete/grades")
async def get_concrete_grades():
    """获取混凝土强度等级列表"""
    return {
        "grades": [item["grade"] for item in CONCRETE_PRICES]
    }


# ============================================================
# 砂浆价格 API
# ============================================================

@router.get("/mortar", response_model=CostReferenceResponse)
async def get_mortar_prices():
    """获取砂浆参考价格列表"""
    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="砂浆",
        items=MORTAR_PRICES
    )


# ============================================================
# 综合查询 API
# ============================================================

@router.get("/search")
async def search_cost_reference(
    keyword: str = Query(..., description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类: 钢筋/混凝土/砂浆")
):
    """
    综合搜索造价参考价

    - 按关键词搜索: ?keyword=Φ12
    - 按分类筛选: ?category=钢筋
    """
    results = []

    # 搜索钢筋
    if category is None or category == "钢筋":
        for item in STEEL_REBAR_PRICES:
            if keyword.lower() in item["name"].lower() or keyword in item.get("spec", ""):
                results.append({
                    "category": "钢筋",
                    **item
                })

    # 搜索混凝土
    if category is None or category == "混凝土":
        for item in CONCRETE_PRICES:
            if keyword.lower() in item["grade"].lower():
                results.append({
                    "category": "混凝土",
                    **item
                })

    # 搜索砂浆
    if category is None or category == "砂浆":
        for item in MORTAR_PRICES:
            if keyword.lower() in item["name"].lower():
                results.append({
                    "category": "砂浆",
                    **item
                })

    return {
        "source": "烟台工程建设标准造价管理",
        "period": "2024年第一季度",
        "keyword": keyword,
        "category": category,
        "results": results,
        "count": len(results)
    }


@router.get("/categories")
async def get_cost_categories():
    """获取造价分类列表"""
    return {
        "categories": [
            {"id": "钢筋", "name": "钢筋价格", "count": len(STEEL_REBAR_PRICES)},
            {"id": "混凝土", "name": "混凝土价格", "count": len(CONCRETE_PRICES)},
            {"id": "砂浆", "name": "砂浆价格", "count": len(MORTAR_PRICES)},
        ]
    }


@router.get("/summary")
async def get_cost_summary():
    """获取造价参考价汇总"""
    return {
        "source": "烟台工程建设标准造价管理",
        "period": "2024年第一季度",
        "summary": {
            "钢筋": {
                "count": len(STEEL_REBAR_PRICES),
                "price_range": {
                    "min": min(item["unit_price"] for item in STEEL_REBAR_PRICES),
                    "max": max(item["unit_price"] for item in STEEL_REBAR_PRICES)
                },
                "unit": "元/吨"
            },
            "混凝土": {
                "count": len(CONCRETE_PRICES),
                "price_range": {
                    "min_pump": min(item["pump_price"] for item in CONCRETE_PRICES),
                    "max_pump": max(item["pump_price"] for item in CONCRETE_PRICES)
                },
                "unit": "元/立方米"
            },
            "砂浆": {
                "count": len(MORTAR_PRICES),
                "price_range": {
                    "min": min(item["unit_price"] for item in MORTAR_PRICES),
                    "max": max(item["unit_price"] for item in MORTAR_PRICES)
                },
                "unit": "元/吨"
            }
        }
    }


@router.get("/sources")
async def get_cost_sources():
    """获取所有可用的数据来源列表"""
    return {
        "sources": [
            {
                "id": "yantai_2024q1",
                "name": "烟台工程建设标准造价管理",
                "period": "2024年第一季度",
                "description": "烟台市建筑、安装工程材料价格表",
                "available": True
            },
            {
                "id": "yantai_2023q4",
                "name": "烟台工程建设标准造价管理",
                "period": "2023年第四季度",
                "description": "待录入",
                "available": False
            },
            {
                "id": "shandong_2024q1",
                "name": "山东省建筑工程造价信息",
                "period": "2024年第一季度",
                "description": "待录入",
                "available": False
            },
        ]
    }