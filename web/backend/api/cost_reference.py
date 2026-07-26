"""
造价管理 - 参考价格查询 API
用于查询官方发布的钢筋、混凝土等造价参考价
"""

from fastapi import APIRouter, Query, Depends, Header
from typing import List, Optional
from pydantic import BaseModel
import re
import logging

from api.deps import get_current_account
from services.supabase_service import SupabaseService

router = APIRouter(tags=["造价参考价"])
logger = logging.getLogger(__name__)


def get_supabase():
    return SupabaseService()


class CostReferencePriceItem(BaseModel):
    """造价参考价条目（批量插入用）"""
    category: str
    code: Optional[str] = None
    name: str
    spec: Optional[str] = None
    unit: str = 't'
    unit_price: Optional[float] = None
    tax_rate: float = 13.0
    pump_price: Optional[float] = None
    non_pump_price: Optional[float] = None
    source: str = '烟台工程建设标准造价管理'
    period: str = '2024年第一季度'
    region: str = '山东烟台'
    notes: Optional[str] = None


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
    steel_type: Optional[str] = Query(None, description="按类型筛选，如 HRB400, HPB300, HRB400E"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """
    获取钢筋参考价格列表

    - 按规格筛选: ?spec=Φ12
    - 按类型筛选: ?steel_type=HRB400
    """
    logger.info(f"[get_steel_prices] 查询钢筋价格 | spec={spec}, steel_type={steel_type}")
    items = supabase.get_cost_reference_prices(category='钢筋', spec=spec, limit=1000)

    if steel_type:
        items = [item for item in items if steel_type in item.get('name', '')]

    logger.info(f"[get_steel_prices] 查询完成 | count={len(items)}")
    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="钢筋",
        items=items
    )


@router.get("/steel/types")
async def get_steel_types(supabase: SupabaseService = Depends(get_supabase)):
    """获取钢筋类型列表"""
    logger.info(f"[get_steel_types] 查询钢筋类型列表")
    items = supabase.get_cost_reference_prices(category='钢筋', limit=1000)
    types = set()
    for item in items:
        name = item.get('name', '')
        for t in ['HPB300', 'HRB400E', 'HRB500', 'HRB400', 'CRB600H']:
            if t in name:
                types.add(t)
    result = sorted(list(types))
    logger.info(f"[get_steel_types] 查询完成 | types={result}")
    return {"types": result}


@router.get("/steel/specs")
async def get_steel_specs(supabase: SupabaseService = Depends(get_supabase)):
    """获取钢筋规格列表"""
    logger.info(f"[get_steel_specs] 查询钢筋规格列表")
    items = supabase.get_cost_reference_prices(category='钢筋', limit=1000)
    specs = set()
    for item in items:
        name = item.get('name', '')
        match = re.search(r'Φ[\d<>~]+', name)
        if match:
            specs.add(match.group())
    result = sorted(list(specs))
    logger.info(f"[get_steel_specs] 查询完成 | specs={result}")
    return {"specs": result}


# ============================================================
# 混凝土价格 API
# ============================================================

@router.get("/concrete", response_model=CostReferenceResponse)
async def get_concrete_prices(
    min_grade: Optional[str] = Query(None, description="最小强度等级，如 C30"),
    max_grade: Optional[str] = Query(None, description="最大强度等级，如 C40"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """
    获取混凝土参考价格列表

    - 按强度等级范围筛选: ?min_grade=C30&max_grade=C40
    """
    logger.info(f"[get_concrete_prices] 查询混凝土价格 | min_grade={min_grade}, max_grade={max_grade}")
    items = supabase.get_cost_reference_prices(category='混凝土', limit=1000)

    if min_grade or max_grade:
        grades_order = ["C15", "C20", "C25", "C30", "C35", "C40", "C45", "C50", "C55", "C60"]
        def grade_index(grade):
            try:
                return grades_order.index(grade)
            except ValueError:
                return -1
        filtered = []
        for item in items:
            grade = item.get('grade', '')
            if min_grade and grade_index(grade) < grade_index(min_grade):
                continue
            if max_grade and grade_index(grade) > grade_index(max_grade):
                continue
            filtered.append(item)
        items = filtered

    logger.info(f"[get_concrete_prices] 查询完成 | count={len(items)}")
    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="混凝土",
        items=items
    )


@router.get("/concrete/grades")
async def get_concrete_grades(supabase: SupabaseService = Depends(get_supabase)):
    """获取混凝土强度等级列表"""
    logger.info(f"[get_concrete_grades] 查询混凝土强度等级列表")
    items = supabase.get_cost_reference_prices(category='混凝土', limit=1000)
    grades = [item.get('grade') for item in items if item.get('grade')]
    logger.info(f"[get_concrete_grades] 查询完成 | grades={grades}")
    return {"grades": grades}


# ============================================================
# 砂浆价格 API
# ============================================================

@router.get("/mortar", response_model=CostReferenceResponse)
async def get_mortar_prices(supabase: SupabaseService = Depends(get_supabase)):
    """获取砂浆参考价格列表"""
    logger.info(f"[get_mortar_prices] 查询砂浆价格")
    items = supabase.get_cost_reference_prices(category='砂浆', limit=1000)
    logger.info(f"[get_mortar_prices] 查询完成 | count={len(items)}")
    return CostReferenceResponse(
        source="烟台工程建设标准造价管理",
        period="2024年第一季度",
        category="砂浆",
        items=items
    )


# ============================================================
# 综合查询 API
# ============================================================

@router.get("/search")
async def search_cost_reference(
    keyword: str = Query(..., description="搜索关键词"),
    category: Optional[str] = Query(None, description="分类: 钢筋/混凝土/砂浆"),
    supabase: SupabaseService = Depends(get_supabase)
):
    """
    综合搜索造价参考价

    - 按关键词搜索: ?keyword=Φ12
    - 按分类筛选: ?category=钢筋
    """
    logger.info(f"[search_cost_reference] 搜索造价参考价 | keyword={keyword}, category={category}")
    results = []

    # 搜索钢筋
    if category is None or category == "钢筋":
        items = supabase.get_cost_reference_prices(category='钢筋', limit=1000)
        for item in items:
            if keyword.lower() in item.get('name', '').lower():
                results.append({'category': '钢筋', **item})

    # 搜索混凝土
    if category is None or category == "混凝土":
        items = supabase.get_cost_reference_prices(category='混凝土', limit=1000)
        for item in items:
            if keyword.lower() in str(item.get('grade', '')).lower():
                results.append({'category': '混凝土', **item})

    # 搜索砂浆
    if category is None or category == "砂浆":
        items = supabase.get_cost_reference_prices(category='砂浆', limit=1000)
        for item in items:
            if keyword.lower() in item.get('name', '').lower():
                results.append({'category': '砂浆', **item})

    logger.info(f"[search_cost_reference] 搜索完成 | count={len(results)}")
    return {
        "source": "烟台工程建设标准造价管理",
        "period": "2024年第一季度",
        "keyword": keyword,
        "category": category,
        "results": results,
        "count": len(results)
    }


@router.get("/categories")
async def get_cost_categories(supabase: SupabaseService = Depends(get_supabase)):
    """获取造价分类列表"""
    logger.info(f"[get_cost_categories] 查询造价分类列表")
    cats = supabase.get_cost_reference_categories()
    logger.info(f"[get_cost_categories] 查询完成 | count={len(cats)}")
    return {"categories": cats}


@router.get("/summary")
async def get_cost_summary(supabase: SupabaseService = Depends(get_supabase)):
    """获取造价参考价汇总"""
    logger.info(f"[get_cost_summary] 查询造价汇总")
    summary = supabase.get_cost_reference_summary()
    logger.info(f"[get_cost_summary] 查询完成 | summary_keys={list(summary.keys())}")
    return {
        "source": "烟台工程建设标准造价管理",
        "period": "2024年第一季度",
        "summary": summary
    }


@router.post("/prices")
async def insert_cost_reference_prices(
    items: List[CostReferencePriceItem],
    account: str = Depends(get_current_account),
    supabase: SupabaseService = Depends(get_supabase)
):
    """批量插入造价参考价"""
    logger.info(f"[insert_cost_reference_prices] 批量插入造价参考价 | count={len(items)} | by={account}")
    data = [item.model_dump() for item in items]
    result = supabase.insert_cost_reference_prices(data)
    logger.info(f"[insert_cost_reference_prices] 插入完成 | imported={result.get('imported')}, total={result.get('total')}")
    return result


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