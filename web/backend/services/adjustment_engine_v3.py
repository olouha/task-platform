"""
统一调差计算引擎 AdjustmentEngineV3
遵循《地产项目材料调差规则_AI可执行配置规范》v3.0

7步标准流程：
Step 1: 校验配置 (_validate_config)
Step 2: 取基准价 (_fetch_base_prices)
Step 3: 取施工期均价 (_fetch_period_prices)
Step 3.5: 价格数据校验 (_validate_price_data)
Step 4: 判断是否超风险幅度 (_check_risk_threshold)
Step 5: 代入公式计算 (_calculate_adjustment)
Step 5.5: 分阶段汇总 (_summarize_by_phase)
Step 6: 输出结果 (_format_output)

核心特性：
- 整合 FormulaEngine 和 PriceService
- 支持多部位分时段计算（各部位独立计算施工期均价）
- 支持5种调差公式模板
- 完整的价格数据校验
- 分阶段汇总
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from web.backend.services.formula_engine import FormulaEngine, FormulaInput, FormulaType as FormulaTypeStr
from web.backend.services.price_service import PriceService, PriceData as PSPriceData
from web.backend.models.adjustment_rules import (
    AdjustmentRuleConfig,
    AdjustmentDetail as ModelAdjustmentDetail,
    CalculationResult as ModelCalculationResult,
    RiskConfig,
    RiskType,
    FormulaType,
    NegativeHandling,
    PhaseType,
    HolidayHandling,
    PriceRounding,
)

logger = logging.getLogger(__name__)


# ============================================================
# 数据类定义（v3.0 标准输出格式）
# ============================================================

@dataclass
class PriceData:
    """价格数据"""
    date: str           # YYYY-MM-DD 格式
    price: float
    source: str = ""    # 数据来源


@dataclass
class QuantityData:
    """工程量数据（含部位和时段信息）"""
    material_name: str
    quantity: float
    unit: str = "t"
    phase: str = "整体"
    location: str = ""   # 楼栋/部位名称
    start_date: Optional[str] = None  # 施工开始日期
    end_date: Optional[str] = None    # 施工结束日期


@dataclass
class CalculationInput:
    """计算输入数据"""
    base_prices: Dict[str, float]              # 材料名 -> 基准价
    period_prices: Dict[str, List[PriceData]] # 材料名 -> 价格列表
    quantities: List[QuantityData]            # 工程量列表


@dataclass
class AdjustmentDetail:
    """调差明细 - v3.0 输出格式"""
    材料名称: str
    阶段: str = "整体"
    部位: str = ""
    工程量: float = 0
    工程量单位: str = "t"
    基准价: float = 0
    施工均价: float = 0
    风险幅度: str = ""
    是否超幅: bool = False
    调整单价: float = 0
    调整金额: float = 0
    税率: float = 9
    含税调整金额: float = 0
    计算公式: str = ""
    计算依据: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "材料名称": self.材料名称,
            "阶段": self.阶段,
            "部位": self.部位,
            "工程量": self.工程量,
            "工程量单位": self.工程量单位,
            "基准价": self.基准价,
            "施工均价": self.施工均价,
            "风险幅度": self.风险幅度,
            "是否超幅": self.是否超幅,
            "调整单价": self.调整单价,
            "调整金额": self.调整金额,
            "税率": self.税率,
            "含税调整金额": self.含税调整金额,
            "计算公式": self.计算公式,
            "计算依据": self.计算依据,
        }


@dataclass
class CalculationResult:
    """调差计算结果 - v3.0 输出格式"""
    项目名称: str
    调差总金额: float = 0
    不含税总金额: float = 0
    税金: float = 0
    明细: List[AdjustmentDetail] = field(default_factory=list)
    阶段汇总: List[Dict[str, Any]] = field(default_factory=list)
    价格校验: Optional[Dict[str, Any]] = None
    使用规则版本: str = "v3.0"
    计算时间: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "项目名称": self.项目名称,
            "调差总金额": self.调差总金额,
            "不含税总金额": self.不含税总金额,
            "税金": self.税金,
            "明细": [d.to_dict() for d in self.明细],
            "阶段汇总": self.阶段汇总,
            "价格校验": self.价格校验,
            "使用规则版本": self.使用规则版本,
            "计算时间": self.计算时间.isoformat() if isinstance(self.计算时间, datetime) else str(self.计算时间),
        }


@dataclass
class PriceValidationResult:
    """价格数据校验结果"""
    material_name: str
    total_days: int = 0
    valid_days: int = 0
    missing_days: int = 0
    missing_dates: List[str] = field(default_factory=list)
    data_completeness: float = 0.0
    warnings: List[str] = field(default_factory=list)
    is_valid: bool = True

    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
        if "数据完整率过低" in warning or "价格异常" in warning:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "material_name": self.material_name,
            "total_days": self.total_days,
            "valid_days": self.valid_days,
            "missing_days": self.missing_days,
            "missing_dates": self.missing_dates,
            "data_completeness": round(self.data_completeness, 4),
            "warnings": self.warnings,
            "is_valid": self.is_valid,
        }


@dataclass
class PhaseSummary:
    """阶段汇总数据"""
    阶段名称: str
    材料明细: List[AdjustmentDetail] = field(default_factory=list)
    小计金额: float = 0.0
    含税小计: float = 0.0

    def add_detail(self, detail: AdjustmentDetail) -> None:
        """添加明细并更新汇总"""
        self.材料明细.append(detail)
        self.小计金额 += detail.调整金额
        self.含税小计 += detail.含税调整金额


class AdjustmentEngineV3Error(Exception):
    """统一计算引擎异常"""
    def __init__(self, message: str, missing_fields: List[str] = None, step: str = None):
        self.message = message
        self.missing_fields = missing_fields or []
        self.step = step
        super().__init__(self.message)


# ============================================================
# 统一计算引擎
# ============================================================

class AdjustmentEngineV3:
    """
    统一调差计算引擎 v3.0

    整合 FormulaEngine 和 PriceService，实现7步标准计算流程：
    1. 校验配置
    2. 取基准价
    3. 取施工期均价
    3.5. 价格数据校验
    4. 判断是否超风险幅度
    5. 代入公式计算
    5.5. 分阶段汇总
    6. 输出结果

    支持多部位分时段计算：各部位独立计算自己的施工时段，互不通用
    """

    def __init__(self, config: AdjustmentRuleConfig):
        """
        初始化统一计算引擎

        Args:
            config: 调差规则配置
        """
        logger.info(f"[AdjustmentEngineV3] 初始化 | project={config.项目名称}, version={config.使用规则版本}")
        self.config = config
        self.formula_engine = FormulaEngine()
        self.price_service = PriceService()
        self.validation_errors: List[str] = []
        self.price_validation_results: Dict[str, PriceValidationResult] = {}
        self.phase_summaries: Dict[str, PhaseSummary] = {}

    # ============================================================
    # Step 1: 校验配置
    # ============================================================

    def _validate_config(self) -> None:
        """
        Step 1: 校验配置必填项

        校验内容：
        - 项目名称不能为空
        - 调差项目列表不能为空
        - 必须指定调差公式模板
        - 税率必须设置
        - 分阶段调差时必须有阶段划分

        Raises:
            AdjustmentEngineV3Error: 配置校验失败
        """
        logger.info("[_validate_config] 开始校验配置")
        errors = []

        # 基础信息校验
        if not self.config.项目名称 or not self.config.项目名称.strip():
            errors.append("缺少必填项: 项目名称")

        # 调差项目校验
        if not self.config.调差项目:
            errors.append("缺少必填项: 调差项目")

        # 公式模板校验
        if not self.config.调差公式模板:
            errors.append("缺少必填项: 调差公式模板")

        # 税率校验
        if self.config.税率 is None or self.config.税率 <= 0:
            errors.append("缺少必填项: 税率")

        # 分阶段调差校验
        if self.config.是否分阶段调差 == PhaseType.YES and not self.config.阶段划分:
            errors.append("分阶段调差时必须指定阶段划分")

        if errors:
            logger.error(f"[_validate_config] 配置校验失败 | errors={errors}")
            raise AdjustmentEngineV3Error(
                message="配置校验失败",
                missing_fields=errors,
                step="Step 1"
            )

        # 材料配置检查 - 自动补充默认风险幅度
        for material in self.config.调差项目:
            if material.名称 not in self.config.风险幅度:
                logger.warning(f"[_validate_config] 材料 '{material.名称}' 未配置风险幅度，使用默认值0%")
                self.config.风险幅度[material.名称] = RiskConfig(类型=RiskType.NONE, 值=0)

        logger.info(f"[_validate_config] 配置校验完成 | materials={len(self.config.调差项目)}")

    # ============================================================
    # Step 2: 取基准价
    # ============================================================

    def _fetch_base_prices(self, input_data: CalculationInput) -> Dict[str, float]:
        """
        Step 2: 获取基准价

        直接使用输入数据中的基准价（不进行配置匹配）
        支持"钢筋HRB400" -> "钢筋"的模糊匹配

        Args:
            input_data: 计算输入数据

        Returns:
            材料名 -> 基准价字典
        """
        logger.info(f"[_fetch_base_prices] 获取基准价 | materials={list(input_data.base_prices.keys())}")
        return dict(input_data.base_prices)

    # ============================================================
    # Step 3: 取施工期均价
    # ============================================================

    def _fetch_period_prices(self, input_data: CalculationInput) -> Dict[str, float]:
        """
        Step 3: 获取施工期均价

        按施工期价格采集规则采集价格
        支持多部位分时段计算：每个部位使用自己的施工时段

        Args:
            input_data: 计算输入数据

        Returns:
            材料名 -> 施工期均价字典
        """
        logger.info(f"[_fetch_period_prices] 获取施工期均价 | materials={list(input_data.period_prices.keys())}")

        avg_prices = {}

        for material_name, prices in input_data.period_prices.items():
            if not prices:
                avg_prices[material_name] = 0.0
                logger.debug(f"[_fetch_period_prices] 材料 '{material_name}' 无价格数据，使用均价0")
                continue

            # 获取采集规则
            rule = self.config.施工期价格采集规则
            if isinstance(rule, str):
                acquisition_rule = rule
            elif isinstance(rule, dict):
                # 多材料规则：按材料名获取
                acquisition_rule = rule.get(material_name, "按月算术平均")
            else:
                acquisition_rule = "按月算术平均"

            # 计算均价
            avg_price = self._calculate_average_price(prices, acquisition_rule)

            # 价格取整
            if self.config.价格取整规则 == PriceRounding.INTEGER:
                avg_price = round(avg_price)
            else:
                avg_price = round(avg_price, 2)

            avg_prices[material_name] = avg_price
            logger.debug(f"[_fetch_period_prices] 材料 '{material_name}' 均价={avg_price}")

        return avg_prices

    def _calculate_average_price(self, prices: List[PriceData], rule: str) -> float:
        """
        按规则计算平均价格

        目前支持：
        - 按月算术平均
        """
        if not prices:
            return 0.0

        # 按月算术平均
        total = sum(p.price for p in prices)
        return total / len(prices)

    def _get_period_avg_for_location(
        self,
        material_name: str,
        location: str,
        start_date: Optional[str],
        end_date: Optional[str],
        period_prices: Dict[str, List[PriceData]]
    ) -> float:
        """
        获取指定部位在施工时段内的均价

        多部位分时段计算核心方法：
        各部位使用自己独立的施工时段，互不通用

        Args:
            material_name: 材料名称
            location: 部位/楼栋名称
            start_date: 施工开始日期
            end_date: 施工结束日期
            period_prices: 价格数据

        Returns:
            施工期均价
        """
        if not start_date or not end_date:
            logger.debug(f"[_get_period_avg_for_location] 无时段信息 | location={location}")
            return 0.0

        prices = period_prices.get(material_name, [])
        if not prices:
            return 0.0

        # 过滤日期范围内的价格
        filtered = [p.price for p in prices if start_date <= p.date <= end_date]

        if not filtered:
            logger.debug(f"[_get_period_avg_for_location] 范围内无价格 | location={location}, range={start_date} to {end_date}")
            return 0.0

        avg = sum(filtered) / len(filtered)
        logger.debug(f"[_get_period_avg_for_location] 均价计算 | location={location}, avg={avg:.2f}")
        return avg

    # ============================================================
    # Step 3.5: 价格数据校验
    # ============================================================

    def _validate_price_data(
        self,
        input_data: CalculationInput,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, PriceValidationResult]:
        """
        Step 3.5: 价格数据校验

        校验内容：
        - 数据完整性（缺失率）
        - 节假日数量
        - 异常价格检测
        - 数据时间范围匹配

        Args:
            input_data: 计算输入数据
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            各材料的价格校验结果
        """
        logger.info("[_validate_price_data] 开始价格数据校验")

        # 如果没有指定时间范围，从工程量数据中推断
        if not start_date or not end_date:
            if input_data.quantities:
                dates = []
                for q in input_data.quantities:
                    if q.start_date:
                        dates.append(q.start_date)
                    if q.end_date:
                        dates.append(q.end_date)
                if dates:
                    start_date = min(dates)
                    end_date = max(dates)

        # 计算总天数
        total_days = 0
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                total_days = (end - start).days + 1
            except Exception as e:
                logger.warning(f"[_validate_price_data] 日期解析失败 | start={start_date}, end={end_date}", exc_info=True)

        # 校验每种材料的价格数据
        for material_name, prices in input_data.period_prices.items():
            result = self._validate_single_material_prices(
                material_name,
                prices,
                total_days,
                start_date,
                end_date
            )
            self.price_validation_results[material_name] = result

            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"[_validate_price_data] {material_name}: {warning}")

        valid_count = sum(1 for r in self.price_validation_results.values() if r.is_valid)
        logger.info(f"[_validate_price_data] 校验完成 | materials={len(self.price_validation_results)}, valid={valid_count}")

        return self.price_validation_results

    def _validate_single_material_prices(
        self,
        material_name: str,
        prices: List[PriceData],
        total_days: int,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> PriceValidationResult:
        """
        校验单个材料的价格数据

        Args:
            material_name: 材料名称
            prices: 价格数据列表
            total_days: 总天数
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            校验结果
        """
        result = PriceValidationResult(material_name=material_name)
        result.total_days = total_days

        if not prices:
            result.missing_days = total_days if total_days > 0 else 0
            result.add_warning(f"数据完整率过低: 0%")
            result.data_completeness = 0.0
            return result

        # 统计有效数据天数
        valid_dates = set()
        for p in prices:
            if p.price > 0:
                valid_dates.add(p.date)

        result.valid_days = len(valid_dates)

        # 找出缺失的日期
        if start_date and end_date and total_days > 0:
            all_dates = set()
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                current = start
                while current <= end:
                    all_dates.add(current.strftime("%Y-%m-%d"))
                    current += timedelta(days=1)
            except Exception:
                pass

            missing = all_dates - valid_dates
            result.missing_dates = sorted(list(missing))[:10]  # 只保留前10个缺失日期
            result.missing_days = len(missing)

        # 计算数据完整率
        if total_days > 0:
            result.data_completeness = (result.valid_days / total_days) * 100
        elif len(prices) > 0:
            result.data_completeness = 100.0

        # 检查完整率
        if result.data_completeness < 50:
            result.add_warning(f"数据完整率过低: {result.data_completeness:.1f}%")
        elif result.data_completeness < 80:
            result.add_warning(f"数据完整率偏低: {result.data_completeness:.1f}%")

        # 检测异常价格（偏离均值超过50%）
        price_values = [p.price for p in prices if p.price > 0]
        if len(price_values) >= 3:
            avg_price = sum(price_values) / len(price_values)
            for p in prices:
                if p.price > 0 and avg_price > 0:
                    deviation = abs(p.price - avg_price) / avg_price
                    if deviation > 0.5:
                        result.add_warning(f"价格异常: {p.date} 价格={p.price} 偏离均值{deviation*100:.1f}%")

        return result

    def _get_price_validation_summary(self) -> Dict[str, Any]:
        """
        获取价格校验汇总信息

        Returns:
            汇总字典
        """
        if not self.price_validation_results:
            return {}

        total_materials = len(self.price_validation_results)
        valid_materials = sum(1 for r in self.price_validation_results.values() if r.is_valid)

        return {
            "total_materials": total_materials,
            "valid_materials": valid_materials,
            "invalid_materials": total_materials - valid_materials,
            "average_completeness": sum(r.data_completeness for r in self.price_validation_results.values()) / total_materials,
            "details": {
                name: result.to_dict()
                for name, result in self.price_validation_results.items()
            }
        }

    # ============================================================
    # Step 4: 判断是否超风险幅度
    # ============================================================

    def _check_risk_threshold(
        self,
        material_name: str,
        base_price: float,
        avg_price: float
    ) -> Tuple[bool, bool, float]:
        """
        Step 4: 判断是否超风险幅度

        Args:
            material_name: 材料名称
            base_price: 基准价
            avg_price: 施工期均价

        Returns:
            Tuple[bool, bool, float]: (是否超幅, 是否上涨, 有效价差)
        """
        logger.debug(f"[_check_risk_threshold] 检查风险幅度 | material={material_name}, base={base_price}, avg={avg_price}")

        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        # 情况1: 完全无风险配置 (RiskType.NONE) 或值为0
        if risk_config.类型 == RiskType.NONE or risk_config.值 == 0:
            logger.debug(f"[_check_risk_threshold] 0%风险幅度，全额调差 | material={material_name}")
            return True, avg_price > base_price, avg_price - base_price

        # 情况2: 有风险幅度配置，检查是否超幅
        if base_price <= 0:
            logger.warning(f"[_check_risk_threshold] 基准价为0 | material={material_name}")
            return False, False, 0

        if risk_config.类型 == RiskType.PERCENTAGE:
            # 百分比风险幅度
            upper = base_price * (1 + risk_config.值 / 100)
            lower = base_price * (1 - risk_config.值 / 100)
        else:
            # 固定金额风险幅度
            upper = base_price + risk_config.值
            lower = base_price - risk_config.值

        if avg_price > upper:
            # 超幅度上浮
            effective_diff = avg_price - upper
            logger.info(f"[_check_risk_threshold] 超幅上涨 | material={material_name}, diff={effective_diff:.2f}")
            return True, True, effective_diff
        elif avg_price < lower:
            # 超幅度下浮
            effective_diff = avg_price - lower
            logger.info(f"[_check_risk_threshold] 超幅下跌 | material={material_name}, diff={effective_diff:.2f}")
            return True, False, effective_diff
        else:
            # 幅度内
            logger.debug(f"[_check_risk_threshold] 幅度内不调差 | material={material_name}")
            return False, False, 0

    def _get_risk_display(self, risk_config: RiskConfig) -> str:
        """获取风险幅度显示字符串"""
        if risk_config.类型 == RiskType.PERCENTAGE:
            return f"±{risk_config.值}%"
        elif risk_config.类型 == RiskType.FIXED:
            return f"±{risk_config.值}元"
        else:
            return "0%全额调差"

    # ============================================================
    # Step 5: 代入公式计算
    # ============================================================

    def _calculate_adjustment(
        self,
        material_name: str,
        quantity: float,
        unit: str,
        base_price: float,
        avg_price: float,
        phase: str,
        location: str = ""
    ) -> AdjustmentDetail:
        """
        Step 5: 代入公式计算

        支持5种调差公式模板：
        1. 标准三段式 (standard_three_stage)
        2. 龙湖增值税率换算法 (longhu_vat_conversion)
        3. 豪森比例调差法 (ratio_adjustment)
        4. 造价信息调整法 (cost_info_adjustment)
        5. 无风险幅度 (no_risk)

        Args:
            material_name: 材料名称
            quantity: 工程量
            unit: 单位
            base_price: 基准价
            avg_price: 施工期均价
            phase: 阶段
            location: 部位

        Returns:
            调差明细
        """
        logger.info(
            f"[_calculate_adjustment] 计算调差 | material={material_name}, "
            f"quantity={quantity}, base={base_price}, avg={avg_price}"
        )

        # 获取风险配置
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        # Step 4: 判断是否超幅度
        is_over_risk, is_rising, effective_diff = self._check_risk_threshold(
            material_name, base_price, avg_price
        )

        # 获取风险幅度显示
        risk_display = self._get_risk_display(risk_config)

        # 构建公式输入
        risk_config_dict = {
            "类型": risk_config.类型.value if hasattr(risk_config.类型, 'value') else str(risk_config.类型),
            "值": risk_config.值
        }

        formula_input = FormulaInput(
            material_name=material_name,
            quantity=quantity,
            unit=unit,
            base_price=base_price,
            period_avg_price=avg_price,
            risk_config=risk_config_dict,
            tax_rate=self.config.税率,
        )

        # 获取公式类型字符串
        formula_type_str = self._get_formula_type_string()

        # 调用公式引擎计算
        try:
            adjustment_amount, formula = self.formula_engine.calculate(formula_type_str, formula_input)
        except Exception as e:
            logger.error(f"[_calculate_adjustment] 公式计算失败 | material={material_name}, error={e}", exc_info=True)
            adjustment_amount = 0
            formula = f"公式计算失败: {e}"

        # 关键：如果风险阈值检查未超幅，覆盖公式计算结果
        if not is_over_risk:
            adjustment_amount = 0
            formula = f"风险幅度内不调差 | 施工期均价{avg_price}在范围内"
            logger.debug(f"[_calculate_adjustment] 风险幅度内不调差 | material={material_name}")

        # 处理负数（跌价）
        if adjustment_amount < 0:
            if self.config.负数处理 == NegativeHandling.NO_ADJUST:
                adjustment_amount = 0
                formula = formula + " (不调整)"

        # 计算含税金额
        tax_rate = self.config.税率 / 100
        tax_amount = adjustment_amount * tax_rate
        total_with_tax = adjustment_amount + tax_amount

        # 调整单价（不含税）
        adjustment_unit_price = adjustment_amount / quantity if quantity > 0 else 0

        return AdjustmentDetail(
            材料名称=material_name,
            阶段=phase,
            部位=location,
            工程量=quantity,
            工程量单位=unit,
            基准价=base_price,
            施工均价=avg_price,
            风险幅度=risk_display,
            是否超幅=is_over_risk,
            调整单价=round(adjustment_unit_price, 2),
            调整金额=round(adjustment_amount, 2),
            税率=self.config.税率,
            含税调整金额=round(total_with_tax, 2),
            计算公式=formula,
            计算依据=f"基准价来源:{self.config.基准价来源}, 均价规则:{self.config.施工期价格采集规则}"
        )

    def _get_formula_type_string(self) -> str:
        """获取公式类型字符串"""
        formula_type = self.config.调差公式模板

        # 处理枚举值
        type_value = formula_type.value if hasattr(formula_type, 'value') else str(formula_type)

        # 映射到 FormulaEngine 的字符串常量
        mapping = {
            "标准三段式": FormulaTypeStr.STANDARD_THREE_STAGE,
            "standard_three_stage": FormulaTypeStr.STANDARD_THREE_STAGE,
            "无风险幅度": FormulaTypeStr.NO_RISK,
            "no_risk": FormulaTypeStr.NO_RISK,
            "比例调差法": FormulaTypeStr.RATIO_ADJUSTMENT,
            "ratio_adjustment": FormulaTypeStr.RATIO_ADJUSTMENT,
            "造价信息调整法": FormulaTypeStr.COST_INFO_ADJUSTMENT,
            "cost_info_adjustment": FormulaTypeStr.COST_INFO_ADJUSTMENT,
            "龙湖增值税率换算法": FormulaTypeStr.LONGHU_VAT_CONVERSION,
            "longhu_vat_conversion": FormulaTypeStr.LONGHU_VAT_CONVERSION,
            "自定义": "custom",
        }

        return mapping.get(type_value, FormulaTypeStr.STANDARD_THREE_STAGE)

    # ============================================================
    # Step 5.5: 分阶段汇总
    # ============================================================

    def _summarize_by_phase(self, details: List[AdjustmentDetail]) -> Dict[str, PhaseSummary]:
        """
        Step 5.5: 分阶段汇总

        按施工阶段分组统计调差金额

        Args:
            details: 调差明细列表

        Returns:
            阶段名称 -> 汇总数据
        """
        logger.info(f"[_summarize_by_phase] 开始分阶段汇总 | details={len(details)}")

        phase_summaries: Dict[str, PhaseSummary] = defaultdict(
            lambda: PhaseSummary(阶段名称="整体")
        )

        for detail in details:
            phase_name = detail.阶段 or "整体"
            if phase_name not in phase_summaries:
                phase_summaries[phase_name] = PhaseSummary(阶段名称=phase_name)
            phase_summaries[phase_name].add_detail(detail)

        # 记录汇总结果
        for phase_name, summary in phase_summaries.items():
            logger.info(f"[_summarize_by_phase] 阶段汇总 | phase={phase_name}, items={len(summary.材料明细)}, subtotal={summary.含税小计:.2f}")

        self.phase_summaries = dict(phase_summaries)
        return self.phase_summaries

    def _get_phase_summary_data(self) -> List[Dict[str, Any]]:
        """
        获取分阶段汇总数据（用于输出）

        Returns:
            阶段汇总列表
        """
        if not self.phase_summaries:
            return []

        return [
            {
                "阶段名称": summary.阶段名称,
                "材料种数": len(summary.材料明细),
                "小计金额（不含税）": round(summary.小计金额, 2),
                "含税小计": round(summary.含税小计, 2)
            }
            for summary in self.phase_summaries.values()
        ]

    # ============================================================
    # Step 6: 输出结果
    # ============================================================

    def _format_output(
        self,
        details: List[AdjustmentDetail],
        project_name: str
    ) -> CalculationResult:
        """
        Step 6: 格式化输出 - v3.0 输出格式

        Args:
            details: 调差明细列表
            project_name: 项目名称

        Returns:
            调差计算结果
        """
        logger.info(f"[_format_output] 格式化输出 | details={len(details)}, project={project_name}")

        # 计算总金额
        total_with_tax = sum(d.含税调整金额 for d in details)
        total_without_tax = sum(d.调整金额 for d in details)
        tax_amount = total_with_tax - total_without_tax

        # 分阶段汇总
        self._summarize_by_phase(details)

        # 构建结果
        result = CalculationResult(
            项目名称=project_name,
            调差总金额=round(total_with_tax, 2),
            不含税总金额=round(total_without_tax, 2),
            税金=round(tax_amount, 2),
            明细=details,
            阶段汇总=self._get_phase_summary_data(),
            价格校验=self._get_price_validation_summary(),
            使用规则版本="v3.0",
            计算时间=datetime.now()
        )

        logger.info(f"[_format_output] 输出完成 | total_tax={total_with_tax:.2f}, total_no_tax={total_without_tax:.2f}")

        return result

    # ============================================================
    # 主计算方法
    # ============================================================

    def calculate(self, input_data: CalculationInput) -> CalculationResult:
        """
        执行完整的7步调差计算流程

        Step 1: 校验配置
        Step 2: 取基准价
        Step 3: 取施工期均价
        Step 3.5: 价格数据校验
        Step 4: 判断是否超风险幅度
        Step 5: 代入公式计算
        Step 5.5: 分阶段汇总
        Step 6: 输出结果

        Args:
            input_data: 计算输入数据

        Returns:
            调差计算结果

        Raises:
            AdjustmentEngineV3Error: 计算过程中发生错误
        """
        logger.info(f"[calculate] 开始调差计算 | project={self.config.项目名称}")

        try:
            # Step 1: 校验配置
            logger.info("[calculate] Step 1: 校验配置")
            self._validate_config()

            # Step 2: 取基准价
            logger.info("[calculate] Step 2: 取基准价")
            base_prices = self._fetch_base_prices(input_data)
            logger.debug(f"[calculate] 基准价 | {base_prices}")

            # Step 3: 取施工期均价
            logger.info("[calculate] Step 3: 取施工期均价")
            avg_prices = self._fetch_period_prices(input_data)
            logger.debug(f"[calculate] 施工期均价 | {avg_prices}")

            # Step 3.5: 价格数据校验
            logger.info("[calculate] Step 3.5: 价格数据校验")
            self._validate_price_data(input_data)
            invalid_count = sum(1 for r in self.price_validation_results.values() if not r.is_valid)
            if invalid_count > 0:
                logger.warning(f"[calculate] 价格数据存在问题 | invalid_materials={invalid_count}")

            # 计算明细
            details = []

            # 按部位分组（多部位分时段计算核心）
            location_groups: Dict[str, List[QuantityData]] = defaultdict(list)
            for qty in input_data.quantities:
                loc = qty.location or "整体"
                location_groups[loc].append(qty)

            # 每个部位分别计算
            for location_name, quantities in location_groups.items():
                for qty_data in quantities:
                    material_name = qty_data.material_name
                    phase = qty_data.phase or "整体"

                    # 模糊匹配：检查材料名称是否在调差项目中
                    matched_material = None
                    for m in self.config.调差项目:
                        if self._match_material_name(material_name, m.名称):
                            matched_material = m
                            break

                    if not matched_material:
                        logger.warning(f"[calculate] 材料不在调差配置中，跳过 | material={material_name}")
                        continue

                    # 检查工程量
                    if qty_data.quantity <= 0:
                        logger.warning(f"[calculate] 工程量为0，跳过 | material={material_name}")
                        continue

                    # 获取基准价
                    base_price = base_prices.get(material_name, 0)
                    if base_price <= 0:
                        logger.warning(f"[calculate] 基准价为0，跳过 | material={material_name}")
                        continue

                    # 获取施工期均价（使用部位的时段）
                    avg_price = self._get_period_avg_for_location(
                        material_name=material_name,
                        location=location_name,
                        start_date=qty_data.start_date,
                        end_date=qty_data.end_date,
                        period_prices=input_data.period_prices
                    )

                    if avg_price <= 0:
                        # 尝试使用整体均价
                        avg_price = avg_prices.get(material_name, 0)

                    # Step 5: 计算
                    detail = self._calculate_adjustment(
                        material_name=material_name,
                        quantity=qty_data.quantity,
                        unit=qty_data.unit,
                        base_price=base_price,
                        avg_price=avg_price,
                        phase=phase,
                        location=location_name
                    )
                    details.append(detail)

            # Step 6: 输出结果
            return self._format_output(details, self.config.项目名称)

        except AdjustmentEngineV3Error as e:
            logger.error(f"[calculate] 配置校验失败 | message={e.message}")
            raise
        except Exception as e:
            logger.error(f"[calculate] 计算异常 | error={type(e).__name__}: {e}", exc_info=True)
            raise AdjustmentEngineV3Error(
                message=f"计算异常: {type(e).__name__}: {e}",
                step="unknown"
            )

    def _match_material_name(self, name1: str, name2: str) -> bool:
        """
        模糊匹配材料名称

        支持：
        - 精确匹配
        - 包含匹配（"钢筋HRB400" 匹配 "钢筋"）
        - 部分匹配

        Args:
            name1: 材料名称1
            name2: 材料名称2

        Returns:
            是否匹配
        """
        if name1 == name2:
            return True
        if name1 in name2 or name2 in name1:
            return True
        # 常见材料别名
        aliases = {
            "钢筋": ["钢筋", "螺纹钢筋", "HRB400", "HRB400E", "钢筋", " Steel"],
            "混凝土": ["混凝土", "商品混凝土", "商混", "砼"],
            "电缆": ["电缆", "电力电缆", "Control Cable"],
        }
        for standard_name, alias_list in aliases.items():
            if name1 in alias_list and name2 in alias_list:
                return True
        return False

    # ============================================================
    # 便捷方法
    # ============================================================

    @staticmethod
    def calculate_simple(
        base_price: float,
        avg_price: float,
        quantity: float,
        risk_percent: float = 0,
        risk_fixed: float = 0,
        tax_rate: float = 9
    ) -> Dict[str, float]:
        """
        简单计算（无需完整配置）
        用于快速计算单个材料的调差
        """
        tax_rate = tax_rate / 100

        if risk_percent > 0:
            upper = base_price * (1 + risk_percent / 100)
            lower = base_price * (1 - risk_percent / 100)
        elif risk_fixed > 0:
            upper = base_price + risk_fixed
            lower = base_price - risk_fixed
        else:
            upper = lower = base_price

        if avg_price > upper:
            effective_diff = avg_price - upper
        elif avg_price < lower:
            effective_diff = avg_price - lower
        else:
            effective_diff = 0

        adjustment = quantity * effective_diff
        total_with_tax = adjustment * (1 + tax_rate)

        return {
            "base_price": base_price,
            "avg_price": avg_price,
            "quantity": quantity,
            "effective_diff": effective_diff,
            "adjustment_amount": round(adjustment, 2),
            "tax_amount": round(adjustment * tax_rate, 2),
            "total_with_tax": round(total_with_tax, 2)
        }


# ============================================================
# 便捷函数
# ============================================================

def calculate_with_config(
    config: Dict,
    base_prices: Dict[str, float],
    period_prices: Dict[str, List[PriceData]],
    quantities: List[Dict]
) -> Dict:
    """
    使用字典配置执行调差计算
    便捷函数，无需手动构建配置对象
    """
    # 构建配置对象
    rule_config = AdjustmentRuleConfig(**config)

    # 构建输入数据
    input_data = CalculationInput(
        base_prices=base_prices,
        period_prices={
            k: [PriceData(**p) if isinstance(p, dict) else p for p in v]
            for k, v in period_prices.items()
        },
        quantities=[
            QuantityData(**q) if isinstance(q, dict) else q
            for q in quantities
        ]
    )

    # 执行计算
    engine = AdjustmentEngineV3(rule_config)
    result = engine.calculate(input_data)

    # 转为字典
    return result.to_dict()