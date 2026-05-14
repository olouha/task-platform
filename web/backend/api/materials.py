"""
材料管理 API
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import MaterialCategory, Material

router = APIRouter()

# 模拟数据
_categories_db = {}
_materials_db = {}


@router.get("/categories", response_model=List[MaterialCategory])
async def list_categories():
    """获取所有材料分类"""
    return sorted(_categories_db.values(), key=lambda x: x.sort_order)


@router.post("/categories", response_model=MaterialCategory)
async def create_category(category: MaterialCategory):
    """创建材料分类"""
    import uuid
    category.id = str(uuid.uuid4())
    _categories_db[category.id] = category
    return category


@router.get("/categories/{category_id}", response_model=MaterialCategory)
async def get_category(category_id: str):
    """获取分类详情"""
    if category_id not in _categories_db:
        raise HTTPException(status_code=404, detail="分类不存在")
    return _categories_db[category_id]


@router.put("/categories/{category_id}", response_model=MaterialCategory)
async def update_category(category_id: str, category: MaterialCategory):
    """更新分类"""
    if category_id not in _categories_db:
        raise HTTPException(status_code=404, detail="分类不存在")
    category.id = category_id
    _categories_db[category_id] = category
    return category


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    """删除分类"""
    if category_id in _categories_db:
        del _categories_db[category_id]
    return {"success": True}


# ========== 材料 ==========

@router.get("/", response_model=List[Material])
async def list_materials(category_id: str = None):
    """获取所有材料"""
    materials = list(_materials_db.values())
    if category_id:
        materials = [m for m in materials if m.category_id == category_id]
    return materials


@router.post("/", response_model=Material)
async def create_material(material: Material):
    """创建材料"""
    import uuid
    material.id = str(uuid.uuid4())
    _materials_db[material.id] = material
    return material


@router.get("/{material_id}", response_model=Material)
async def get_material(material_id: str):
    """获取材料详情"""
    if material_id not in _materials_db:
        raise HTTPException(status_code=404, detail="材料不存在")
    return _materials_db[material_id]


@router.put("/{material_id}", response_model=Material)
async def update_material(material_id: str, material: Material):
    """更新材料"""
    if material_id not in _materials_db:
        raise HTTPException(status_code=404, detail="材料不存在")
    material.id = material_id
    _materials_db[material_id] = material
    return material


@router.delete("/{material_id}")
async def delete_material(material_id: str):
    """删除材料"""
    if material_id in _materials_db:
        del _materials_db[material_id]
    return {"success": True}


@router.put("/{material_id}/price")
async def update_material_price(material_id: str, base_price: float):
    """更新材料基准价"""
    if material_id not in _materials_db:
        raise HTTPException(status_code=404, detail="材料不存在")
    _materials_db[material_id].base_price = base_price
    return _materials_db[material_id]