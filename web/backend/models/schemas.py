"""
数据模型
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class MaterialCategory(BaseModel):
    """材料分类"""
    id: Optional[str] = None
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0


class Material(BaseModel):
    """材料"""
    id: Optional[str] = None
    category_id: Optional[str] = None
    name: str
    spec: Optional[str] = None
    unit: Optional[str] = None
    base_price: Optional[float] = None
    source_id: Optional[str] = None
    is_adjusted: bool = True
    adjustment_threshold: float = 5.0


class PriceSource(BaseModel):
    """价格来源"""
    id: Optional[str] = None
    name: str
    website_name: str
    website_url: str
    material_category: str
    price_url: str
    selector: Optional[str] = None
    xpath: Optional[str] = None
    is_active: bool = True
    interval_minutes: int = 1440
    last_fetched_at: Optional[datetime] = None


class PriceRecord(BaseModel):
    """价格记录"""
    id: Optional[str] = None
    material_id: Optional[str] = None
    source_id: Optional[str] = None
    price: float
    unit: Optional[str] = None
    recorded_date: date
    raw_data: Optional[dict] = None
    fetch_status: Optional[str] = None


class Project(BaseModel):
    """项目"""
    id: Optional[str] = None
    name: str
    contract_no: Optional[str] = None
    contract_date: Optional[date] = None
    base_date: Optional[date] = None
    completion_date: Optional[date] = None
    total_value: Optional[float] = None
    created_by: Optional[str] = None


class ProjectMaterial(BaseModel):
    """项目材料"""
    id: Optional[str] = None
    project_id: str
    material_id: Optional[str] = None
    material_name: str
    spec: Optional[str] = None
    unit: Optional[str] = None
    quantity: float
    contract_price: float
    base_price: float
    adjustment_type: str = "adjustable"  # full, adjustable, fixed
    threshold: float = 5.0
    source_id: Optional[str] = None


class ConstructionPhase(BaseModel):
    """施工阶段"""
    id: Optional[str] = None
    project_id: str
    phase_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = None
    sort_order: int = 0


class AdjustmentRecord(BaseModel):
    """调差记录"""
    id: Optional[str] = None
    project_id: str
    material_id: Optional[str] = None
    phase_id: Optional[str] = None
    phase_name: Optional[str] = None
    base_price: float
    current_price: float
    change_rate: float
    adjustment_amount: float
    calculated_at: Optional[datetime] = None


class IndicatorCategory(BaseModel):
    """指标分类"""
    id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0


class Indicator(BaseModel):
    """指标"""
    id: Optional[str] = None
    category_id: Optional[str] = None
    project_id: Optional[str] = None
    name: str
    unit: Optional[str] = None
    target_value: Optional[float] = None
    target_type: Optional[str] = None
    warning_threshold: Optional[float] = None
    current_value: Optional[float] = None
    data_type: str = "number"
    status: str = "normal"


class AdjustmentResult(BaseModel):
    """调差计算结果"""
    phase_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    adjustment: float
    materials: List[dict] = []