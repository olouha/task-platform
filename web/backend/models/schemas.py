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
    # 指标库扩展字段
    # 基本信息
    area_total: Optional[float] = None  # 总面积(㎡)
    area_above: Optional[float] = None  # 地上面积(㎡)
    area_below: Optional[float] = None  # 地下面积(㎡)
    floor_above: Optional[int] = None  # 地上层数
    floor_below: Optional[int] = None  # 地下层数
    height: Optional[float] = None  # 檐高(m)
    structure: Optional[str] = None  # 结构形式
    category_type: Optional[str] = None  # 业态类型
    location: Optional[str] = None  # 地区
    complete_date: Optional[str] = None  # 竣工时间
    # 造价指标
    total_cost: Optional[float] = None  # 总造价(万元)
    unit_cost: Optional[float] = None  # 单方造价(元/㎡)
    unit_structure: Optional[float] = None  # 土建单方(元/㎡)
    unit_installation: Optional[float] = None  # 安装单方(元/㎡)
    unit_decoration: Optional[float] = None  # 装饰单方(元/㎡)
    unit_measure: Optional[float] = None  # 措施费单方(元/㎡)
    # 主要经济指标
    underground_structure: Optional[float] = None  # 地下结构单方
    above_structure: Optional[float] = None  # 地上结构单方
    roof: Optional[float] = None  # 屋面工程单方
    exterior_wall: Optional[float] = None  # 外墙装饰单方
    interior_wall: Optional[float] = None  # 内墙装饰单方
    floor_area: Optional[float] = None  # 楼地面单方
    electrical: Optional[float] = None  # 电气工程单方
    plumbing: Optional[float] = None  # 给排水单方
    hvac: Optional[float] = None  # 暖通空调单方
    elevator: Optional[float] = None  # 电梯工程单方
    fire_protection: Optional[float] = None  # 消防工程单方
    # 主要材料含量
    steel_content: Optional[float] = None  # 钢筋含量(kg/㎡)
    concrete_content: Optional[float] = None  # 混凝土含量(m³/㎡)
    formwork_content: Optional[float] = None  # 模板含量(㎡/㎡)
    block_content: Optional[float] = None  # 砌块含量(m³/㎡)
    cable_content: Optional[float] = None  # 电缆含量(m/㎡)
    pipe_content: Optional[float] = None  # 管道含量(m/㎡)
    duct_content: Optional[float] = None  # 风管含量(㎡/㎡)
    # 修正系数
    height_factor: Optional[float] = None  # 高度修正系数
    structure_factor: Optional[float] = None  # 结构修正系数
    region_factor: Optional[float] = None  # 地区修正系数
    # 来源信息
    source_file: Optional[str] = None  # 原始文件
    remarks: Optional[str] = None  # 备注
    version: Optional[str] = "1.0"  # 版本
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdjustmentResult(BaseModel):
    """调差计算结果"""
    phase_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    adjustment: float
    materials: List[dict] = []