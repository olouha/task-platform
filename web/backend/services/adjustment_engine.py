"""
调差计算引擎 - AI可执行配置规范实现
遵循《地产项目材料调差规则_AI可执行配置规范》v2.0

5种调差公式模板：
1. 标准三段式 - 超幅度后调整
2. 无风险幅度 - 全额调差
3. 比例调差法 - 豪森模式
4. 造价信息调整法 - 朱家庄模式
5. 龙湖增值税率换算法 - 龙湖模式

7步标准流程（优化版）：
Step 1: 读取配置 → 校验必填项
Step 2: 取基准价
Step 3: 取施工期均价
Step 3.5: 价格数据校验
Step 4: 判断是否超风险幅度
Step 5: 代入公式计算
Step 5.5: 分阶段汇总
Step 6: 输出结果
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from models.adjustment_rules import (
    AdjustmentRuleConfig, AdjustmentDetail, CalculationResult,
    RiskConfig, RiskType, FormulaType, NegativeHandling, PhaseDefinition,
    MaterialConfig, HolidayHandling, ShortCycleHandling, PriceRounding
)

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """价格数据"""
    date: str
    price: float
    source: str = ""


@dataclass
class QuantityData:
    """工程量数据"""
    material_name: str
    quantity: float
    unit: str
    phase: str = "整体"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@dataclass
class CalculationInput:
    """计算输入数据"""
    base_prices: Dict[str, float]  # 材料名 -> 基准价
    period_prices: Dict[str, List[PriceData]]  # 材料名 -> 价格列表
    quantities: List[QuantityData]  # 工程量列表
    phase: str = "整体"


class AdjustmentValidationError(Exception):
    """配置校验错误"""
    def __init__(self, message: str, missing_fields: List[str] = None):
        self.message = message
        self.missing_fields = missing_fields or []
        super().__init__(self.message)


class AdjustmentCalculationError(Exception):
    """计算错误"""
    def __init__(self, message: str, material: str = None, phase: str = None):
        self.message = message
        self.material = material
        self.phase = phase
        super().__init__(self.message)


@dataclass
class PriceValidationResult:
    """价格数据校验结果"""
    material_name: str
    total_days: int = 0  # 总天数
    valid_days: int = 0  # 有效数据天数
    missing_days: int = 0  # 缺失天数
    missing_dates: List[str] = field(default_factory=list)  # 缺失的日期列表
    holiday_count: int = 0  # 节假日数量
    data_completeness: float = 0.0  # 数据完整率 (0-100%)
    warnings: List[str] = field(default_factory=list)  # 警告信息
    is_valid: bool = True  # 是否有效

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
            "holiday_count": self.holiday_count,
            "data_completeness": round(self.data_completeness, 1),
            "warnings": self.warnings,
            "is_valid": self.is_valid
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


class AdjustmentEngine:
    """调差计算引擎 - 优化版"""

    def __init__(self, config: AdjustmentRuleConfig):
        self.config = config
        self.validation_errors: List[str] = []
        self.price_validation_results: Dict[str, PriceValidationResult] = {}  # 价格校验结果
        self.phase_summaries: Dict[str, PhaseSummary] = {}  # 阶段汇总

    # ============================================================
    # Step 1: 校验配置
    # ============================================================

    def _validate_config(self) -> None:
        """Step 1: 校验24项必填配置"""
        logger.info("[_validate_config] 开始校验配置")
        errors = []

        # 基础信息类检查
        if not self.config.调差项目:
            errors.append("缺少必填项: 调差项目")

        # 价格规则类检查
        if not self.config.基准价来源:
            errors.append("缺少必填项: 基准价来源")
        if not self.config.基准价取价规则:
            errors.append("缺少必填项: 基准价取价规则")
        if not self.config.施工期价格采集规则:
            errors.append("缺少必填项: 施工期价格采集规则")

        # 周期与阶段类检查
        if self.config.是否分阶段调差 == "是" and not self.config.阶段划分:
            errors.append("分阶段调差时必须指定阶段划分")

        # 计算公式类检查
        if not self.config.调差公式模板:
            errors.append("缺少必填项: 调差公式模板")
        if self.config.税率 is None:
            errors.append("缺少必填项: 税率")

        if errors:
            logger.error(f"[_validate_config] 配置校验失败 | errors={errors}")
            raise AdjustmentValidationError(
                "配置校验失败",
                missing_fields=errors
            )

        # 材料配置检查
        for material in self.config.调差项目:
            if material.名称 not in self.config.风险幅度:
                logger.warning(f"[_validate_config] 材料 '{material.名称}' 未配置风险幅度，使用默认值")
                self.config.风险幅度[material.名称] = RiskConfig(类型=RiskType.NONE, 值=0)

        logger.info(f"[_validate_config] 配置校验完成 | materials={len(self.config.调差项目)}")

    # ============================================================
    # Step 2: 取基准价
    # ============================================================

    def _fetch_base_prices(self, input_data: CalculationInput) -> Dict[str, float]:
        """
        Step 2: 获取基准价
        根据基准价来源和取价规则确定基准价
        """
        # 直接使用输入数据中的基准价（不进行配置匹配）
        # 这样可以处理"钢筋HRB400" -> "钢筋"的匹配问题
        return dict(input_data.base_prices)

    # ============================================================
    # Step 3: 取施工期均价
    # ============================================================

    def _fetch_period_prices(self, input_data: CalculationInput) -> Dict[str, float]:
        """
        Step 3: 获取施工期均价
        按施工期价格采集规则采集价格
        """
        avg_prices = {}

        # 直接使用输入数据中的施工期价格
        for material_name, prices in input_data.period_prices.items():
            if not prices:
                avg_prices[material_name] = 0
                continue

            # 按采集规则计算均价
            avg_price = self._calculate_average_price(
                prices,
                str(self.config.施工期价格采集规则) if self.config.施工期价格采集规则 else "按月算术平均"
            )

            # 价格取整
            avg_price = self._round_price(avg_price, self.config.价格取整规则)
            avg_prices[material_name] = avg_price

        return avg_prices

    def _calculate_average_price(self, prices: List[PriceData], rule: str) -> float:
        """按规则计算平均价格"""
        if not prices:
            return 0

        # 目前支持：按月算术平均
        # 未来可扩展：每月1/10/20日取价等
        total = sum(p.price for p in prices)
        return total / len(prices)

    def _handle_missing_price(
        self,
        fallback_price: float,
        rule: HolidayHandling
    ) -> float:
        """
        处理缺失价格 - 实现节假日/无价处理逻辑

        Args:
            fallback_price: 回退价格
            rule: 处理规则

        Returns:
            处理后的价格，0表示需要从外部获取
        """
        logger.debug(f"[_handle_missing_price] 处理缺失价格 | fallback={fallback_price}, rule={rule}")

        if fallback_price > 0:
            return fallback_price

        # 按规则处理
        if rule == HolidayHandling.LAST_MONTH:
            # 取上月价 - 返回0表示需要从历史获取
            logger.debug("[_handle_missing_price] 使用上月价格")
            return 0
        elif rule == HolidayHandling.SHIFT_DAY:
            # 顺延1天 - 返回0表示需要顺延
            logger.debug("[_handle_missing_price] 顺延到下一个工作日")
            return 0
        elif rule == HolidayHandling.AVERAGE_PREV_NEXT:
            # 取前后日均价 - 返回0表示需要计算均值
            logger.debug("[_handle_missing_price] 取前后日均价")
            return 0

        return 0

    def _get_next_workday(self, current_date: date) -> date:
        """
        获取下一个工作日（顺延1天）
        简单实现：周末顺延，周一到周五不变
        """
        next_day = current_date + timedelta(days=1)
        # 如果是周六或周日，继续顺延
        while next_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
            next_day += timedelta(days=1)
        return next_day

    def _get_previous_workday(self, current_date: date) -> date:
        """
        获取上一个工作日
        """
        prev_day = current_date - timedelta(days=1)
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)
        return prev_day

    def _calculate_workday_average(
        self,
        prices: List[PriceData],
        target_date: date
    ) -> float:
        """
        计算前后工作日的均价

        Args:
            prices: 价格列表
            target_date: 目标日期（缺失价格的日期）

        Returns:
            前后工作日均价
        """
        prev_prices = [p for p in prices if self._to_date(p.date) < target_date]
        next_prices = [p for p in prices if self._to_date(p.date) > target_date]

        if not prev_prices and not next_prices:
            return 0

        # 获取最近的前后价格
        prev_price = prev_prices[-1].price if prev_prices else 0
        next_price = next_prices[0].price if next_prices else 0

        if prev_price > 0 and next_price > 0:
            return (prev_price + next_price) / 2
        elif prev_price > 0:
            return prev_price
        elif next_price > 0:
            return next_price
        return 0

    @staticmethod
    def _to_date(date_str: str) -> date:
        """字符串转date"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()

    def _round_price(self, price: float, rule: PriceRounding) -> float:
        """价格取整"""
        if rule == PriceRounding.INTEGER:
            return round(price)  # 取整到元
        else:
            return round(price, 2)  # 保留2位小数

    # ============================================================
    # Step 3.5: 价格数据校验（新增）
    # ============================================================

    def _validate_price_data(
        self,
        input_data: CalculationInput,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, PriceValidationResult]:
        """
        Step 3.5: 价格数据校验

        检查内容：
        1. 数据完整性（缺失率）
        2. 节假日数量
        3. 异常价格检测
        4. 数据时间范围匹配

        Returns:
            各材料的价格校验结果
        """
        logger.info("[_validate_price_data] 开始价格数据校验")
        validation_results: Dict[str, PriceValidationResult] = {}

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
                start = self._to_date(start_date)
                end = self._to_date(end_date)
                total_days = (end - start).days + 1
            except Exception as e:
                logger.warning(f"[_validate_price_data] 日期解析失败 | start={start_date}, end={end_date}")

        # 校验每种材料的价格数据
        for material_name, prices in input_data.period_prices.items():
            result = self._validate_single_material_prices(
                material_name,
                prices,
                total_days,
                start_date,
                end_date
            )
            validation_results[material_name] = result
            self.price_validation_results[material_name] = result

            if result.warnings:
                for warning in result.warnings:
                    logger.warning(f"[_validate_price_data] {material_name}: {warning}")

        valid_count = sum(1 for r in validation_results.values() if r.is_valid)
        logger.info(f"[_validate_price_data] 校验完成 | materials={len(validation_results)}, valid={valid_count}")

        return validation_results

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
            return result

        # 按日期排序
        sorted_prices = sorted(prices, key=lambda p: p.date)

        # 统计节假日/周末
        holiday_dates = set()
        for p in prices:
            try:
                d = self._to_date(p.date)
                if d.weekday() >= 5:  # 周六日
                    holiday_dates.add(p.date)
            except Exception:
                pass

        result.holiday_count = len(holiday_dates)

        # 计算有效数据天数（排除重复日期）
        valid_dates = set()
        for p in prices:
            if p.price > 0:  # 有效价格
                valid_dates.add(p.date)

        result.valid_days = len(valid_dates)

        # 找出缺失的日期
        if start_date and end_date and total_days > 0:
            all_dates = set()
            try:
                start = self._to_date(start_date)
                end = self._to_date(end_date)
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
            result.data_completeness = 100.0  # 无法确定总天数时，假设完整

        # 检查完整率
        if result.data_completeness < 50:
            result.add_warning(f"数据完整率过低: {result.data_completeness:.1f}%")
        elif result.data_completeness < 80:
            result.add_warning(f"数据完整率偏低: {result.data_completeness:.1f}%")

        # 检测异常价格（偏离均值超过50%）
        price_values = [p.price for p in prices if p.price > 0]
        if len(price_values) >= 3:
            avg = sum(price_values) / len(price_values)
            for p in prices:
                if p.price > 0 and avg > 0:
                    deviation = abs(p.price - avg) / avg
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
        avg_completeness = sum(r.data_completeness for r in self.price_validation_results.values()) / total_materials

        return {
            "total_materials": total_materials,
            "valid_materials": valid_materials,
            "invalid_materials": total_materials - valid_materials,
            "average_completeness": round(avg_completeness, 1),
            "details": {
                name: result.to_dict()
                for name, result in self.price_validation_results.items()
            }
        }

    # ============================================================
    # Step 4: 判断是否超风险幅度（优化版）
    # ============================================================

    def _check_risk_threshold(
        self,
        material_name: str,
        base_price: float,
        avg_price: float
    ) -> Tuple[bool, bool, float]:
        """
        Step 4: 判断是否超风险幅度
        返回: (是否超幅, 是否上涨, 有效价差)

        优化说明：
        1. 明确区分 RiskType.NONE（无风险配置）和 0%（全额调差）
        2. 增加详细日志记录
        """
        logger.debug(f"[_check_risk_threshold] 检查风险幅度 | material={material_name}, base={base_price}, avg={avg_price}")

        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        # 情况1: 完全无风险配置 (RiskType.NONE)
        # 使用默认值0，表示全额调差
        if risk_config.类型 == RiskType.NONE:
            logger.debug(f"[_check_risk_threshold] 无风险配置，全额调差 | material={material_name}")
            return True, avg_price > base_price, avg_price - base_price

        # 情况2: 明确0%风险幅度 = 全额调差
        if risk_config.值 == 0:
            logger.debug(f"[_check_risk_threshold] 0%风险幅度，全额调差 | material={material_name}")
            return True, avg_price > base_price, avg_price - base_price

        # 情况3: 有风险幅度配置，检查是否超幅
        if base_price <= 0:
            logger.warning(f"[_check_risk_threshold] 基准价为0 | material={material_name}")
            return False, False, 0

        if risk_config.类型 == RiskType.PERCENTAGE:
            # 百分比风险幅度
            upper = base_price * (1 + risk_config.值 / 100)
            lower = base_price * (1 - risk_config.值 / 100)
            risk_type_str = f"±{risk_config.值}%"
        else:
            # 固定金额风险幅度
            upper = base_price + risk_config.值
            lower = base_price - risk_config.值
            risk_type_str = f"±{risk_config.值}元"

        logger.debug(f"[_check_risk_threshold] 风险区间 | upper={upper:.2f}, lower={lower:.2f}, type={risk_type_str}")

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

    # ============================================================
    # Step 5: 代入公式计算
    # ============================================================

    def _get_risk_display(self, risk_config: RiskConfig) -> str:
        """获取风险幅度显示字符串"""
        if risk_config.类型 == RiskType.PERCENTAGE:
            return f"±{risk_config.值}%"
        elif risk_config.类型 == RiskType.FIXED:
            return f"±{risk_config.值}元/{self.config.调差项目[0].工程量范围.split('；')[0].split('(')[0].strip() if self.config.调差项目 else '吨'}" if '电缆' not in risk_config else f"±{risk_config.值}元/吨铜价"
        else:
            return "0%全额调差"

    def _calculate_standard_three_stage(
        self,
        material_name: str,
        quantity: float,
        base_price: float,
        avg_price: float,
        is_over_risk: bool,
        is_rising: bool
    ) -> Tuple[float, str]:
        """标准三段式公式"""
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        if not is_over_risk:
            # 幅度内，不调差
            return 0, "幅度内，不调差"

        if risk_config.类型 == RiskType.NONE or risk_config.值 == 0:
            # 无风险幅度
            amount = quantity * (avg_price - base_price)
            formula = f"{quantity} × ({avg_price} - {base_price})"
        elif risk_config.类型 == RiskType.PERCENTAGE:
            upper = base_price * (1 + risk_config.值 / 100)
            lower = base_price * (1 - risk_config.值 / 100)
            amount = quantity * (avg_price - upper if is_rising else avg_price - lower)
            formula = f"{quantity} × [{avg_price} - {base_price} × {'1+' if is_rising else '1-'}{risk_config.值 / 100} = {upper if is_rising else lower}]"
        else:
            # 固定金额
            upper = base_price + risk_config.值
            lower = base_price - risk_config.值
            amount = quantity * (avg_price - upper if is_rising else avg_price - lower)
            formula = f"{quantity} × [{avg_price} - {'基价+' if is_rising else '基价-'}{risk_config.值}]"

        return amount, formula

    def _calculate_no_risk(
        self,
        quantity: float,
        base_price: float,
        avg_price: float
    ) -> Tuple[float, str]:
        """无风险幅度公式（全额调差）"""
        amount = quantity * (avg_price - base_price)
        formula = f"{quantity} × ({avg_price} - {base_price}) = {amount}"
        return amount, formula

    def _calculate_ratio_adjustment(
        self,
        material_name: str,
        quantity: float,
        base_price: float,
        avg_price: float,
        is_over_risk: bool,
        is_rising: bool
    ) -> Tuple[float, str]:
        """比例调差法（豪森模式）

        涨幅（Pi/P0 > 1 + 风险幅度）：
          调整金额 = P0 × (Pi/P0 - (1 + 风险幅度)) × Qi × (1 + 税率)

        跌幅（Pi/P0 < 1 - 风险幅度）：
          调整金额 = P0 × (Pi/P0 - (1 - 风险幅度)) × Qi × (1 + 税率)
        """
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        if not is_over_risk:
            return 0, "幅度内，不调差"

        if risk_config.值 == 0:
            # 无风险幅度，按全额计算
            ratio = avg_price / base_price if base_price > 0 else 0
            amount = base_price * (ratio - 1) * quantity
            formula = f"{base_price} × ({ratio:.4f} - 1) × {quantity}"
        else:
            risk_rate = risk_config.值 / 100
            ratio = avg_price / base_price if base_price > 0 else 0
            effective_ratio = ratio - (1 + risk_rate if is_rising else 1 - risk_rate)
            amount = base_price * effective_ratio * quantity
            formula = f"{base_price} × ({ratio:.4f} - {1 + risk_rate if is_rising else 1 - risk_rate}) × {quantity}"

        return amount, formula

    def _calculate_cost_info_adjustment(
        self,
        material_name: str,
        quantity: float,
        base_price: float,
        avg_price: float,
        is_over_risk: bool,
        is_rising: bool
    ) -> Tuple[float, str]:
        """造价信息调整法（朱家庄模式）

        涨幅超风险幅度：
          调整金额 = 工程量 × (信息价 - 基准价 × (1 + 风险幅度)) × (1 + 税率)

        跌幅超风险幅度：
          调整金额 = 工程量 × (信息价 - 基准价 × (1 - 风险幅度)) × (1 + 税率)
        """
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.PERCENTAGE, 值=3))

        if not is_over_risk:
            return 0, "幅度内，不调差"

        if risk_config.类型 == RiskType.PERCENTAGE:
            upper = base_price * (1 + risk_config.值 / 100)
            lower = base_price * (1 - risk_config.值 / 100)
        else:
            upper = base_price + risk_config.值
            lower = base_price - risk_config.值

        amount = quantity * (avg_price - upper if is_rising else avg_price - lower)
        formula = f"{quantity} × [{avg_price} - {base_price} × {'1+' if is_rising else '1-'}{risk_config.值 / 100} = {upper if is_rising else lower}]"

        return amount, formula

    def _calculate_longhu_vat_conversion(
        self,
        material_name: str,
        quantity: float,
        base_price: float,
        avg_price: float,
        is_over_risk: bool,
        is_rising: bool
    ) -> Tuple[float, str]:
        """龙湖增值税率换算法（含税价与不含税价换算）

        钢筋（无风险幅度，全额调差）：
          调整金额 = {工程量 × [指导价 - 基价]} / (1 + 增值税率) × (1 + 合同税率)

        混凝土（有±3%风险幅度）：
          涨幅>3%：
            调整金额 = {工程量 × [指导价 - 基价 × 1.03]} / (1 + 增值税率) × (1 + 合同税率)
          跌幅>3%：
            调整金额 = {工程量 × [指导价 - 基价 × 0.97]} / (1 + 增值税率) × (1 + 合同税率)
          幅度内：
            调整金额 = 0
        """
        vat_rate = (self.config.增值税率 or 13) / 100
        contract_rate = (self.config.合同税率 or 9) / 100

        # 判断是钢筋还是混凝土
        is_rebar = '钢筋' in material_name
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.PERCENTAGE, 值=3))

        if is_rebar:
            # 钢筋：0%风险幅度，全额调差
            # 调整金额 = {工程量 × [指导价 - 基价]} / (1 + 增值税率) × (1 + 合同税率)
            amount = (quantity * (avg_price - base_price)) / (1 + vat_rate) * (1 + contract_rate)
            formula = f"{{{quantity} × [{avg_price} - {base_price}]}} / (1 + {vat_rate}) × (1 + {contract_rate})"
        else:
            # 混凝土：有风险幅度
            if not is_over_risk:
                return 0, "幅度内，不调差"

            threshold = 1 + risk_config.值 / 100  # 1.03 or 0.97
            if is_rising:
                # 涨幅超风险幅度
                amount = (quantity * (avg_price - base_price * threshold)) / (1 + vat_rate) * (1 + contract_rate)
                formula = f"{{{quantity} × [{avg_price} - {base_price} × {threshold}]}} / (1 + {vat_rate}) × (1 + {contract_rate})"
            else:
                # 跌幅超风险幅度
                threshold = 1 - risk_config.值 / 100
                amount = (quantity * (avg_price - base_price * threshold)) / (1 + vat_rate) * (1 + contract_rate)
                formula = f"{{{quantity} × [{avg_price} - {base_price} × {threshold}]}} / (1 + {vat_rate}) × (1 + {contract_rate})"

        return amount, formula

    def _calculate_adjustment(
        self,
        material_name: str,
        quantity: float,
        unit: str,
        base_price: float,
        avg_price: float,
        phase: str
    ) -> AdjustmentDetail:
        """
        Step 5: 代入公式计算
        支持5种调差公式模板
        """
        risk_config = self.config.风险幅度.get(material_name, RiskConfig(类型=RiskType.NONE, 值=0))

        # Step 4: 判断是否超幅度
        is_over_risk, is_rising, effective_diff = self._check_risk_threshold(
            material_name, base_price, avg_price
        )

        # 获取风险幅度显示
        risk_display = self._get_risk_display(risk_config)

        # 根据公式模板计算
        formula_type = self.config.调差公式模板

        if formula_type == FormulaType.NO_RISK:
            # 无风险幅度公式
            adjustment_amount, formula = self._calculate_no_risk(quantity, base_price, avg_price)

        elif formula_type == FormulaType.STANDARD_THREE_STAGE:
            # 标准三段式
            adjustment_amount, formula = self._calculate_standard_three_stage(
                material_name, quantity, base_price, avg_price, is_over_risk, is_rising
            )

        elif formula_type == FormulaType.RATIO_ADJUSTMENT:
            # 比例调差法（豪森模式）
            adjustment_amount, formula = self._calculate_ratio_adjustment(
                material_name, quantity, base_price, avg_price, is_over_risk, is_rising
            )

        elif formula_type == FormulaType.COST_INFO_ADJUSTMENT:
            # 造价信息调整法（朱家庄模式）
            adjustment_amount, formula = self._calculate_cost_info_adjustment(
                material_name, quantity, base_price, avg_price, is_over_risk, is_rising
            )

        elif formula_type == FormulaType.LONGHU_VAT_CONVERSION:
            # 龙湖增值税率换算法
            adjustment_amount, formula = self._calculate_longhu_vat_conversion(
                material_name, quantity, base_price, avg_price, is_over_risk, is_rising
            )

        else:
            # 自定义公式（暂不支持）
            adjustment_amount = 0
            formula = "自定义公式（暂不支持）"

        # 处理负数（跌价）
        adjustment_amount = self._handle_negative_adjustment(
            adjustment_amount, is_rising
        )

        # 计算含税金额（标准模式使用合同税率）
        tax_rate = self.config.税率 / 100
        tax_amount = adjustment_amount * tax_rate
        total_with_tax = adjustment_amount + tax_amount

        # 调整单价（不含税）
        adjustment_unit_price = adjustment_amount / quantity if quantity > 0 else 0

        return AdjustmentDetail(
            材料名称=material_name,
            阶段=phase,
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
            计算依据=f"基准价来源:{self.config.基准价来源}, 均价规则:{self.config.施工期价格采集规则 if isinstance(self.config.施工期价格采集规则, str) else '多材料规则'}"
        )

    def _handle_negative_adjustment(
        self,
        amount: float,
        is_rising: bool
    ) -> float:
        """处理负数调差（跌价情况）"""
        if amount >= 0:
            return amount

        if self.config.负数处理 == NegativeHandling.DEDUCT:
            # 扣回
            return amount
        elif self.config.负数处理 == NegativeHandling.NO_ADJUST:
            # 不调整
            return 0
        elif self.config.负数处理 == NegativeHandling.ACTUAL:
            # 按实计算
            return amount
        else:
            return amount

    # ============================================================
    # Step 5.5: 分阶段汇总（新增）
    # ============================================================

    def _summarize_by_phase(
        self,
        details: List[AdjustmentDetail]
    ) -> Dict[str, PhaseSummary]:
        """
        Step 5.5: 分阶段汇总

        按施工阶段分组统计调差金额

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
    # Step 6: 输出结果（优化版）
    # ============================================================

    def _format_output(
        self,
        details: List[AdjustmentDetail],
        project_name: str
    ) -> CalculationResult:
        """
        Step 6: 格式化输出 - 遵循v2.0输出格式标准

        优化内容：
        1. 增加分阶段汇总
        2. 增加价格校验信息
        """
        logger.info(f"[_format_output] 格式化输出 | details={len(details)}, project={project_name}")

        # 计算总金额
        total = sum(d.含税调整金额 for d in details)

        # 分阶段汇总
        self._summarize_by_phase(details)

        result = CalculationResult(
            项目名称=project_name,
            调差总金额=round(total, 2),
            明细=details,
            使用规则版本="v2.0",
            计算时间=datetime.now()
        )

        # 添加扩展属性（如果有需要）
        result_dict = result.model_dump()
        result_dict['阶段汇总'] = self._get_phase_summary_data()
        result_dict['价格校验'] = self._get_price_validation_summary()

        logger.info(f"[_format_output] 输出完成 | total={total:.2f}, phases={len(self.phase_summaries)}")

        # 返回增强版结果
        return CalculationResult(**result_dict)

    # ============================================================
    # 主计算方法（优化版：7步流程）
    # ============================================================

    def calculate(self, input_data: CalculationInput) -> CalculationResult:
        """
        执行完整的7步调差计算流程（优化版）

        Step 1: 读取配置 → 校验必填项
        Step 2: 取基准价
        Step 3: 取施工期均价
        Step 3.5: 价格数据校验（新增）
        Step 4: 判断是否超风险幅度
        Step 5: 代入公式计算
        Step 5.5: 分阶段汇总（新增）
        Step 6: 输出结果
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

            # Step 3.5: 价格数据校验（新增）
            logger.info("[calculate] Step 3.5: 价格数据校验")
            validation_results = self._validate_price_data(input_data)
            invalid_count = sum(1 for r in validation_results.values() if not r.is_valid)
            if invalid_count > 0:
                logger.warning(f"[calculate] 价格数据存在问题 | invalid_materials={invalid_count}")

            # 计算明细
            details = []

            for qty_data in input_data.quantities:
                material_name = qty_data.material_name
                phase = qty_data.phase or "整体"

                # 模糊匹配：检查材料名称是否在调差项目中
                matched_material = None
                for m in self.config.调差项目:
                    if material_name in m.名称 or m.名称 in material_name or '钢筋' in m.名称 and '钢筋' in material_name:
                        matched_material = m
                        break

                if not matched_material:
                    logger.warning(f"[calculate] 材料不在调差配置中，跳过 | material={material_name}")
                    continue

                # 检查工程量
                if qty_data.quantity <= 0:
                    raise AdjustmentCalculationError(
                        f"工程量必须大于0",
                        material=material_name,
                        phase=phase
                    )

                # 获取基准价和均价
                base_price = base_prices.get(material_name, 0)
                avg_price = avg_prices.get(material_name, 0)

                if base_price <= 0:
                    logger.warning(f"[calculate] 基准价为0，跳过 | material={material_name}")
                    continue

                # Step 4 & 5: 计算
                detail = self._calculate_adjustment(
                    material_name,
                    qty_data.quantity,
                    qty_data.unit,
                    base_price,
                    avg_price,
                    phase
                )
                details.append(detail)

            # Step 6: 输出结果
            return self._format_output(details, self.config.项目名称)

        except AdjustmentValidationError as e:
            logger.error(f"配置校验失败: {e.message}")
            raise
        except AdjustmentCalculationError as e:
            logger.error(f"计算错误: {e.message}")
            raise
        except Exception as e:
            logger.error(f"计算异常: {str(e)}")
            raise AdjustmentCalculationError(f"计算异常: {str(e)}")

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
    engine = AdjustmentEngine(rule_config)
    result = engine.calculate(input_data)

    # 转为字典
    return result.model_dump()
