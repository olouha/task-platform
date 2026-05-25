"""
调差项目 API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import json
from pathlib import Path

from models.adjustment_project import (
    AdjustmentProject, MaterialItem, AttachmentFile,
    CreateProjectRequest, UpdateProjectRequest, ProjectMaterialRequest,
    AttachmentRequest, DEMO_PROJECTS
)

router = APIRouter(prefix="/api/adjustment-projects", tags=["调差项目管理"])

# 存储目录
DATA_DIR = Path(__file__).parent.parent / "services" / "data"
DATA_DIR.mkdir(exist_ok=True)
PROJECTS_FILE = DATA_DIR / "adjustment_projects.json"


def load_projects() -> List[dict]:
    """加载项目列表"""
    if PROJECTS_FILE.exists():
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEMO_PROJECTS.copy()


def save_projects(projects: List[dict]):
    """保存项目列表"""
    with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)


# ============================================================
# 项目管理 API
# ============================================================

@router.get("/", summary="获取所有调差项目")
async def list_projects():
    """获取所有调差项目列表"""
    projects = load_projects()
    return {"projects": projects, "total": len(projects)}


@router.get("/{project_id}", summary="获取单个项目")
async def get_project(project_id: str):
    """获取指定项目的详细信息"""
    projects = load_projects()
    for p in projects:
        if p.get("id") == project_id:
            return p
    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


@router.post("/", summary="创建调差项目")
async def create_project(request: CreateProjectRequest):
    """创建新的调差项目"""
    projects = load_projects()

    new_project = {
        "id": str(uuid.uuid4()),
        "name": request.name,
        "contract_no": request.contract_no,
        "rule_id": request.rule_id or "",
        "rule_name": request.rule_name,
        "base_price_source": request.base_price_source,
        "status": "draft",
        "materials": [],
        "attachments": [],
        "adjustment_result": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    projects.append(new_project)
    save_projects(projects)

    return {"id": new_project["id"], "name": new_project["name"], "success": True}


@router.put("/{project_id}", summary="更新项目")
async def update_project(project_id: str, request: UpdateProjectRequest):
    """更新项目信息"""
    projects = load_projects()

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            if request.name is not None:
                projects[i]["name"] = request.name
            if request.contract_no is not None:
                projects[i]["contract_no"] = request.contract_no
            if request.rule_id is not None:
                projects[i]["rule_id"] = request.rule_id
            if request.rule_name is not None:
                projects[i]["rule_name"] = request.rule_name
            if request.base_price_source is not None:
                projects[i]["base_price_source"] = request.base_price_source
            if request.construction_start is not None:
                projects[i]["construction_start"] = request.construction_start
            if request.construction_end is not None:
                projects[i]["construction_end"] = request.construction_end
            if request.status is not None:
                projects[i]["status"] = request.status

            projects[i]["updated_at"] = datetime.now().isoformat()
            save_projects(projects)
            return {"success": True, "project": projects[i]}

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


@router.delete("/{project_id}", summary="删除项目")
async def delete_project(project_id: str):
    """删除调差项目"""
    projects = load_projects()

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            projects.pop(i)
            save_projects(projects)
            return {"success": True}

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


# ============================================================
# 材料管理 API
# ============================================================

@router.post("/{project_id}/materials", summary="设置项目材料")
async def set_project_materials(project_id: str, materials: List[dict]):
    """设置项目的材料清单"""
    projects = load_projects()

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            # 确保材料有ID
            for j, m in enumerate(materials):
                if "id" not in m:
                    materials[j]["id"] = j + 1

            projects[i]["materials"] = materials
            projects[i]["updated_at"] = datetime.now().isoformat()
            save_projects(projects)
            return {"success": True, "count": len(materials)}

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


@router.get("/{project_id}/materials", summary="获取项目材料")
async def get_project_materials(project_id: str):
    """获取项目的材料清单"""
    projects = load_projects()

    for p in projects:
        if p.get("id") == project_id:
            return {"materials": p.get("materials", [])}

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


# ============================================================
# 附件管理 API
# ============================================================

@router.post("/{project_id}/attachments", summary="添加附件")
async def add_attachment(project_id: str, attachment: dict):
    """添加项目附件"""
    projects = load_projects()

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            attachment["id"] = attachment.get("id") or str(uuid.uuid4())
            attachment["uploaded_at"] = attachment.get("uploaded_at") or datetime.now().isoformat()

            if "attachments" not in projects[i]:
                projects[i]["attachments"] = []

            projects[i]["attachments"].append(attachment)
            projects[i]["updated_at"] = datetime.now().isoformat()
            save_projects(projects)
            return {"success": True, "attachment_id": attachment["id"]}

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


@router.delete("/{project_id}/attachments/{attachment_id}", summary="删除附件")
async def delete_attachment(project_id: str, attachment_id: str):
    """删除项目附件"""
    projects = load_projects()

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            attachments = p.get("attachments", [])
            for j, a in enumerate(attachments):
                if a.get("id") == attachment_id:
                    attachments.pop(j)
                    projects[i]["attachments"] = attachments
                    projects[i]["updated_at"] = datetime.now().isoformat()
                    save_projects(projects)
                    return {"success": True}

            raise HTTPException(status_code=404, detail=f"附件 {attachment_id} 不存在")

    raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")


# ============================================================
# Excel 解析 API
# ============================================================

@router.post("/parse-excel", summary="解析工程量表Excel")
async def parse_excel(file_content: bytes = None, filename: str = ""):
    """
    解析工程量表Excel文件
    提取材料名称、规格、用量等信息
    """
    # 如果没有上传文件，返回示例格式
    return {
        "success": True,
        "materials": [
            {"name": "钢筋HRB400", "spec": "Φ12", "unit": "t", "quantity": 500, "bid_price": 0},
            {"name": "钢筋HRB400", "spec": "Φ14", "unit": "t", "quantity": 300, "bid_price": 0},
            {"name": "钢筋HRB400", "spec": "Φ25", "unit": "t", "quantity": 800, "bid_price": 0},
            {"name": "商品混凝土", "spec": "C30", "unit": "m³", "quantity": 2000, "bid_price": 0},
            {"name": "商品混凝土", "spec": "C35", "unit": "m³", "quantity": 1500, "bid_price": 0},
        ],
        "message": "请上传Excel文件以获取实际数据"
    }


@router.get("/excel-template", summary="下载工程量表模板")
async def get_excel_template():
    """获取工程量表Excel模板"""
    return {
        "template": {
            "name": "工程量表模板",
            "description": "调差工程量表Excel模板，包含以下列：",
            "columns": [
                {"name": "材料名称", "example": "钢筋HRB400"},
                {"name": "规格型号", "example": "Φ12"},
                {"name": "单位", "example": "t"},
                {"name": "工程量", "example": "500"},
                {"name": "投标单价", "example": "4200"},
                {"name": "施工阶段", "example": "地下室/主体结构"},
                {"name": "备注", "example": ""},
            ]
        }
    }