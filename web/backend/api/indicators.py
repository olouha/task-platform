"""
指标管理 API
使用 Supabase 数据库实现数据持久化
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from models.schemas import IndicatorCategory, Indicator
from services.supabase_service import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


def get_supabase():
    return SupabaseService()


@router.get("/categories", response_model=List[dict])
async def list_indicator_categories(project_id: str = None, supabase: SupabaseService = Depends(get_supabase)):
    """获取指标分类"""
    logger.info(f"[list_indicator_categories] 查询分类 | project_id={project_id}")
    try:
        result = supabase.get_indicator_categories(project_id)
        logger.info(f"[list_indicator_categories] 返回 {len(result)} 个分类")
        return result
    except Exception as e:
        logger.error(f"[list_indicator_categories] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/categories", response_model=dict)
async def create_indicator_category(category: IndicatorCategory, supabase: SupabaseService = Depends(get_supabase)):
    """创建指标分类"""
    logger.info(f"[create_indicator_category] 创建分类 | name={category.name}")
    try:
        category_data = category.dict(exclude={'id'})
        result = supabase.create_indicator_category(category_data)
        if result:
            logger.info(f"[create_indicator_category] 创建成功 | category_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_indicator_category] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建分类失败")


@router.put("/categories/{category_id}", response_model=dict)
async def update_indicator_category(category_id: str, category: IndicatorCategory, supabase: SupabaseService = Depends(get_supabase)):
    """更新指标分类"""
    logger.info(f"[update_indicator_category] 更新分类 | category_id={category_id}")
    try:
        category_data = category.dict(exclude={'id'})
        success = supabase.update_indicator_category(category_id, category_data)
        if success:
            logger.info(f"[update_indicator_category] 更新成功 | category_id={category_id}")
            return {**category_data, 'id': category_id}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_indicator_category] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新分类失败")


@router.delete("/categories/{category_id}")
async def delete_indicator_category(category_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """删除指标分类"""
    logger.info(f"[delete_indicator_category] 删除分类 | category_id={category_id}")
    try:
        success = supabase.delete_indicator_category(category_id)
        if success:
            logger.info(f"[delete_indicator_category] 删除成功 | category_id={category_id}")
        else:
            logger.warning(f"[delete_indicator_category] 分类不存在 | category_id={category_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_indicator_category] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


@router.get("/", response_model=List[dict])
async def list_indicators(project_id: str = None, category_id: str = None, supabase: SupabaseService = Depends(get_supabase)):
    """获取指标列表"""
    logger.info(f"[list_indicators] 查询指标 | project_id={project_id}, category_id={category_id}")
    try:
        result = supabase.get_indicators(project_id, category_id)
        logger.info(f"[list_indicators] 返回 {len(result)} 个指标")
        return result
    except Exception as e:
        logger.error(f"[list_indicators] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=dict)
async def create_indicator(indicator: Indicator, supabase: SupabaseService = Depends(get_supabase)):
    """创建指标"""
    logger.info(f"[create_indicator] 创建指标 | name={indicator.name}")
    try:
        indicator_data = indicator.dict(exclude={'id'})
        result = supabase.create_indicator(indicator_data)
        if result:
            logger.info(f"[create_indicator] 创建成功 | indicator_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_indicator] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建指标失败")


@router.get("/{indicator_id}", response_model=dict)
async def get_indicator(indicator_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取指标详情"""
    logger.info(f"[get_indicator] 查询指标 | indicator_id={indicator_id}")
    try:
        result = supabase.get_indicator(indicator_id)
        if not result:
            logger.warning(f"[get_indicator] 指标不存在 | indicator_id={indicator_id}")
            raise HTTPException(status_code=404, detail="指标不存在")
        logger.info(f"[get_indicator] 查询成功 | indicator_id={indicator_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_indicator] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.put("/{indicator_id}", response_model=dict)
async def update_indicator(indicator_id: str, indicator: Indicator, supabase: SupabaseService = Depends(get_supabase)):
    """更新指标"""
    logger.info(f"[update_indicator] 更新指标 | indicator_id={indicator_id}")
    try:
        indicator_data = indicator.dict(exclude={'id'})
        success = supabase.update_indicator(indicator_id, indicator_data)
        if success:
            result = supabase.get_indicator(indicator_id)
            logger.info(f"[update_indicator] 更新成功 | indicator_id={indicator_id}")
            return result
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_indicator] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新指标失败")


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """删除指标"""
    logger.info(f"[delete_indicator] 删除指标 | indicator_id={indicator_id}")
    try:
        success = supabase.delete_indicator(indicator_id)
        if success:
            logger.info(f"[delete_indicator] 删除成功 | indicator_id={indicator_id}")
        else:
            logger.warning(f"[delete_indicator] 指标不存在 | indicator_id={indicator_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_indicator] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


@router.put("/{indicator_id}/value")
async def update_indicator_value(indicator_id: str, current_value: float, supabase: SupabaseService = Depends(get_supabase)):
    """更新指标当前值"""
    logger.info(f"[update_indicator_value] 更新值 | indicator_id={indicator_id}, current_value={current_value}")
    try:
        indicator = supabase.get_indicator(indicator_id)
        if not indicator:
            logger.warning(f"[update_indicator_value] 指标不存在 | indicator_id={indicator_id}")
            raise HTTPException(status_code=404, detail="指标不存在")

        target_value = indicator.get('target_value')
        warning_threshold = indicator.get('warning_threshold') or 5

        status = 'normal'
        if target_value:
            if current_value > target_value * (1 + warning_threshold / 100):
                status = 'danger'
            elif current_value > target_value:
                status = 'warning'

        update_data = {'current_value': current_value, 'status': status}
        success = supabase.update_indicator(indicator_id, update_data)
        if success:
            logger.info(f"[update_indicator_value] 更新成功 | indicator_id={indicator_id}, status={status}")
            return {**update_data, 'id': indicator_id}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_indicator_value] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新失败")


@router.post("/evaluate")
async def evaluate_indicators(project_id: str = None, current_values: dict = None, supabase: SupabaseService = Depends(get_supabase)):
    """评估指标状态"""
    logger.info(f"[evaluate_indicators] 评估指标 | project_id={project_id}")
    try:
        from services.adjustment_calculator import IndicatorService

        indicators = supabase.get_indicators(project_id=project_id)

        service = IndicatorService()
        results = service.evaluate_indicators(indicators, current_values or {})

        stats = {
            'total': len(results),
            'normal': sum(1 for r in results if r.get('status') == 'normal'),
            'warning': sum(1 for r in results if r.get('status') == 'warning'),
            'danger': sum(1 for r in results if r.get('status') == 'danger'),
            'unknown': sum(1 for r in results if r.get('status') == 'unknown')
        }

        logger.info(f"[evaluate_indicators] 评估完成 | total={stats['total']}")
        return {'indicators': results, 'stats': stats}
    except Exception as e:
        logger.error(f"[evaluate_indicators] 评估失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="评估失败")