"""
公式工厂 FormulaEngine
实现5种调差公式模板
遵循《地产项目材料调差规则_AI可执行配置规范》v1.0
"""

import logging
from typing import Optional, Tuple

from pydantic import BaseModel, Field
from web.backend.models.adjustment_rules import RiskType, RiskConfig

logger = logging.getLogger(__name__)


# ============================================================
# 数据输入模型
# ============================================================

class FormulaInput(BaseModel):
    """公式计算输入参数"""
    material_name: str = Field(..., description="材料名称")
    quantity: float = Field(..., gt=0, description="工程量")
    unit: str = Field(..., description="单位")
    base_price: float = Field(..., ge=0, description="基准价")
    period_avg_price: float = Field(..., ge=0, description="施工期均价（指导价）")
    risk_config: Optional[dict] = Field(default=None, description="风险幅度配置")
    tax_rate: float = Field(default=9.0, ge=0, le=100, description="税率%")


# ============================================================
# 公式类型枚举（映射到中文名称）
# ============================================================

class FormulaType:
    """公式类型字符串常量"""
    STANDARD_THREE_STAGE = "standard_three_stage"           # 标准三段式
    LONGHU_VAT_CONVERSION = "longhu_vat_conversion"         # 龙湖增值税率换算法
    RATIO_ADJUSTMENT = "ratio_adjustment"                   # 豪森比例调差法
    COST_INFO_ADJUSTMENT = "cost_info_adjustment"          # 造价信息调整法
    NO_RISK = "no_risk"                                     # 无风险幅度（全额调差）


# ============================================================
# 公式工厂
# ============================================================

class FormulaEngine:
    """
    调差公式工厂
    实现5种调差公式模板，返回(调整金额, 计算公式说明)
    """

    def __init__(self):
        """初始化公式引擎"""
        logger.info("[FormulaEngine] 公式引擎初始化")

    def calculate(
        self,
        formula_type: str,
        input_data: FormulaInput
    ) -> Tuple[float, str]:
        """
        根据公式类型计算调整金额

        Args:
            formula_type: 公式类型标识符
            input_data: 公式输入参数

        Returns:
            Tuple[float, str]: (调整金额, 计算公式说明)
        """
        logger.info(
            f"[FormulaEngine.calculate] 执行计算 | "
            f"formula_type={formula_type} | "
            f"material={input_data.material_name} | "
            f"quantity={input_data.quantity} | "
            f"base_price={input_data.base_price} | "
            f"period_avg={input_data.period_avg_price}"
        )

        try:
            if formula_type == FormulaType.STANDARD_THREE_STAGE:
                return self._standard_three_stage(input_data)
            elif formula_type == FormulaType.LONGHU_VAT_CONVERSION:
                return self._longhu_vat_conversion(input_data)
            elif formula_type == FormulaType.RATIO_ADJUSTMENT:
                return self._ratio_adjustment(input_data)
            elif formula_type == FormulaType.COST_INFO_ADJUSTMENT:
                return self._cost_info_adjustment(input_data)
            elif formula_type == FormulaType.NO_RISK:
                return self._no_risk(input_data)
            else:
                logger.error(f"[FormulaEngine.calculate] 不支持的公式类型 | type={formula_type}")
                raise ValueError(f"不支持的公式类型: {formula_type}")

        except Exception as e:
            logger.error(
                f"[FormulaEngine.calculate] 计算失败 | "
                f"formula_type={formula_type} | "
                f"error={type(e).__name__}: {e}",
                exc_info=True
            )
            raise

    # ============================================================
    # 1. 标准三段式 (standard_three_stage)
    # ============================================================

    def _standard_three_stage(self, input_data: FormulaInput) -> Tuple[float, str]:
        """
        标准三段式调差公式

        涨幅超出：调整金额 = 工程量 × (施工期均价 - 基准价 × (1 + 风险幅度%))
        跌幅超出：调整金额 = 工程量 × (施工期均价 - 基准价 × (1 - 风险幅度%))
        风险幅度内：不调差
        """
        logger.debug(f"[_standard_three_stage] 计算标准三段式 | material={input_data.material_name}")

        # 解析风险幅度
        risk_value, risk_percentage = self._parse_risk_config(input_data.risk_config)

        if risk_percentage is None or risk_value == 0:
            # 无风险幅度配置时，全额调差（0%风险幅度）
            adjustment = input_data.quantity * (input_data.period_avg_price - input_data.base_price)
            formula = (
                f"标准三段式(无风险幅度全额调差)| "
                f"调整金额 = {input_data.quantity} × ({input_data.period_avg_price} - {input_data.base_price})"
                f" = {adjustment:.2f}元"
            )
            logger.info(f"[_standard_three_stage] 无风险幅度全额调差 | adjustment={adjustment:.2f}")
            return adjustment, formula

        # 计算上下限
        upper_limit = input_data.base_price * (1 + risk_value / 100)
        lower_limit = input_data.base_price * (1 - risk_value / 100)

        price_diff = input_data.period_avg_price - input_data.base_price
        adjustment = 0.0
        formula = ""

        if input_data.period_avg_price > upper_limit:
            # 涨幅超出
            adjustment = input_data.quantity * (input_data.period_avg_price - upper_limit)
            formula = (
                f"标准三段式(涨幅超出)| "
                f"上限={input_data.base_price}×(1+{risk_value}%)={upper_limit:.2f} | "
                f"调整金额 = {input_data.quantity} × ({input_data.period_avg_price} - {upper_limit:.2f})"
                f" = {adjustment:.2f}元"
            )
            logger.info(f"[_standard_three_stage] 涨幅超出 | upper_limit={upper_limit:.2f} | adjustment={adjustment:.2f}")
        elif input_data.period_avg_price < lower_limit:
            # 跌幅超出
            adjustment = input_data.quantity * (input_data.period_avg_price - lower_limit)
            formula = (
                f"标准三段式(跌幅超出)| "
                f"下限={input_data.base_price}×(1-{risk_value}%)={lower_limit:.2f} | "
                f"调整金额 = {input_data.quantity} × ({input_data.period_avg_price} - {lower_limit:.2f})"
                f" = {adjustment:.2f}元"
            )
            logger.info(f"[_standard_three_stage] 跌幅超出 | lower_limit={lower_limit:.2f} | adjustment={adjustment:.2f}")
        else:
            # 风险幅度内，不调差
            formula = (
                f"标准三段式(风险幅度内)| "
                f"施工期均价{input_data.period_avg_price}在[{lower_limit:.2f}, {upper_limit:.2f}]范围内，不调差"
            )
            logger.info(f"[_standard_three_stage] 风险幅度内不调差 | period_avg={input_data.period_avg_price}")

        return adjustment, formula

    # ============================================================
    # 2. 龙湖增值税率换算法 (longhu_vat_conversion)
    # ============================================================

    def _longhu_vat_conversion(self, input_data: FormulaInput) -> Tuple[float, str]:
        """
        龙湖增值税率换算法

        钢筋（0%风险幅度）：调整金额 = {工程量 × (指导价 - 基准价)} / (1 + 13%) × (1 + 9%)
        混凝土（±3%风险幅度）：调整金额 = {工程量 × (指导价 - 基准价 × (1 ± 3%))} / 1.13 × 1.09

        特点：承包人采购钢材可取得13%增值税专用发票，发包人支付时应换算为合同税率9%
        """
        logger.debug(f"[_longhu_vat_conversion] 计算龙湖公式 | material={input_data.material_name}")

        VAT_INPUT = 13.0   # 采购发票税率
        VAT_OUTPUT = 9.0   # 合同约定税率

        # 解析风险幅度
        risk_value, risk_percentage = self._parse_risk_config(input_data.risk_config)

        # 判断是否有风险幅度（钢筋0%全额调差，混凝土±3%）
        if risk_percentage == RiskType.NONE or (risk_percentage == RiskType.PERCENTAGE and risk_value == 0):
            # 钢筋：0%风险幅度，全额调差
            price_diff = input_data.period_avg_price - input_data.base_price
            adjustment = (input_data.quantity * price_diff) / (1 + VAT_INPUT / 100) * (1 + VAT_OUTPUT / 100)
            formula = (
                f"龙湖增值税率换算法(钢筋0%全额调差)| "
                f"调整金额 = [{input_data.quantity} × ({input_data.period_avg_price} - {input_data.base_price})]"
                f" / (1+{VAT_INPUT}%) × (1+{VAT_OUTPUT}%)"
                f" = {adjustment:.2f}元"
            )
            logger.info(f"[_longhu_vat_conversion] 钢筋全额调差 | adjustment={adjustment:.2f}")
        else:
            # 混凝土：有风险幅度
            upper_limit = input_data.base_price * (1 + risk_value / 100)
            lower_limit = input_data.base_price * (1 - risk_value / 100)

            if input_data.period_avg_price > upper_limit:
                # 涨幅超出
                price_diff = input_data.period_avg_price - upper_limit
                adjustment = (input_data.quantity * price_diff) / (1 + VAT_INPUT / 100) * (1 + VAT_OUTPUT / 100)
                formula = (
                    f"龙湖增值税率换算法(混凝土涨幅)| "
                    f"上限={input_data.base_price}×(1+{risk_value}%)={upper_limit:.2f} | "
                    f"调整金额 = [{input_data.quantity} × ({input_data.period_avg_price} - {upper_limit:.2f})]"
                    f" / (1+{VAT_INPUT}%) × (1+{VAT_OUTPUT}%)"
                    f" = {adjustment:.2f}元"
                )
                logger.info(f"[_longhu_vat_conversion] 混凝土涨幅 | upper_limit={upper_limit:.2f} | adjustment={adjustment:.2f}")
            elif input_data.period_avg_price < lower_limit:
                # 跌幅超出
                price_diff = input_data.period_avg_price - lower_limit
                adjustment = (input_data.quantity * price_diff) / (1 + VAT_INPUT / 100) * (1 + VAT_OUTPUT / 100)
                formula = (
                    f"龙湖增值税率换算法(混凝土跌幅)| "
                    f"下限={input_data.base_price}×(1-{risk_value}%)={lower_limit:.2f} | "
                    f"调整金额 = [{input_data.quantity} × ({input_data.period_avg_price} - {lower_limit:.2f})]"
                    f" / (1+{VAT_INPUT}%) × (1+{VAT_OUTPUT}%)"
                    f" = {adjustment:.2f}元"
                )
                logger.info(f"[_longhu_vat_conversion] 混凝土跌幅 | lower_limit={lower_limit:.2f} | adjustment={adjustment:.2f}")
            else:
                # 风险幅度内，不调差
                adjustment = 0.0
                formula = (
                    f"龙湖增值税率换算法(风险幅度内)| "
                    f"施工期均价{input_data.period_avg_price}在[{lower_limit:.2f}, {upper_limit:.2f}]范围内，不调差"
                )
                logger.info(f"[_longhu_vat_conversion] 混凝土风险幅度内不调差")

        return adjustment, formula

    # ============================================================
    # 3. 豪森比例调差法 (ratio_adjustment)
    # ============================================================

    def _ratio_adjustment(self, input_data: FormulaInput) -> Tuple[float, str]:
        """
        豪森比例调差法

        涨幅：调整金额 = 基准价 × (Pi/P0 - (1 + 风险幅度)) × 工程量
        跌幅：调整金额 = 基准价 × (Pi/P0 - (1 - 风险幅度)) × 工程量

        电缆特殊规则：铜价波动 ≤ 2000元/吨不调差
        """
        logger.debug(f"[_ratio_adjustment] 计算豪森比例调差 | material={input_data.material_name}")

        # 解析风险幅度
        risk_value, risk_percentage = self._parse_risk_config(input_data.risk_config)

        # 电缆特殊规则：铜价波动 ≤ 2000元/吨不调差
        if input_data.material_name == "电缆" and risk_percentage == RiskType.FIXED:
            copper_fluctuation = abs(input_data.period_avg_price - input_data.base_price)
            if copper_fluctuation <= risk_value:
                formula = (
                    f"豪森比例调差法(电缆特殊规则)| "
                    f"铜价波动={copper_fluctuation:.2f}元/吨 ≤ {risk_value}元/吨阈值，不调差"
                )
                logger.info(f"[_ratio_adjustment] 电缆铜价波动在阈值内不调差 | fluctuation={copper_fluctuation:.2f}")
                return 0.0, formula

        # 计算价格比例
        price_ratio = input_data.period_avg_price / input_data.base_price if input_data.base_price != 0 else 0

        if risk_percentage == RiskType.PERCENTAGE:
            # 百分比风险幅度
            upper_ratio = 1 + risk_value / 100
            lower_ratio = 1 - risk_value / 100

            if price_ratio > upper_ratio:
                # 涨幅超出
                adjustment = input_data.base_price * (price_ratio - upper_ratio) * input_data.quantity
                formula = (
                    f"豪森比例调差法(涨幅超出)| "
                    f"Pi/P0={price_ratio:.4f} > {upper_ratio:.4f} | "
                    f"调整金额 = {input_data.base_price} × ({price_ratio:.4f} - {upper_ratio:.4f}) × {input_data.quantity}"
                    f" = {adjustment:.2f}元"
                )
                logger.info(f"[_ratio_adjustment] 涨幅超出 | ratio={price_ratio:.4f} | adjustment={adjustment:.2f}")
            elif price_ratio < lower_ratio:
                # 跌幅超出
                adjustment = input_data.base_price * (price_ratio - lower_ratio) * input_data.quantity
                formula = (
                    f"豪森比例调差法(跌幅超出)| "
                    f"Pi/P0={price_ratio:.4f} < {lower_ratio:.4f} | "
                    f"调整金额 = {input_data.base_price} × ({price_ratio:.4f} - {lower_ratio:.4f}) × {input_data.quantity}"
                    f" = {adjustment:.2f}元"
                )
                logger.info(f"[_ratio_adjustment] 跌幅超出 | ratio={price_ratio:.4f} | adjustment={adjustment:.2f}")
            else:
                # 风险幅度内，不调差
                adjustment = 0.0
                formula = (
                    f"豪森比例调差法(风险幅度内)| "
                    f"Pi/P0={price_ratio:.4f}在[{lower_ratio:.4f}, {upper_ratio:.4f}]范围内，不调差"
                )
                logger.info(f"[_ratio_adjustment] 风险幅度内不调差 | ratio={price_ratio:.4f}")
        else:
            # 无风险幅度，按比例全额调差
            adjustment = input_data.base_price * (price_ratio - 1) * input_data.quantity
            formula = (
                f"豪森比例调差法(无风险幅度全额调差)| "
                f"Pi/P0={price_ratio:.4f} | "
                f"调整金额 = {input_data.base_price} × ({price_ratio:.4f} - 1) × {input_data.quantity}"
                f" = {adjustment:.2f}元"
            )
            logger.info(f"[_ratio_adjustment] 无风险幅度全额调差 | adjustment={adjustment:.2f}")

        return adjustment, formula

    # ============================================================
    # 4. 造价信息调整法 (cost_info_adjustment)
    # ============================================================

    def _cost_info_adjustment(self, input_data: FormulaInput) -> Tuple[float, str]:
        """
        造价信息调整法

        与标准三段式相同逻辑
        """
        logger.debug(f"[_cost_info_adjustment] 计算造价信息调整 | material={input_data.material_name}")

        adjustment, formula = self._standard_three_stage(input_data)

        # 替换公式名称
        formula = formula.replace("标准三段式", "造价信息调整法")

        logger.info(f"[_cost_info_adjustment] 造价信息调整计算完成 | adjustment={adjustment:.2f}")
        return adjustment, formula

    # ============================================================
    # 5. 无风险幅度 (no_risk)
    # ============================================================

    def _no_risk(self, input_data: FormulaInput) -> Tuple[float, str]:
        """
        无风险幅度公式

        全额调差：调整金额 = 工程量 × (施工期均价 - 基准价)
        """
        logger.debug(f"[_no_risk] 计算无风险幅度全额调差 | material={input_data.material_name}")

        price_diff = input_data.period_avg_price - input_data.base_price
        adjustment = input_data.quantity * price_diff

        formula = (
            f"无风险幅度全额调差| "
            f"调整金额 = {input_data.quantity} × ({input_data.period_avg_price} - {input_data.base_price})"
            f" = {adjustment:.2f}元"
        )

        logger.info(
            f"[_no_risk] 全额调差完成 | "
            f"price_diff={price_diff:.2f} | "
            f"adjustment={adjustment:.2f}"
        )

        return adjustment, formula

    # ============================================================
    # 辅助方法
    # ============================================================

    def _parse_risk_config(
        self,
        risk_config: Optional[dict]
    ) -> Tuple[float, Optional[RiskType]]:
        """
        解析风险幅度配置

        Args:
            risk_config: 风险配置字典 {"类型": "百分比"/"固定金额"/"无", "值": 3.0}

        Returns:
            Tuple[float, Optional[RiskType]]: (风险值, 风险类型)
        """
        if risk_config is None:
            return 0.0, None

        try:
            risk_type_str = risk_config.get("类型", "无")
            risk_value = risk_config.get("值", 0.0)

            # 映射到 RiskType 枚举
            if risk_type_str in ("百分比", "percent", "PERCENTAGE"):
                return risk_value, RiskType.PERCENTAGE
            elif risk_type_str in ("固定金额", "fixed", "FIXED"):
                return risk_value, RiskType.FIXED
            else:
                return risk_value, RiskType.NONE

        except Exception as e:
            logger.warning(f"[_parse_risk_config] 解析风险配置失败 | config={risk_config} | error={e}")
            return 0.0, RiskType.NONE