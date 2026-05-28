"""
调差计算服务 - 单次调差计算模块

提供基础调差计算功能，支持风险幅度和税率配置
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


class AdjustmentCalculator:
    """
    工程调差计算器

    提供简单调差计算功能，支持风险幅度扣除和税率计算
    """

    def __init__(self, risk_percent: float = 0, risk_fixed: float = 0, tax_rate: float = 0.09):
        """
        初始化调差计算器

        Args:
            risk_percent: 风险幅度百分比(%)，默认为0
            risk_fixed: 风险幅度固定金额，默认为0
            tax_rate: 增值税率，默认为9%(0.09)
        """
        logger.info(f"[AdjustmentCalculator] 初始化 | risk_percent={risk_percent}%, risk_fixed={risk_fixed}, tax_rate={tax_rate}")
        self.risk_percent = risk_percent
        self.risk_fixed = risk_fixed
        self.tax_rate = tax_rate

    def calculate(
        self,
        base_price: float,
        current_price: float,
        quantity: float
    ) -> Dict[str, float]:
        """
        计算调差金额（基于实例配置）

        Args:
            base_price: 基准价格
            current_price: 当前价格
            quantity: 工程量

        Returns:
            调差计算结果字典
        """
        logger.info(f"[calculate] 开始计算 | base_price={base_price}, current_price={current_price}, quantity={quantity}")
        logger.debug(f"[calculate] 实例配置 | risk_percent={self.risk_percent}%, risk_fixed={self.risk_fixed}, tax_rate={self.tax_rate}")

        try:
            # 计算价差
            price_diff = current_price - base_price

            # 计算价格变化率(%)
            price_change_rate = (price_diff / base_price * 100) if base_price > 0 else 0.0

            # 计算基础调差金额（不含税）
            base_adjustment = price_diff * quantity

            # 计算风险调差金额
            # 风险幅度：超过阈值部分才计入调差
            risk_adjustment = 0.0
            if self.risk_percent > 0:
                # 百分比风险幅度
                threshold = base_price * (self.risk_percent / 100)
                if abs(price_diff) > threshold:
                    # 超过阈值的部分
                    effective_diff = price_diff - (threshold if price_diff > 0 else -threshold)
                    risk_adjustment = effective_diff * quantity
            elif self.risk_fixed > 0:
                # 固定金额风险幅度
                if abs(price_diff) > self.risk_fixed:
                    # 超过阈值的部分
                    effective_diff = price_diff - (self.risk_fixed if price_diff > 0 else -self.risk_fixed)
                    risk_adjustment = effective_diff * quantity
            else:
                # 无风险幅度，全部调差
                risk_adjustment = base_adjustment

            # 计算税前金额
            pre_tax = risk_adjustment

            # 计算税额
            tax = pre_tax * self.tax_rate

            # 计算含税总额
            total = pre_tax + tax

            # 使用Decimal确保精度
            result = {
                'base_price': round(base_price, 2),
                'current_price': round(current_price, 2),
                'price_diff': round(price_diff, 2),
                'price_change_rate': round(price_change_rate, 2),
                'quantity': round(quantity, 2),
                'base_adjustment': round(base_adjustment, 2),
                'risk_adjustment': round(risk_adjustment, 2),
                'pre_tax': round(pre_tax, 2),
                'tax': round(tax, 2),
                'total': round(total, 2)
            }

            logger.info(f"[calculate] 计算完成 | price_change_rate={result['price_change_rate']}%, total={result['total']}")
            return result

        except Exception as e:
            logger.error(f"[calculate] 计算失败 | {type(e).__name__}: {e}", exc_info=True)
            raise

    def calculate_simple(
        self,
        base_price: float,
        avg_price: float,
        quantity: float,
        risk_percent: float,
        risk_fixed: float,
        tax_rate: float
    ) -> Dict[str, float]:
        """
        简单调差计算（直接传入参数）

        Args:
            base_price: 基准价格
            avg_price: 施工期平均价格
            quantity: 工程量
            risk_percent: 风险幅度百分比(%)
            risk_fixed: 风险幅度固定金额
            tax_rate: 增值税率

        Returns:
            调差计算结果字典
        """
        logger.info(f"[calculate_simple] 开始计算 | base_price={base_price}, avg_price={avg_price}, quantity={quantity}")
        logger.debug(f"[calculate_simple] 参数 | risk_percent={risk_percent}%, risk_fixed={risk_fixed}, tax_rate={tax_rate}")

        try:
            # 计算价差
            price_diff = avg_price - base_price

            # 计算价格变化率(%)
            price_change_rate = (price_diff / base_price * 100) if base_price > 0 else 0.0

            # 计算基础调差金额（不含税）
            base_adjustment = price_diff * quantity

            # 计算风险调差金额
            risk_adjustment = 0.0
            if risk_percent > 0:
                # 百分比风险幅度
                threshold = base_price * (risk_percent / 100)
                if abs(price_diff) > threshold:
                    effective_diff = price_diff - (threshold if price_diff > 0 else -threshold)
                    risk_adjustment = effective_diff * quantity
            elif risk_fixed > 0:
                # 固定金额风险幅度
                if abs(price_diff) > risk_fixed:
                    effective_diff = price_diff - (risk_fixed if price_diff > 0 else -risk_fixed)
                    risk_adjustment = effective_diff * quantity
            else:
                # 无风险幅度，全部调差
                risk_adjustment = base_adjustment

            # 计算税前金额
            pre_tax = risk_adjustment

            # 计算税额
            tax = pre_tax * tax_rate

            # 计算含税总额
            total = pre_tax + tax

            result = {
                'base_price': round(base_price, 2),
                'current_price': round(avg_price, 2),
                'price_diff': round(price_diff, 2),
                'price_change_rate': round(price_change_rate, 2),
                'quantity': round(quantity, 2),
                'base_adjustment': round(base_adjustment, 2),
                'risk_adjustment': round(risk_adjustment, 2),
                'pre_tax': round(pre_tax, 2),
                'tax': round(tax, 2),
                'total': round(total, 2)
            }

            logger.info(f"[calculate_simple] 计算完成 | price_change_rate={result['price_change_rate']}%, total={result['total']}")
            return result

        except Exception as e:
            logger.error(f"[calculate_simple] 计算失败 | {type(e).__name__}: {e}", exc_info=True)
            raise

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证调差配置参数

        Args:
            config: 配置字典

        Returns:
            验证结果 {'valid': bool, 'errors': List[str]}
        """
        logger.info(f"[validate_config] 验证配置 | config_keys={list(config.keys())}")

        errors = []

        # 验证风险幅度
        risk_percent = config.get('risk_percent', 0)
        risk_fixed = config.get('risk_fixed', 0)

        if not isinstance(risk_percent, (int, float)):
            errors.append("risk_percent必须是数字类型")
        elif risk_percent < 0 or risk_percent > 100:
            errors.append("risk_percent必须在0-100之间")

        if not isinstance(risk_fixed, (int, float)):
            errors.append("risk_fixed必须是数字类型")
        elif risk_fixed < 0:
            errors.append("risk_fixed不能为负数")

        # 不能同时设置百分比和固定金额风险幅度
        if risk_percent > 0 and risk_fixed > 0:
            errors.append("风险幅度不能同时设置百分比和固定金额")

        # 验证税率
        tax_rate = config.get('tax_rate', 0.09)
        if not isinstance(tax_rate, (int, float)):
            errors.append("tax_rate必须是数字类型")
        elif tax_rate < 0 or tax_rate > 1:
            errors.append("tax_rate必须在0-1之间（表示百分比，如0.09表示9%）")

        # 验证价格
        base_price = config.get('base_price')
        if base_price is not None:
            if not isinstance(base_price, (int, float)):
                errors.append("base_price必须是数字类型")
            elif base_price <= 0:
                errors.append("base_price必须大于0")

        # 验证工程量
        quantity = config.get('quantity')
        if quantity is not None:
            if not isinstance(quantity, (int, float)):
                errors.append("quantity必须是数字类型")
            elif quantity < 0:
                errors.append("quantity不能为负数")

        result = {
            'valid': len(errors) == 0,
            'errors': errors
        }

        if result['valid']:
            logger.info("[validate_config] 配置验证通过")
        else:
            logger.warning(f"[validate_config] 配置验证失败 | errors={errors}")

        return result


# 用于快速计算的辅助函数
def quick_calculate(
    base_price: float,
    avg_price: float,
    quantity: float,
    risk_percent: float = 5.0,
    tax_rate: float = 0.09
) -> Dict[str, float]:
    """
    快速调差计算（便捷函数）

    默认使用5%风险幅度，适用于常见钢材调差场景

    Args:
        base_price: 基准价格
        avg_price: 施工期平均价格
        quantity: 工程量
        risk_percent: 风险幅度百分比，默认5%
        tax_rate: 增值税率，默认9%

    Returns:
        调差计算结果字典
    """
    logger.info(f"[quick_calculate] 快速计算 | base={base_price}, avg={avg_price}, qty={quantity}")
    calculator = AdjustmentCalculator(risk_percent=risk_percent, tax_rate=tax_rate)
    return calculator.calculate_simple(
        base_price=base_price,
        avg_price=avg_price,
        quantity=quantity,
        risk_percent=risk_percent,
        risk_fixed=0,
        tax_rate=tax_rate
    )