"""
造价管理 - 参考价格数据模型
用于存储官方发布的钢筋、混凝土等造价参考价
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class CostReferencePrice(BaseModel):
    """造价参考价"""
    id: Optional[int] = None
    source: str = "烟台工程建设标准造价管理"  # 价格来源
    period: str = "2024年第一季度"  # 周期
    category: str  # 分类: 钢筋/混凝土/型钢等
    code: Optional[str] = None  # 编码
    name: str  # 名称
    spec: Optional[str] = None  # 规格
    unit: str  # 单位
    unit_price: float  # 含税单价(元)
    tax_rate: float = 13.0  # 增值税率%
    notes: Optional[str] = None  # 备注
    created_at: Optional[str] = None


class ConcretePrice(BaseModel):
    """混凝土价格"""
    id: Optional[int] = None
    source: str = "烟台工程建设标准造价管理"
    period: str = "2024年第一季度"
    brand: str  # 品牌/厂商
    grade: str  # 强度等级 (C15-C60)
    pump_price: float  # 泵送价格 (元/立方米)
    non_pump_price: float  # 非泵送价格 (元/立方米)
    notes: Optional[str] = None


class MortarPrice(BaseModel):
    """砂浆价格"""
    id: Optional[int] = None
    source: str = "烟台工程建设标准造价管理"
    period: str = "2024年第一季度"
    name: str  # 名称
    code: Optional[str] = None  # 型号代码
    unit_price: float  # 单价 (元/吨或元/立方米)
    unit: str  # 单位
    notes: Optional[str] = None


# ============================================================
# 预设数据 - 2024年第一季度烟台造价管理数据
# ============================================================

STEEL_REBAR_PRICES = [
    # 编码, 名称, 规格, 单位, 含税单价, 增值税率
    {"code": "01010001", "name": "钢筋HPB300Φ6.5", "spec": "Φ6.5", "unit": "t", "unit_price": 4893.00, "tax_rate": 13.0},
    {"code": "01010005", "name": "钢筋HPB300Φ8", "spec": "Φ8", "unit": "t", "unit_price": 4536.00, "tax_rate": 13.0},
    {"code": "01010007", "name": "钢筋HPB300Φ10", "spec": "Φ10", "unit": "t", "unit_price": 4515.00, "tax_rate": 13.0},
    {"code": "01010011", "name": "钢筋HPB300Φ12", "spec": "Φ12", "unit": "t", "unit_price": 4460.00, "tax_rate": 13.0},
    {"code": "01010013", "name": "钢筋HPB300>Φ12", "spec": ">Φ12", "unit": "t", "unit_price": 4660.00, "tax_rate": 13.0},
    {"code": "01010021", "name": "钢筋HRB400Φ6", "spec": "Φ6", "unit": "t", "unit_price": 4810.00, "tax_rate": 13.0},
    {"code": "01010023", "name": "钢筋HRB400Φ8", "spec": "Φ8", "unit": "t", "unit_price": 4590.00, "tax_rate": 13.0},
    {"code": "01010025", "name": "钢筋HRB400Φ10", "spec": "Φ10", "unit": "t", "unit_price": 4560.00, "tax_rate": 13.0},
    {"code": "01010027", "name": "钢筋HRB400Φ12", "spec": "Φ12", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    {"code": "01010029", "name": "钢筋HRB400Φ14", "spec": "Φ14", "unit": "t", "unit_price": 4420.00, "tax_rate": 13.0},
    {"code": "01010031", "name": "钢筋HRB400Φ16", "spec": "Φ16", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010033", "name": "钢筋HRB400Φ18", "spec": "Φ18", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010035", "name": "钢筋HRB400Φ20", "spec": "Φ20", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010037", "name": "钢筋HRB400Φ22", "spec": "Φ22", "unit": "t", "unit_price": 4330.00, "tax_rate": 13.0},
    {"code": "01010039", "name": "钢筋HRB400Φ25", "spec": "Φ25", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010041", "name": "钢筋HRB400Φ28", "spec": "Φ28", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    {"code": "01010043", "name": "钢筋HRB400Φ32", "spec": "Φ32", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    {"code": "01010049", "name": "钢筋HRB500≤Φ18", "spec": "≤Φ18", "unit": "t", "unit_price": 4640.00, "tax_rate": 13.0},
    {"code": "01010051", "name": "钢筋HRB500≤Φ25", "spec": "≤Φ25", "unit": "t", "unit_price": 4640.00, "tax_rate": 13.0},
    {"code": "01010053", "name": "钢筋HRB500>Φ25", "spec": ">Φ25", "unit": "t", "unit_price": 4700.00, "tax_rate": 13.0},
    # 抗震螺纹钢
    {"code": "01010061", "name": "抗震螺纹钢HRB400EΦ6", "spec": "Φ6", "unit": "t", "unit_price": 4810.00, "tax_rate": 13.0},
    {"code": "01010063", "name": "抗震螺纹钢HRB400EΦ8", "spec": "Φ8", "unit": "t", "unit_price": 4590.00, "tax_rate": 13.0},
    {"code": "01010065", "name": "抗震螺纹钢HRB400EΦ10", "spec": "Φ10", "unit": "t", "unit_price": 4560.00, "tax_rate": 13.0},
    {"code": "01010067", "name": "抗震螺纹钢HRB400EΦ12", "spec": "Φ12", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    {"code": "01010069", "name": "抗震螺纹钢HRB400EΦ14", "spec": "Φ14", "unit": "t", "unit_price": 4420.00, "tax_rate": 13.0},
    {"code": "01010071", "name": "抗震螺纹钢HRB400EΦ16", "spec": "Φ16", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010073", "name": "抗震螺纹钢HRB400EΦ18", "spec": "Φ18", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010075", "name": "抗震螺纹钢HRB400EΦ20", "spec": "Φ20", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010077", "name": "抗震螺纹钢HRB400EΦ22", "spec": "Φ22", "unit": "t", "unit_price": 4330.00, "tax_rate": 13.0},
    {"code": "01010079", "name": "抗震螺纹钢HRB400EΦ25", "spec": "Φ25", "unit": "t", "unit_price": 4390.00, "tax_rate": 13.0},
    {"code": "01010081", "name": "抗震螺纹钢HRB400EΦ28", "spec": "Φ28", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    {"code": "01010083", "name": "抗震螺纹钢HRB400EΦ32", "spec": "Φ32", "unit": "t", "unit_price": 4450.00, "tax_rate": 13.0},
    # CRB600H钢筋
    {"code": "01010091", "name": "钢筋CRB600H8", "spec": "Φ8", "unit": "t", "unit_price": 5790.00, "tax_rate": 13.0},
    {"code": "01010093", "name": "钢筋CRB600H10", "spec": "Φ10", "unit": "t", "unit_price": 5940.00, "tax_rate": 13.0},
    {"code": "01010095", "name": "钢筋CRB600H12", "spec": "Φ12", "unit": "t", "unit_price": 5850.00, "tax_rate": 13.0},
    # 冷轧带肋钢筋
    {"code": "01010113", "name": "冷轧带肋钢筋Φ6", "spec": "Φ6", "unit": "t", "unit_price": 4790.00, "tax_rate": 13.0},
    {"code": "01010115", "name": "冷轧带肋钢筋Φ8", "spec": "Φ8", "unit": "t", "unit_price": 4590.00, "tax_rate": 13.0},
    {"code": "01010117", "name": "冷轧带肋钢筋Φ10", "spec": "Φ10", "unit": "t", "unit_price": 4590.00, "tax_rate": 13.0},
    # 预应力螺纹钢筋
    {"code": "01010163", "name": "预应力螺纹钢筋Φ25", "spec": "Φ25", "unit": "t", "unit_price": 5320.00, "tax_rate": 13.0},
    {"code": "01010167", "name": "预应力螺纹钢筋Φ32", "spec": "Φ32", "unit": "t", "unit_price": 5390.00, "tax_rate": 13.0},
    {"code": "01010171", "name": "预应力螺纹钢筋Φ40", "spec": "Φ40", "unit": "t", "unit_price": 5390.00, "tax_rate": 13.0},
    # 钢绞线
    {"code": "01070001", "name": "钢绞线(综合)", "spec": "综合", "unit": "t", "unit_price": 6650.00, "tax_rate": 13.0},
    {"code": "01070003", "name": "钢绞线", "spec": "Φ7", "unit": "t", "unit_price": 6650.00, "tax_rate": 13.0},
]

CONCRETE_PRICES = [
    # 强度等级, 泵送价格, 非泵送价格
    {"grade": "C15", "pump_price": 450, "non_pump_price": 440},
    {"grade": "C20", "pump_price": 460, "non_pump_price": 450},
    {"grade": "C25", "pump_price": 470, "non_pump_price": 460},
    {"grade": "C30", "pump_price": 480, "non_pump_price": 470},
    {"grade": "C35", "pump_price": 490, "non_pump_price": 480},
    {"grade": "C40", "pump_price": 500, "non_pump_price": 490},
    {"grade": "C45", "pump_price": 530, "non_pump_price": 520},
    {"grade": "C50", "pump_price": 560, "non_pump_price": 550},
    {"grade": "C55", "pump_price": 610, "non_pump_price": 600},
    {"grade": "C60", "pump_price": 650, "non_pump_price": 640},
]

MORTAR_PRICES = [
    {"name": "刚性抗裂防水砂浆", "code": "DWS", "unit_price": 2100, "unit": "元/吨"},
    {"name": "聚合物水泥抗裂防水砂浆", "code": "DWS", "unit_price": 4300, "unit": "元/吨"},
    {"name": "渗透结晶防水材料", "code": "CCCW", "unit_price": 8500, "unit": "元/吨"},
    {"name": "聚合物保温界面粘结砂浆", "code": "DEA", "unit_price": 2100, "unit": "元/吨"},
    {"name": "聚合物抗裂抹面砂浆", "code": "DBI", "unit_price": 2100, "unit": "元/吨"},
    {"name": "外墙柔性抗裂腻子", "code": None, "unit_price": 4700, "unit": "元/吨"},
    {"name": "陶瓷墙地砖胶黏剂", "code": "DTA", "unit_price": 1900, "unit": "元/吨"},
    {"name": "瓷砖勾缝剂", "code": "CG", "unit_price": 2100, "unit": "元/吨"},
    {"name": "界面砂浆", "code": None, "unit_price": 1900, "unit": "元/吨"},
    {"name": "保温砂浆", "code": None, "unit_price": 1900, "unit": "元/吨"},
    {"name": "无机保温砂浆", "code": None, "unit_price": 1900, "unit": "元/吨"},
    {"name": "玻化微珠保温砂浆", "code": "ZJ11", "unit_price": 1500, "unit": "元/吨"},
    {"name": "轻质抹灰石膏", "code": None, "unit_price": 1500, "unit": "元/吨"},
]