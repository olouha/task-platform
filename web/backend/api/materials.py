"""
材料管理 API
使用本地 SQLite 数据库实现数据持久化（services/materials_db_service.py）
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

from services.materials_db_service import MaterialsDBService
from services.auth_service import session_manager, user_service
from api.deps import get_current_user_can_delete

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> MaterialsDBService:
    """依赖注入：获取材料数据库服务实例"""
    return MaterialsDBService()


# ---------------- 输入验证模型 ----------------

class CategoryRequest(BaseModel):
    """材料分类请求体"""
    name: str = Field(..., min_length=1, max_length=50)
    icon: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=20)
    sort_order: int = Field(0, ge=0)


class MaterialRequest(BaseModel):
    """材料请求体"""
    category_id: Optional[str] = Field(None, max_length=64)
    name: str = Field(..., min_length=1, max_length=100)
    spec: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    base_price: Optional[float] = Field(None, ge=0)
    source: Optional[str] = Field(None, max_length=50)
    source_id: Optional[str] = Field(None, max_length=64)
    is_adjusted: bool = True
    adjustment_threshold: float = Field(5.0, ge=0, le=100)


# ==================== 分类 ====================

@router.get("/categories", response_model=List[dict])
async def list_categories(service: MaterialsDBService = Depends(get_service)) -> List[Dict[str, Any]]:
    """获取所有材料分类（含材料数量 count）"""
    logger.info("[list_categories] 接收请求")
    try:
        result = service.list_categories()
        logger.info(f"[list_categories] 返回 {len(result)} 个分类")
        return result
    except Exception as e:
        logger.error(f"[list_categories] 查询失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/categories", response_model=dict, status_code=201)
async def create_category(data: CategoryRequest, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """创建材料分类"""
    logger.info(f"[create_category] 接收请求 | name={data.name}")
    try:
        result = service.create_category(data.dict())
        logger.info(f"[create_category] 创建成功 | id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"[create_category] 创建失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建分类失败")


@router.get("/categories/{category_id}", response_model=dict)
async def get_category(category_id: str, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """获取分类详情"""
    logger.info(f"[get_category] 接收请求 | category_id={category_id}")
    try:
        category = service.get_category(category_id)
        if not category:
            logger.warning(f"[get_category] 分类不存在 | category_id={category_id}")
            raise HTTPException(status_code=404, detail="分类不存在")
        logger.info(f"[get_category] 查询成功 | category_id={category_id}")
        return category
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_category] 查询失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.put("/categories/{category_id}", response_model=dict)
async def update_category(category_id: str, data: CategoryRequest, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """更新分类"""
    logger.info(f"[update_category] 接收请求 | category_id={category_id}")
    try:
        success = service.update_category(category_id, data.dict())
        if not success:
            logger.warning(f"[update_category] 分类不存在 | category_id={category_id}")
            raise HTTPException(status_code=404, detail="分类不存在")
        logger.info(f"[update_category] 更新成功 | category_id={category_id}")
        return {**data.dict(), "id": category_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_category] 更新失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新分类失败")


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, admin_account: str = Depends(get_current_user_can_delete), service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """删除分类（仅管理员/管理/开发）"""
    logger.info(f"[delete_category] 接收请求 | category_id={category_id}, admin={admin_account}")
    try:
        success = service.delete_category(category_id)
        if success:
            logger.info(f"[delete_category] 删除成功 | category_id={category_id}")
        else:
            logger.warning(f"[delete_category] 分类不存在 | category_id={category_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_category] 删除失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


# ==================== 材料 ====================

@router.get("/", response_model=List[dict])
async def list_materials(
    category_id: Optional[str] = Query(None, max_length=64),
    service: MaterialsDBService = Depends(get_service)
) -> List[Dict[str, Any]]:
    """获取所有材料（含分类名称 category，可按 category_id 过滤）"""
    logger.info(f"[list_materials] 接收请求 | category_id={category_id}")
    try:
        materials = service.list_materials(category_id)
        logger.info(f"[list_materials] 返回 {len(materials)} 个材料")
        return materials
    except Exception as e:
        logger.error(f"[list_materials] 查询失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=dict, status_code=201)
async def create_material(data: MaterialRequest, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """创建材料"""
    logger.info(f"[create_material] 接收请求 | name={data.name}")
    try:
        result = service.create_material(data.dict())
        logger.info(f"[create_material] 创建成功 | id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"[create_material] 创建失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建材料失败")


@router.get("/{material_id}", response_model=dict)
async def get_material(material_id: str, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """获取材料详情"""
    logger.info(f"[get_material] 接收请求 | material_id={material_id}")
    try:
        result = service.get_material(material_id)
        if not result:
            logger.warning(f"[get_material] 材料不存在 | material_id={material_id}")
            raise HTTPException(status_code=404, detail="材料不存在")
        logger.info(f"[get_material] 查询成功 | material_id={material_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_material] 查询失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.put("/{material_id}", response_model=dict)
async def update_material(material_id: str, data: MaterialRequest, service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """更新材料"""
    logger.info(f"[update_material] 接收请求 | material_id={material_id}")
    try:
        success = service.update_material(material_id, data.dict())
        if not success:
            logger.warning(f"[update_material] 材料不存在 | material_id={material_id}")
            raise HTTPException(status_code=404, detail="材料不存在")
        result = service.get_material(material_id)
        logger.info(f"[update_material] 更新成功 | material_id={material_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_material] 更新失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新材料失败")


@router.delete("/{material_id}")
async def delete_material(material_id: str, admin_account: str = Depends(get_current_user_can_delete), service: MaterialsDBService = Depends(get_service)) -> Dict[str, Any]:
    """删除材料（仅管理员/管理/开发）"""
    logger.info(f"[delete_material] 接收请求 | material_id={material_id}, admin={admin_account}")
    try:
        success = service.delete_material(material_id)
        if success:
            logger.info(f"[delete_material] 删除成功 | material_id={material_id}")
        else:
            logger.warning(f"[delete_material] 材料不存在 | material_id={material_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_material] 删除失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


@router.put("/{material_id}/price")
async def update_material_price(
    material_id: str,
    base_price: float = Query(..., ge=0),
    service: MaterialsDBService = Depends(get_service)
) -> Dict[str, Any]:
    """更新材料基准价"""
    logger.info(f"[update_material_price] 接收请求 | material_id={material_id} | base_price={base_price}")
    try:
        success = service.update_material_price(material_id, base_price)
        if not success:
            logger.warning(f"[update_material_price] 材料不存在 | material_id={material_id}")
            raise HTTPException(status_code=404, detail="材料不存在")
        logger.info(f"[update_material_price] 更新成功 | material_id={material_id}")
        return {"success": True, "material_id": material_id, "base_price": base_price}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_material_price] 更新失败 | {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新价格失败")
