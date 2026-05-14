"""
项目管理 API
"""

from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import Project, ProjectMaterial, ConstructionPhase

router = APIRouter()

# 模拟数据（后续连接 Supabase）
_projects_db = {}
_phases_db = {}
_project_materials_db = {}


@router.get("/", response_model=List[Project])
async def list_projects():
    """获取所有项目"""
    return list(_projects_db.values())


@router.post("/", response_model=Project)
async def create_project(project: Project):
    """创建项目"""
    import uuid
    project.id = str(uuid.uuid4())
    _projects_db[project.id] = project
    return project


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """获取项目详情"""
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    return _projects_db[project_id]


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, project: Project):
    """更新项目"""
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    project.id = project_id
    _projects_db[project_id] = project
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """删除项目"""
    if project_id in _projects_db:
        del _projects_db[project_id]
    return {"success": True}


# ========== 施工阶段 ==========

@router.get("/{project_id}/phases", response_model=List[ConstructionPhase])
async def list_phases(project_id: str):
    """获取项目施工阶段"""
    return [p for p in _phases_db.values() if p.project_id == project_id]


@router.post("/{project_id}/phases", response_model=ConstructionPhase)
async def create_phase(project_id: str, phase: ConstructionPhase):
    """创建施工阶段"""
    import uuid
    phase.id = str(uuid.uuid4())
    phase.project_id = project_id
    _phases_db[phase.id] = phase
    return phase


# ========== 项目材料 ==========

@router.get("/{project_id}/materials", response_model=List[ProjectMaterial])
async def list_project_materials(project_id: str):
    """获取项目材料"""
    return [m for m in _project_materials_db.values() if m.project_id == project_id]


@router.post("/{project_id}/materials", response_model=ProjectMaterial)
async def add_project_material(project_id: str, material: ProjectMaterial):
    """添加项目材料"""
    import uuid
    material.id = str(uuid.uuid4())
    material.project_id = project_id
    _project_materials_db[material.id] = material
    return material


@router.put("/{project_id}/materials/{material_id}", response_model=ProjectMaterial)
async def update_project_material(project_id: str, material_id: str, material: ProjectMaterial):
    """更新项目材料"""
    if material_id not in _project_materials_db:
        raise HTTPException(status_code=404, detail="材料不存在")
    material.id = material_id
    material.project_id = project_id
    _project_materials_db[material_id] = material
    return material


@router.delete("/{project_id}/materials/{material_id}")
async def delete_project_material(project_id: str, material_id: str):
    """删除项目材料"""
    if material_id in _project_materials_db:
        del _project_materials_db[material_id]
    return {"success": True}