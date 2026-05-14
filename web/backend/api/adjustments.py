"""
调差计算 API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from services.adjustment_calculator import AdjustmentCalculator
from models.schemas import AdjustmentRecord, AdjustmentResult

router = APIRouter()
calculator = AdjustmentCalculator()

# 模拟数据
_adjustment_records_db = {}


@router.post("/calculate", response_model=List[AdjustmentResult])
async def calculate_adjustment(
    project_id: str,
    phase_id: str = None,
    materials: List[dict] = [],
    price_history: dict = {}
):
    """计算调差"""
    # 模拟数据
    phases = [{'id': phase_id, 'phase_name': '阶段一', 'start_date': '2024-01-01', 'end_date': '2024-06-30'}]

    result = calculator.calculate_project_adjustment(
        project_id,
        phases,
        materials,
        price_history
    )

    return result.get('phases', [])


@router.get("/records", response_model=List[AdjustmentRecord])
async def list_adjustment_records(
    project_id: str = None,
    phase_id: str = None
):
    """获取调差记录"""
    records = list(_adjustment_records_db.values())

    if project_id:
        records = [r for r in records if r.project_id == project_id]
    if phase_id:
        records = [r for r in records if r.phase_id == phase_id]

    return records


@router.post("/records", response_model=AdjustmentRecord)
async def create_adjustment_record(record: AdjustmentRecord):
    """创建调差记录"""
    import uuid
    record.id = str(uuid.uuid4())
    _adjustment_records_db[record.id] = record
    return record


@router.get("/project/{project_id}/summary")
async def get_project_adjustment_summary(project_id: str):
    """获取项目调差汇总"""
    records = [r for r in _adjustment_records_db.values() if r.project_id == project_id]

    if not records:
        return {
            'project_id': project_id,
            'total_adjustment': 0,
            'phases': [],
            'materials': []
        }

    # 按阶段分组
    phase_summary = {}
    material_summary = {}

    for record in records:
        phase_id = record.phase_id
        if phase_id not in phase_summary:
            phase_summary[phase_id] = {
                'phase_id': phase_id,
                'phase_name': record.phase_name,
                'total': 0
            }
        phase_summary[phase_id]['total'] += record.adjustment_amount

        material_id = record.material_id
        if material_id not in material_summary:
            material_summary[material_id] = {
                'material_id': material_id,
                'total': 0
            }
        material_summary[material_id]['total'] += record.adjustment_amount

    total = sum(r.adjustment_amount for r in records)

    return {
        'project_id': project_id,
        'total_adjustment': round(total, 2),
        'adjustment_text': calculator.number_to_chinese(total),
        'phases': list(phase_summary.values()),
        'materials': list(material_summary.values())
    }


@router.post("/export/{project_id}")
async def export_adjustment_report(project_id: str):
    """导出调差报告"""
    records = [r for r in _adjustment_records_db.values() if r.project_id == project_id]

    if not records:
        raise HTTPException(status_code=404, detail="无调差记录")

    result = {
        'project_id': project_id,
        'total_adjustment': sum(r.adjustment_amount for r in records),
        'adjustment_text': calculator.number_to_chinese(sum(r.adjustment_amount for r in records)),
        'records': [
            {
                'phase_name': r.phase_name,
                'base_price': r.base_price,
                'current_price': r.current_price,
                'change_rate': f"{r.change_rate:+.2f}%",
                'adjustment_amount': r.adjustment_amount
            }
            for r in records
        ]
    }

    return result