"""
调差项目数据模型
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date


class MaterialItem(BaseModel):
    """材料清单条目"""
    id: Optional[int] = None
    name: str  # 材料名称
    spec: str = ""  # 规格型号
    unit: str = "t"  # 单位
    quantity: float = 0  # 用量
    bid_price: float = 0  # 投标单价
    base_price: float = 0  # 基准价(自动匹配或手动输入)
    phase: str = ""  # 施工阶段
    notes: str = ""  # 备注
    # 新增：部位/楼栋信息
    location: str = ""  # 楼栋/部位名称，如"1#楼"、"地下室"
    start_date: Optional[str] = None  # 施工开始日期 YYYY-MM-DD
    end_date: Optional[str] = None  # 施工结束日期 YYYY-MM-DD


class AttachmentFile(BaseModel):
    """附件文件"""
    id: str
    name: str  # 文件名
    type: str  # 文件类型 (quantity/schedule/contract/other)
    size: int  # 文件大小(bytes)
    url: str = ""  # 文件路径/URL
    uploaded_at: str  # 上传时间


class AdjustmentProject(BaseModel):
    """调差项目"""
    id: Optional[str] = None
    name: str  # 项目名称
    contract_no: str = ""  # 合同编号
    rule_id: Optional[str] = None  # 关联的调差规则ID
    rule_name: str = ""  # 调差规则名称
    base_price_source: str = "造价信息"  # 基准价来源 (造价信息/钢铁网/投标价)

    # 施工周期
    construction_start: Optional[date] = None  # 施工开始日期
    construction_end: Optional[date] = None  # 施工结束日期

    # 材料清单
    materials: List[MaterialItem] = []

    # 附件
    attachments: List[AttachmentFile] = []

    # 状态
    status: str = "draft"  # draft(草稿)/configured(已配置)/calculated(已计算)

    # 调差结果
    adjustment_result: Optional[Dict] = None

    # 时间戳
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str
    contract_no: str = ""
    rule_id: Optional[str] = None
    rule_name: str = ""
    base_price_source: str = "造价信息"


class UpdateProjectRequest(BaseModel):
    """更新项目请求"""
    name: Optional[str] = None
    contract_no: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    base_price_source: Optional[str] = None
    construction_start: Optional[str] = None
    construction_end: Optional[str] = None
    status: Optional[str] = None


class ProjectMaterialRequest(BaseModel):
    """项目材料请求"""
    project_id: str
    materials: List[MaterialItem]


class AttachmentRequest(BaseModel):
    """附件请求"""
    project_id: str
    file: AttachmentFile


# 预设的调差项目数据(用于演示)
DEMO_PROJECTS = [
    {
        "id": "demo_001",
        "name": "XX商业综合体项目",
        "contract_no": "HT2024001",
        "rule_name": "青特地产",
        "base_price_source": "造价信息",
        "status": "calculated",
        "materials": [
            {"name": "钢筋HRB400", "spec": "Φ12", "unit": "t", "quantity": 500, "bid_price": 4200, "base_price": 4460},
            {"name": "钢筋HRB400", "spec": "Φ25", "unit": "t", "quantity": 800, "bid_price": 4100, "base_price": 4390},
            {"name": "商品混凝土", "spec": "C30", "unit": "m³", "quantity": 2000, "bid_price": 550, "base_price": 480},
        ],
        "created_at": "2024-03-01T10:00:00",
    },
    {
        "id": "demo_002",
        "name": "YY住宅小区项目",
        "contract_no": "HT2024002",
        "rule_name": "龙湖集团",
        "base_price_source": "钢铁网",
        "status": "draft",
        "materials": [],
        "created_at": "2024-03-15T14:30:00",
    },
]