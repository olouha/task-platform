"""
调差计算引擎 - 支持多部位分时段计算
遵循规则：
1. 依据项目既定调价文件判定调价时间区间
2. 楼栋/部位时间段可能不同
3. 每个部位单独匹配自身实际施工时段，各部位调差时间互不通用
4. 单部位公式：部位钢筋用量 × 分别调差的金额 = 单部位调差金额
5. 全部部位调差金额相加，汇总得出钢筋整体调差总额
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from models.adjustment_rules import (
    AdjustmentRuleConfig, AdjustmentDetail, CalculationResult,
    RiskConfig, RiskType
)


@dataclass
class PriceData:
    """价格数据"""
    date: str
    price: float
    source: str = ""


@dataclass
class QuantityData:
    """工程量数据（含部位和时段信息）"""
    material_name: str
    quantity: float
    unit: str
    phase: str = "整体"
    location: str = ""  # 楼栋/部位名称
    start_date: Optional[str] = None
    施工结束日期: Optional[str] = None


@dataclass
class CalculationInput:
    """计算输入数据"""
    base_prices: Dict[str, float]
    period_prices: Dict[str, List[PriceData]]
    quantities: List[QuantityData]


@dataclass
class LocationPeriod:
    """部位施工时段"""
    名称: str
    施工开始日期: str
    施工结束日期: str


class AdjustmentEngineV2:
    """调差计算引擎 - 多部位分时段计算"""

    def __init__(self, config: AdjustmentRuleConfig):
        self.config = config

    def calculate(self, input_data: CalculationInput) -> CalculationResult:
        """
        按部位/楼栋分别计算调差

        计算逻辑：
        1. 按部位分组工程量
        2. 每个部位使用自己的施工时间段计算均价
        3. 各部位独立计算后汇总
        """
        details = []

        # 按部位分组
        location_groups: Dict[str, List[QuantityData]] = {}
        for qty in input_data.quantities:
            loc = qty.location or "整体"
            if loc not in location_groups:
                location_groups[loc] = []
            location_groups[loc].append(qty)

        # 获取基准日期
        base_date = getattr(self.config, '基准日期', None)

        # 每个部位分别计算
        for location_name, quantities in location_groups.items():
            # 确定该部位的施工时间段
            start_date = quantities[0].start_date if quantities else None
            end_date = quantities[0].施工结束日期 if quantities else None

            # 对每种材料计算
            for qty in quantities:
                detail = self._calculate_single(
                    material_name=qty.material_name,
                    quantity=qty.quantity,
                    unit=qty.unit,
                    base_price=input_data.base_prices.get(qty.material_name, 0),
                    start_date=start_date,
                    end_date=end_date,
                    phase=qty.phase,
                    location=location_name,
                    base_date=base_date
                )
                details.append(detail)

        # 汇总
        total = sum(d.含税调整金额 for d in details)

        return CalculationResult(
            项目名称=self.config.项目名称,
            调差总金额=round(total, 2),
            明细=details,
            使用规则版本="v2.0",
            计算时间=datetime.now()
        )

    def _calculate_single(
        self,
        material_name: str,
        quantity: float,
        unit: str,
        base_price: float,
        start_date: Optional[str],
        end_date: Optional[str],
        phase: str,
        location: str,
        base_date: Optional[str]
    ) -> AdjustmentDetail:
        """计算单个部位的调差"""
        # 获取风险幅度
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.PERCENTAGE, 值=3))

        # 获取施工期均价（按部位时间段）
        period_avg = 0
        if start_date and end_date:
            period_avg = self._get_period_avg(material_name, start_date, end_date)

        # 获取基准价
        if base_price == 0 and base_date:
            base_price = self._get_base_price(material_name, base_date)

        # 判断是否超幅度
        is_over = False
        is_rising = True
        effective_diff = 0

        if base_price > 0:
            upper = base_price * (1 + risk_config.值 / 100)
            lower = base_price * (1 - risk_config.值 / 100)

            if period_avg > upper:
                is_over = True
                is_rising = True
                effective_diff = period_avg - upper
            elif period_avg < lower:
                is_over = True
                is_rising = False
                effective_diff = period_avg - lower

        # 计算调差金额
        adjustment_amount = quantity * effective_diff
        tax_rate = self.config.税率 / 100
        total_with_tax = adjustment_amount * (1 + tax_rate)

        # 风险幅度显示
        if risk_config.类型 == RiskType.PERCENTAGE:
            risk_display = f"±{risk_config.值}%"
        elif risk_config.类型 == RiskType.FIXED:
            risk_display = f"±{risk_config.值}元"
        else:
            risk_display = "0%全额调差"

        # 构建公式
        if is_over:
            formula = f"{quantity} × [{period_avg:.2f} - {base_price:.2f}] = {adjustment_amount:.2f}"
        else:
            formula = f"幅度内不调差 ({base_price:.2f} ±{risk_config.值}%)"

        return AdjustmentDetail(
            材料名称=material_name,
            阶段=phase,
            工程量=quantity,
            工程量单位=unit,
            基准价=base_price,
            施工均价=round(period_avg, 2),
            风险幅度=risk_display,
            是否超幅=is_over,
            调整单价=round(effective_diff, 2),
            调整金额=round(adjustment_amount, 2),
            税率=self.config.税率,
            含税调整金额=round(total_with_tax, 2),
            计算公式=formula,
            计算依据=f"部位:{location}|时段:{start_date or '?'}~{end_date or '?'}"
        )

    def _get_period_avg(self, material_name: str, start_date: str, end_date: str) -> float:
        """获取指定时间段的均价"""
        prices = self.config.调差项目  # 简化实现
        all_prices = getattr(self, '_period_prices', {}).get(material_name, [])

        filtered = [p for p in all_prices if start_date <= p.date <= end_date]

        if filtered:
            return sum(p.price for p in filtered) / len(filtered)
        return 0

    def _get_base_price(self, material_name: str, base_date: str) -> float:
        """获取基准日期的价格"""
        all_prices = getattr(self, '_period_prices', {}).get(material_name, [])

        for p in all_prices:
            if p.date == base_date:
                return p.price

        # 找不到则返回0
        return 0
# 向后兼容别名
AdjustmentEngine = AdjustmentEngineV2
