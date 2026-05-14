"""
指标管理 API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from models.schemas import IndicatorCategory, Indicator

router = APIRouter()

# 模拟数据
_indicator_categories_db = {}
_indicators_db = {}


@router.get("/categories", response_model=List[IndicatorCategory])
async def list_indicator_categories(project_id: str = None):
    """获取指标分类"""
    categories = list(_indicator_categories_db.values())
    if project_id:
        categories = [c for c in categories if c.project_id == project_id]
    return sorted(categories, key=lambda x: x.sort_order)


@router.post("/categories", response_model=IndicatorCategory)
async def create_indicator_category(category: IndicatorCategory):
    """创建指标分类"""
    import uuid
    category.id = str(uuid.uuid4())
    _indicator_categories_db[category.id] = category
    return category


@router.put("/categories/{category_id}", response_model=IndicatorCategory)
async def update_indicator_category(category_id: str, category: IndicatorCategory):
    """更新指标分类"""
    if category_id not in _indicator_categories_db:
        raise HTTPException(status_code=404, detail="分类不存在")
    category.id = category_id
    _indicator_categories_db[category_id] = category
    return category


@router.delete("/categories/{category_id}")
async def delete_indicator_category(category_id: str):
    """删除指标分类"""
    if category_id in _indicator_categories_db:
        del _indicator_categories_db[category_id]
    # 同时删除该分类下的指标
    to_delete = [i for i in _indicators_db if _indicators_db[i].category_id == category_id]
    for i in to_delete:
        del _indicators_db[i]
    return {"success": True}


# ========== 指标 ==========

@router.get("/", response_model=List[Indicator])
async def list_indicators(
    project_id: str = None,
    category_id: str = None
):
    """获取指标列表"""
    indicators = list(_indicators_db.values())

    if project_id:
        indicators = [i for i in indicators if i.project_id == project_id]
    if category_id:
        indicators = [i for i in indicators if i.category_id == category_id]

    return indicators


@router.post("/", response_model=Indicator)
async def create_indicator(indicator: Indicator):
    """创建指标"""
    import uuid
    indicator.id = str(uuid.uuid4())
    _indicators_db[indicator.id] = indicator
    return indicator


@router.get("/{indicator_id}", response_model=Indicator)
async def get_indicator(indicator_id: str):
    """获取指标详情"""
    if indicator_id not in _indicators_db:
        raise HTTPException(status_code=404, detail="指标不存在")
    return _indicators_db[indicator_id]


@router.put("/{indicator_id}", response_model=Indicator)
async def update_indicator(indicator_id: str, indicator: Indicator):
    """更新指标"""
    if indicator_id not in _indicators_db:
        raise HTTPException(status_code=404, detail="指标不存在")
    indicator.id = indicator_id
    _indicators_db[indicator_id] = indicator
    return indicator


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: str):
    """删除指标"""
    if indicator_id in _indicators_db:
        del _indicators_db[indicator_id]
    return {"success": True}


@router.put("/{indicator_id}/value")
async def update_indicator_value(indicator_id: str, current_value: float):
    """更新指标当前值"""
    if indicator_id not in _indicators_db:
        raise HTTPException(status_code=404, detail="指标不存在")

    _indicators_db[indicator_id].current_value = current_value

    # 自动计算状态
    indicator = _indicators_db[indicator_id]
    target_value = indicator.target_value
    warning_threshold = indicator.warning_threshold or 5

    if target_value:
        if current_value > target_value * (1 + warning_threshold / 100):
            indicator.status = 'danger'
        elif current_value > target_value:
            indicator.status = 'warning'
        else:
            indicator.status = 'normal'

    return indicator


@router.post("/evaluate")
async def evaluate_indicators(
    project_id: str = None,
    current_values: dict = None
):
    """评估指标状态"""
    from services.adjustment_calculator import IndicatorService

    indicators = list(_indicators_db.values())
    if project_id:
        indicators = [i for i in indicators if i.project_id == project_id]

    service = IndicatorService()
    results = service.evaluate_indicators(indicators, current_values or {})

    # 统计
    stats = {
        'total': len(results),
        'normal': sum(1 for r in results if r.get('status') == 'normal'),
        'warning': sum(1 for r in results if r.get('status') == 'warning'),
        'danger': sum(1 for r in results if r.get('status') == 'danger'),
        'unknown': sum(1 for r in results if r.get('status') == 'unknown')
    }

    return {
        'indicators': results,
        'stats': stats
    }