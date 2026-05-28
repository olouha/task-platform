"""
材料管理 API
使用 Supabase 数据库实现数据持久化
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from models.schemas import MaterialCategory, Material
from services.supabase_service import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


def get_supabase():
    return SupabaseService()


@router.get("/categories", response_model=List[dict])
async def list_categories(supabase: SupabaseService = Depends(get_supabase)):
    """获取所有材料分类"""
    logger.info("[list_categories] 从数据库查询所有分类")
    try:
        result = supabase.get_material_categories()
        logger.info(f"[list_categories] 返回 {len(result)} 个分类")
        return result
    except Exception as e:
        logger.error(f"[list_categories] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/categories", response_model=dict)
async def create_category(category: MaterialCategory, supabase: SupabaseService = Depends(get_supabase)):
    """创建材料分类"""
    logger.info(f"[create_category] 创建分类 | name={category.name}")
    try:
        category_data = category.dict(exclude={'id'})
        result = supabase.create_material_category(category_data)
        if result:
            logger.info(f"[create_category] 创建成功 | category_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_category] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建分类失败")


@router.get("/categories/{category_id}", response_model=dict)
async def get_category(category_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取分类详情"""
    logger.info(f"[get_category] 查询分类 | category_id={category_id}")
    categories = supabase.get_material_categories()
    category = next((c for c in categories if c.get('id') == category_id), None)
    if not category:
        logger.warning(f"[get_category] 分类不存在 | category_id={category_id}")
        raise HTTPException(status_code=404, detail="分类不存在")
    logger.info(f"[get_category] 查询成功 | category_id={category_id}")
    return category


@router.put("/categories/{category_id}", response_model=dict)
async def update_category(category_id: str, category: MaterialCategory, supabase: SupabaseService = Depends(get_supabase)):
    """更新分类"""
    logger.info(f"[update_category] 更新分类 | category_id={category_id}")
    try:
        category_data = category.dict(exclude={'id'})
        success = supabase.update_material_category(category_id, category_data)
        if success:
            logger.info(f"[update_category] 更新成功 | category_id={category_id}")
            return {**category_data, 'id': category_id}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_category] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新分类失败")


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """删除分类"""
    logger.info(f"[delete_category] 删除分类 | category_id={category_id}")
    try:
        success = supabase.delete_material_category(category_id)
        if success:
            logger.info(f"[delete_category] 删除成功 | category_id={category_id}")
        else:
            logger.warning(f"[delete_category] 分类不存在 | category_id={category_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_category] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


@router.get("/", response_model=List[dict])
async def list_materials(category_id: str = None, supabase: SupabaseService = Depends(get_supabase)):
    """获取所有材料"""
    logger.info(f"[list_materials] 查询材料 | category_id={category_id}")
    try:
        materials = supabase.get_all_materials()
        if category_id:
            materials = [m for m in materials if m.get('category_id') == category_id]
        logger.info(f"[list_materials] 返回 {len(materials)} 个材料")
        return materials
    except Exception as e:
        logger.error(f"[list_materials] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=dict)
async def create_material(material: Material, supabase: SupabaseService = Depends(get_supabase)):
    """创建材料"""
    logger.info(f"[create_material] 创建材料 | name={material.name}")
    try:
        material_data = material.dict(exclude={'id'})
        result = supabase.create_material(material_data)
        if result:
            logger.info(f"[create_material] 创建成功 | material_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_material] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建材料失败")


@router.get("/{material_id}", response_model=dict)
async def get_material(material_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取材料详情"""
    logger.info(f"[get_material] 查询材料 | material_id={material_id}")
    try:
        result = supabase.get_material(material_id)
        if not result:
            logger.warning(f"[get_material] 材料不存在 | material_id={material_id}")
            raise HTTPException(status_code=404, detail="材料不存在")
        logger.info(f"[get_material] 查询成功 | material_id={material_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_material] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.put("/{material_id}", response_model=dict)
async def update_material(material_id: str, material: Material, supabase: SupabaseService = Depends(get_supabase)):
    """更新材料"""
    logger.info(f"[update_material] 更新材料 | material_id={material_id}")
    try:
        material_data = material.dict(exclude={'id'})
        success = supabase.update_material(material_id, material_data)
        if success:
            result = supabase.get_material(material_id)
            logger.info(f"[update_material] 更新成功 | material_id={material_id}")
            return result
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_material] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新材料失败")


@router.delete("/{material_id}")
async def delete_material(material_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """删除材料"""
    logger.info(f"[delete_material] 删除材料 | material_id={material_id}")
    try:
        success = supabase.delete_material(material_id)
        if success:
            logger.info(f"[delete_material] 删除成功 | material_id={material_id}")
        else:
            logger.warning(f"[delete_material] 材料不存在 | material_id={material_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_material] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


@router.put("/{material_id}/price")
async def update_material_price(material_id: str, base_price: float, supabase: SupabaseService = Depends(get_supabase)):
    """更新材料基准价"""
    logger.info(f"[update_material_price] 更新价格 | material_id={material_id}, base_price={base_price}")
    try:
        success = supabase.update_material_price(material_id, base_price)
        if success:
            logger.info(f"[update_material_price] 更新成功 | material_id={material_id}")
            return {"success": True, "material_id": material_id, "base_price": base_price}
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_material_price] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新价格失败")