"""
指标库数据模型
用于指标库管理系统的数据验证和序列化
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IndicatorLibrarySummary(BaseModel):
    """汇总项模型 - 用于列表展示"""
    id: str
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    category: str = Field(..., description="业态: 住宅/商业/办公/工业")
    location: str = Field(..., description="项目所在地")
    structure: str = Field(..., description="结构形式")
    start_date: Optional[str] = Field(None, description="开工时间(YYYY-MM)")
    end_date: Optional[str] = Field(None, description="竣工时间(YYYY-MM)")
    area_total: Optional[float] = Field(None, gt=0, description="总建筑面积(㎡)")
    unit_cost: Optional[float] = Field(None, gt=0, description="平米造价(元/㎡)")
    entry_date: Optional[str] = Field(None, description="录入时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "IND-20240101001",
                "name": "XX住宅项目",
                "category": "住宅",
                "location": "山东烟台",
                "structure": "框架结构",
                "start_date": "2023-01",
                "end_date": "2024-06",
                "area_total": 25000.0,
                "unit_cost": 2350.0,
                "entry_date": "2026-07-01 10:30:00",
                "updated_at": "2026-07-01T10:30:00"
            }
        }


class IndicatorLibraryDetail(BaseModel):
    """完整明细模型 - 用于详情和编辑"""
    # 基本信息
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    category: str = Field(..., description="业态: 住宅/商业/办公/工业")
    location: str = Field(..., description="项目所在地")
    structure: str = Field(..., description="结构形式")
    delivery_type: Optional[str] = Field(None, description="交付形式")
    foundation_type: Optional[str] = Field(None, description="桩基形式")
    start_date: Optional[str] = Field(None, description="开工时间(YYYY-MM)")
    end_date: Optional[str] = Field(None, description="竣工时间(YYYY-MM)")
    floor_above: Optional[int] = Field(None, ge=0, description="地上层数")
    floor_below: Optional[int] = Field(None, ge=0, description="地下层数")
    height: Optional[float] = Field(None, gt=0, description="檐高(m)")
    area_total: Optional[float] = Field(None, gt=0, description="总建筑面积(㎡)")
    area_above: Optional[float] = Field(None, ge=0, description="地上建筑面积(㎡)")
    area_below: Optional[float] = Field(None, ge=0, description="地下建筑面积(㎡)")

    # 造价指标
    unit_cost: Optional[float] = Field(None, gt=0, description="平米造价(元/㎡)")
    total_cost: Optional[float] = Field(None, gt=0, description="总造价(元)")
    unit_structure: Optional[float] = Field(None, ge=0, description="结构平米造价")
    unit_installation: Optional[float] = Field(None, ge=0, description="安装平米造价")

    # 地上/地下造价分解
    cost_above_structure: Optional[float] = Field(None, ge=0, description="地上土建造价(元)")
    cost_above_installation: Optional[float] = Field(None, ge=0, description="地上安装造价(元)")
    unit_cost_above_structure: Optional[float] = Field(None, ge=0, description="地上结构平米造价(元/㎡)")
    unit_cost_above_installation: Optional[float] = Field(None, ge=0, description="地上安装平米造价(元/㎡)")
    cost_underground_structure: Optional[float] = Field(None, ge=0, description="地下土建造价(元)")
    cost_underground_installation: Optional[float] = Field(None, ge=0, description="地下安装造价(元)")
    unit_cost_underground_structure: Optional[float] = Field(None, ge=0, description="地下结构平米造价(元/㎡)")
    unit_cost_underground_installation: Optional[float] = Field(None, ge=0, description="地下安装平米造价(元/㎡)")

    # 措施费与室外
    cost_measures: Optional[float] = Field(None, ge=0, description="措施费(元)")
    unit_cost_measures: Optional[float] = Field(None, ge=0, description="措施费平米造价(元/㎡)")
    cost_outdoor: Optional[float] = Field(None, ge=0, description="室外造价(元)")
    unit_cost_outdoor: Optional[float] = Field(None, ge=0, description="室外平米造价(元/㎡)")

    # 专项工程（8组）
    cost_pile: Optional[float] = Field(None, ge=0, description="桩基工程造价(元)")
    unit_cost_pile: Optional[float] = Field(None, ge=0, description="桩基工程平米造价(元/㎡)")
    cost_foundation_support: Optional[float] = Field(None, ge=0, description="基坑支护工程造价(元)")
    unit_cost_foundation_support: Optional[float] = Field(None, ge=0, description="基坑支护平米造价(元/㎡)")
    cost_curtain_wall: Optional[float] = Field(None, ge=0, description="幕墙工程造价(元)")
    unit_cost_curtain_wall: Optional[float] = Field(None, ge=0, description="幕墙平米造价(元/㎡)")
    cost_decoration: Optional[float] = Field(None, ge=0, description="装饰工程造价(元)")
    unit_cost_decoration: Optional[float] = Field(None, ge=0, description="装饰平米造价(元/㎡)")
    cost_exterior_insulation: Optional[float] = Field(None, ge=0, description="外墙保温工程造价(元)")
    unit_cost_exterior_insulation: Optional[float] = Field(None, ge=0, description="外墙保温平米造价(元/㎡)")
    cost_exterior_windows: Optional[float] = Field(None, ge=0, description="外窗工程造价(元)")
    unit_cost_exterior_windows: Optional[float] = Field(None, ge=0, description="外窗平米造价(元/㎡)")
    cost_water_drainage: Optional[float] = Field(None, ge=0, description="给排水工程造价(元)")
    unit_cost_water_drainage: Optional[float] = Field(None, ge=0, description="给排水平米造价(元/㎡)")
    cost_heating: Optional[float] = Field(None, ge=0, description="采暖工程造价(元)")
    unit_cost_heating: Optional[float] = Field(None, ge=0, description="采暖平米造价(元/㎡)")
    cost_electrical: Optional[float] = Field(None, ge=0, description="电气工程造价(元)")
    unit_cost_electrical: Optional[float] = Field(None, ge=0, description="电气平米造价(元/㎡)")
    cost_hvac: Optional[float] = Field(None, ge=0, description="暖通工程造价(元)")
    unit_cost_hvac: Optional[float] = Field(None, ge=0, description="暖通平米造价(元/㎡)")

    # 地上主体材料
    above_concrete: Optional[float] = Field(None, ge=0, description="地上砼用量(m³)")
    above_concrete_unit: Optional[float] = Field(None, ge=0, description="地上砼平米含量(m³/㎡)")
    above_rebar: Optional[float] = Field(None, ge=0, description="地上钢筋用量(t)")
    above_rebar_unit: Optional[float] = Field(None, ge=0, description="地上钢筋平米含量(t/㎡)")
    above_formwork: Optional[float] = Field(None, ge=0, description="地上模板用量(m²)")
    above_formwork_unit: Optional[float] = Field(None, ge=0, description="地上模板平米含量(m²/㎡)")

    # 地下主体材料
    underground_concrete: Optional[float] = Field(None, ge=0, description="地下砼用量(m³)")
    underground_concrete_unit: Optional[float] = Field(None, ge=0, description="地下砼平米含量(m³/㎡)")
    underground_rebar: Optional[float] = Field(None, ge=0, description="地下钢筋用量(t)")
    underground_rebar_unit: Optional[float] = Field(None, ge=0, description="地下钢筋平米含量(t/㎡)")
    underground_formwork: Optional[float] = Field(None, ge=0, description="地下模板用量(m²)")
    underground_formwork_unit: Optional[float] = Field(None, ge=0, description="地下模板平米含量(m²/㎡)")

    # 元数据
    source: Optional[str] = Field(None, description="数据来源")
    source_file: Optional[str] = Field(None, description="来源文件名")
    remarks: Optional[str] = Field(None, max_length=500, description="备注")
    entry_date: Optional[str] = Field(None, description="录入时间")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "XX住宅项目",
                "category": "住宅",
                "location": "山东烟台",
                "structure": "框架结构",
                "delivery_type": "毛坯交付",
                "foundation_type": "钢板桩",
                "start_date": "2023-01",
                "end_date": "2024-06",
                "floor_above": 12,
                "floor_below": 2,
                "height": 36.0,
                "area_total": 25000.0,
                "unit_cost": 2350.0
            }
        }


class IndicatorLibraryCreate(BaseModel):
    """创建指标库项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    category: str = Field(..., description="业态: 住宅/商业/办公/工业")
    location: str = Field(..., description="项目所在地")
    structure: str = Field(..., description="结构形式")
    delivery_type: Optional[str] = Field(None, description="交付形式")
    foundation_type: Optional[str] = Field(None, description="桩基形式")
    start_date: Optional[str] = Field(None, description="开工时间(YYYY-MM)")
    end_date: Optional[str] = Field(None, description="竣工时间(YYYY-MM)")
    floor_above: Optional[int] = Field(None, ge=0, description="地上层数")
    floor_below: Optional[int] = Field(None, ge=0, description="地下层数")
    height: Optional[float] = Field(None, gt=0, description="檐高(m)")
    area_total: Optional[float] = Field(None, gt=0, description="总建筑面积(㎡)")
    area_above: Optional[float] = Field(None, ge=0, description="地上建筑面积(㎡)")
    area_below: Optional[float] = Field(None, ge=0, description="地下建筑面积(㎡)")
    unit_cost: Optional[float] = Field(None, gt=0, description="平米造价(元/㎡)")
    total_cost: Optional[float] = Field(None, gt=0, description="总造价(元)")
    unit_structure: Optional[float] = Field(None, ge=0, description="结构平米造价")
    unit_installation: Optional[float] = Field(None, ge=0, description="安装平米造价")
    cost_above_structure: Optional[float] = Field(None, ge=0)
    cost_above_installation: Optional[float] = Field(None, ge=0)
    unit_cost_above_structure: Optional[float] = Field(None, ge=0)
    unit_cost_above_installation: Optional[float] = Field(None, ge=0)
    cost_underground_structure: Optional[float] = Field(None, ge=0)
    cost_underground_installation: Optional[float] = Field(None, ge=0)
    unit_cost_underground_structure: Optional[float] = Field(None, ge=0)
    unit_cost_underground_installation: Optional[float] = Field(None, ge=0)
    cost_measures: Optional[float] = Field(None, ge=0)
    unit_cost_measures: Optional[float] = Field(None, ge=0)
    cost_outdoor: Optional[float] = Field(None, ge=0)
    unit_cost_outdoor: Optional[float] = Field(None, ge=0)
    cost_pile: Optional[float] = Field(None, ge=0)
    unit_cost_pile: Optional[float] = Field(None, ge=0)
    cost_foundation_support: Optional[float] = Field(None, ge=0)
    unit_cost_foundation_support: Optional[float] = Field(None, ge=0)
    cost_curtain_wall: Optional[float] = Field(None, ge=0)
    unit_cost_curtain_wall: Optional[float] = Field(None, ge=0)
    cost_decoration: Optional[float] = Field(None, ge=0)
    unit_cost_decoration: Optional[float] = Field(None, ge=0)
    cost_exterior_insulation: Optional[float] = Field(None, ge=0)
    unit_cost_exterior_insulation: Optional[float] = Field(None, ge=0)
    cost_exterior_windows: Optional[float] = Field(None, ge=0)
    unit_cost_exterior_windows: Optional[float] = Field(None, ge=0)
    cost_water_drainage: Optional[float] = Field(None, ge=0)
    unit_cost_water_drainage: Optional[float] = Field(None, ge=0)
    cost_heating: Optional[float] = Field(None, ge=0)
    unit_cost_heating: Optional[float] = Field(None, ge=0)
    cost_electrical: Optional[float] = Field(None, ge=0)
    unit_cost_electrical: Optional[float] = Field(None, ge=0)
    cost_hvac: Optional[float] = Field(None, ge=0)
    unit_cost_hvac: Optional[float] = Field(None, ge=0)
    above_concrete: Optional[float] = Field(None, ge=0)
    above_concrete_unit: Optional[float] = Field(None, ge=0)
    above_rebar: Optional[float] = Field(None, ge=0)
    above_rebar_unit: Optional[float] = Field(None, ge=0)
    above_formwork: Optional[float] = Field(None, ge=0)
    above_formwork_unit: Optional[float] = Field(None, ge=0)
    underground_concrete: Optional[float] = Field(None, ge=0)
    underground_concrete_unit: Optional[float] = Field(None, ge=0)
    underground_rebar: Optional[float] = Field(None, ge=0)
    underground_rebar_unit: Optional[float] = Field(None, ge=0)
    underground_formwork: Optional[float] = Field(None, ge=0)
    underground_formwork_unit: Optional[float] = Field(None, ge=0)
    source: Optional[str] = Field(None, description="数据来源")
    source_file: Optional[str] = Field(None, description="来源文件名")
    remarks: Optional[str] = Field(None, max_length=500, description="备注")

    class Config:
        extra = "allow"  # 允许额外字段


class ValidationWarning(BaseModel):
    """验证警告"""
    field: str = Field(..., description="字段名")
    message: str = Field(..., description="警告信息")
    severity: str = Field(..., description="严重程度: warning/error")
    value: Optional[Any] = Field(None, description="当前值")
    expected: Optional[str] = Field(None, description="期望值或范围")


class ValidationResult(BaseModel):
    """验证结果"""
    passed: bool = Field(..., description="是否通过验证")
    warnings: List[ValidationWarning] = Field(default_factory=list, description="警告列表")
    errors: List[ValidationWarning] = Field(default_factory=list, description="错误列表")
    checks: Dict[str, str] = Field(default_factory=dict, description="各检查项结果")


class ImportPreviewItem(BaseModel):
    """导入预览项"""
    index: int = Field(..., description="序号")
    name: str = Field(..., description="项目名称")
    category: Optional[str] = Field(None, description="业态")
    location: Optional[str] = Field(None, description="项目所在地")
    unit_cost: Optional[float] = Field(None, description="平米造价")
    status: str = Field(..., description="状态: valid/warning/error")
    warnings: List[str] = Field(default_factory=list, description="警告信息列表")
    errors: List[str] = Field(default_factory=list, description="错误信息列表")


class ImportPreviewResult(BaseModel):
    """导入预览结果"""
    total: int = Field(..., description="总项目数")
    valid_count: int = Field(..., description="有效项目数")
    warning_count: int = Field(..., description="警告项目数")
    error_count: int = Field(..., description="错误项目数")
    items: List[ImportPreviewItem] = Field(..., description="项目列表")


class ImportResult(BaseModel):
    """导入结果"""
    success: bool = Field(..., description="是否成功")
    imported: int = Field(..., description="成功导入数")
    total: int = Field(..., description="总数")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="警告列表")
    errors: List[str] = Field(default_factory=list, description="错误列表")


# 辅助函数

def get_all_model_fields() -> List[str]:
    """
    获取 IndicatorLibraryDetail 模型的所有字段名

    Returns:
        字段名列表
    """
    logger.debug("[get_all_model_fields] 获取所有字段名")
    return list(IndicatorLibraryDetail.model_fields.keys())


def validate_field_value(field_name: str, value: Any) -> bool:
    """
    验证单个字段值

    Args:
        field_name: 字段名
        value: 值

    Returns:
        是否有效
    """
    try:
        model = IndicatorLibraryDetail.model_validate({field_name: value})
        return field_name in model.model_fields
    except Exception:
        return False