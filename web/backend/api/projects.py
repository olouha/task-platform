"""
项目管理 API（老 Projects 模块）
使用本地 SQLite 数据库实现数据持久化（原 Supabase 已禁用）

字段契约与前端 Projects.tsx 保持一致：id / name / description / created_at / status
注意：与「调差项目管理」(adjustment_projects) 是两套独立数据，互不影响。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import logging

from models.schemas import ProjectMaterial, ConstructionPhase
from services.supabase_service import SupabaseService
from services import projects_db_service
from api.deps import get_current_user_can_delete

router = APIRouter()
logger = logging.getLogger(__name__)


class ProjectCreateRequest(BaseModel):
    """创建项目请求（契约对齐前端）"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field("", max_length=2000)
    status: Literal["active", "completed"] = Field("active")


class ProjectUpdateRequest(BaseModel):
    """更新项目请求（字段均可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[Literal["active", "completed"]] = None


def get_supabase() -> SupabaseService:
    return SupabaseService()


@router.get("/", response_model=List[dict])
async def list_projects() -> List[Dict[str, Any]]:
    """获取所有项目（本地 SQLite）"""
    logger.info("[list_projects] 从本地数据库查询所有项目")
    try:
        result = projects_db_service.list_projects()
        logger.info(f"[list_projects] 返回 {len(result)} 个项目")
        return result
    except Exception as e:
        logger.error(f"[list_projects] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/", response_model=dict)
async def create_project(project: ProjectCreateRequest) -> Dict[str, Any]:
    """创建项目（本地 SQLite）"""
    logger.info(f"[create_project] 创建项目 | name={project.name}, status={project.status}")
    try:
        result = projects_db_service.create_project(
            name=project.name,
            description=project.description or "",
            status=project.status,
        )
        logger.info(f"[create_project] 创建成功 | id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"[create_project] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建项目失败")


@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str) -> Dict[str, Any]:
    """获取项目详情（本地 SQLite）"""
    logger.info(f"[get_project] 查询项目 | project_id={project_id}")
    try:
        result = projects_db_service.get_project(project_id)
        if not result:
            logger.warning(f"[get_project] 项目不存在 | project_id={project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")
        logger.info(f"[get_project] 查询成功 | project_id={project_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_project] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.put("/{project_id}", response_model=dict)
async def update_project(project_id: str, project: ProjectUpdateRequest, admin_account: str = Depends(get_current_user_can_delete)) -> Dict[str, Any]:
    """更新项目（本地 SQLite）"""
    logger.info(f"[update_project] 更新项目 | project_id={project_id}")
    try:
        result = projects_db_service.update_project(
            project_id,
            name=project.name,
            description=project.description,
            status=project.status,
        )
        if not result:
            logger.warning(f"[update_project] 项目不存在 | project_id={project_id}")
            raise HTTPException(status_code=404, detail="项目不存在")
        logger.info(f"[update_project] 更新成功 | project_id={project_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_project] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新项目失败")


@router.delete("/{project_id}")
async def delete_project(project_id: str, admin_account: str = Depends(get_current_user_can_delete)) -> Dict[str, Any]:
    """删除项目（本地 SQLite）"""
    logger.info(f"[delete_project] 删除项目 | project_id={project_id}")
    try:
        success = projects_db_service.delete_project(project_id)
        if success:
            logger.info(f"[delete_project] 删除成功 | project_id={project_id}")
        else:
            logger.warning(f"[delete_project] 项目不存在 | project_id={project_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_project] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")


# ========== 施工阶段 ==========

@router.get("/{project_id}/phases", response_model=List[dict])
async def list_phases(project_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取项目施工阶段"""
    logger.info(f"[list_phases] 查询施工阶段 | project_id={project_id}")
    try:
        result = supabase.get_project_phases(project_id)
        logger.info(f"[list_phases] 返回 {len(result)} 个阶段")
        return result
    except Exception as e:
        logger.error(f"[list_phases] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/{project_id}/phases", response_model=dict)
async def create_phase(project_id: str, phase: ConstructionPhase, supabase: SupabaseService = Depends(get_supabase)):
    """创建施工阶段"""
    logger.info(f"[create_phase] 创建阶段 | project_id={project_id}")
    try:
        phase_data = phase.dict(exclude={'id'})
        phase_data['project_id'] = project_id
        result = supabase.create_project_phase(phase_data)
        if result:
            logger.info(f"[create_phase] 创建成功 | phase_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="创建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[create_phase] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建阶段失败")


# ========== 项目材料 ==========

@router.get("/{project_id}/materials", response_model=List[dict])
async def list_project_materials(project_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取项目材料"""
    logger.info(f"[list_project_materials] 查询材料 | project_id={project_id}")
    try:
        result = supabase.get_project_materials(project_id)
        logger.info(f"[list_project_materials] 返回 {len(result)} 个材料")
        return result
    except Exception as e:
        logger.error(f"[list_project_materials] 查询失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询失败")


@router.post("/{project_id}/materials", response_model=dict)
async def add_project_material(project_id: str, material: ProjectMaterial, supabase: SupabaseService = Depends(get_supabase)):
    """添加项目材料"""
    logger.info(f"[add_project_material] 添加材料 | project_id={project_id}, name={material.name}")
    try:
        material_data = material.dict(exclude={'id'})
        material_data['project_id'] = project_id
        result = supabase.create_project_material(material_data)
        if result:
            logger.info(f"[add_project_material] 添加成功 | material_id={result['id']}")
            return result
        else:
            raise HTTPException(status_code=500, detail="添加失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[add_project_material] 添加失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="添加材料失败")


@router.put("/{project_id}/materials/{material_id}", response_model=dict)
async def update_project_material(project_id: str, material_id: str, material: ProjectMaterial, supabase: SupabaseService = Depends(get_supabase)):
    """更新项目材料"""
    logger.info(f"[update_project_material] 更新材料 | material_id={material_id}")
    try:
        material_data = material.dict(exclude={'id'})
        material_data['project_id'] = project_id
        success = supabase.update_project_material(material_id, material_data)
        if success:
            logger.info(f"[update_project_material] 更新成功 | material_id={material_id}")
            return material_data
        else:
            raise HTTPException(status_code=500, detail="更新失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[update_project_material] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新材料失败")


@router.delete("/{project_id}/materials/{material_id}")
async def delete_project_material(project_id: str, material_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """删除项目材料"""
    logger.info(f"[delete_project_material] 删除材料 | material_id={material_id}")
    try:
        success = supabase.delete_project_material(material_id)
        if success:
            logger.info(f"[delete_project_material] 删除成功 | material_id={material_id}")
        else:
            logger.warning(f"[delete_project_material] 材料不存在 | material_id={material_id}")
        return {"success": success}
    except Exception as e:
        logger.error(f"[delete_project_material] 删除失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除失败")