"""
价格服务 PriceService
提供价格数据处理的核心功能：
1. 获取施工期均价
2. 获取基准日期价格
3. 处理缺失价格（顺延/均价/上月价）
4. 价格数据校验

依赖: models/adjustment_rules.HolidayHandling
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

# 从 adjustment_rules 导入 HolidayHandling 枚举
from models.adjustment_rules import HolidayHandling

logger = logging.getLogger(__name__)


# ============================================================
# 数据类定义
# ============================================================

@dataclass
class PriceData:
    """价格数据"""
    date: str          # YYYY-MM-DD 格式
    price: float
    source: str = ""   # 数据来源


@dataclass
class PriceValidationResult:
    """价格校验结果"""
    material_name: str
    total_days: int = 0          # 总天数
    valid_days: int = 0          # 有效天数
    missing_days: int = 0        # 缺失天数
    missing_dates: List[str] = field(default_factory=list)  # 缺失日期列表
    data_completeness: float = 0.0  # 数据完整率 0.0-1.0
    warnings: List[str] = field(default_factory=list)       # 警告列表
    is_valid: bool = True        # 是否有效（数据完整率>=80%视为有效）


# ============================================================
# 价格服务类
# ============================================================

class PriceService:
    """
    价格服务 - 提供价格数据处理的核心功能

    提供的功能：
    - get_period_average: 计算施工期均价
    - get_base_price: 获取基准日期价格
    - handle_missing_price: 处理缺失价格
    - validate_prices: 校验价格数据完整性
    """

    def __init__(self):
        """初始化价格服务"""
        logger.info("[PriceService] 价格服务初始化")

    def get_period_average(
        self,
        prices: List[PriceData],
        start_date: str,
        end_date: str,
    ) -> float:
        """
        获取施工期均价

        按时间范围过滤价格数据，计算算术平均值。

        Args:
            prices: 价格数据列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            float: 算术平均值，如无数据返回 0.0

        Examples:
            >>> prices = [PriceData("2026-05-01", 4200.0), PriceData("2026-05-02", 4210.0)]
            >>> service.get_period_average(prices, "2026-05-01", "2026-05-02")
            4205.0
        """
        logger.info(
            f"[get_period_average] 计算施工期均价 | start={start_date}, end={end_date}, "
            f"total_prices={len(prices)}"
        )

        if not prices:
            logger.info("[get_period_average] 空价格列表，返回 0.0")
            return 0.0

        # 过滤日期范围内的价格
        filtered = [
            p.price for p in prices
            if start_date <= p.date <= end_date
        ]

        if not filtered:
            logger.info(f"[get_period_average] 无匹配数据，返回 0.0 | range={start_date} to {end_date}")
            return 0.0

        # 计算算术平均值
        avg = sum(filtered) / len(filtered)
        logger.info(
            f"[get_period_average] 计算完成 | count={len(filtered)}, average={avg:.2f}"
        )
        return avg

    def get_base_price(
        self,
        prices: List[PriceData],
        target_date: str,
    ) -> float:
        """
        获取基准日期价格

        精确匹配日期，找不到返回 0。

        Args:
            prices: 价格数据列表
            target_date: 目标日期 (YYYY-MM-DD)

        Returns:
            float: 匹配的价格，如无数据返回 0.0

        Examples:
            >>> prices = [PriceData("2026-05-01", 4200.0)]
            >>> service.get_base_price(prices, "2026-05-01")
            4200.0
        """
        logger.info(f"[get_base_price] 获取基准价 | target_date={target_date}, total={len(prices)}")

        for p in prices:
            if p.date == target_date:
                logger.info(f"[get_base_price] 找到匹配价格 | date={target_date}, price={p.price}")
                return p.price

        logger.info(f"[get_base_price] 未找到匹配日期，返回 0.0 | date={target_date}")
        return 0.0

    def handle_missing_price(
        self,
        prices: List[PriceData],
        missing_date: str,
        handling: HolidayHandling,
    ) -> float:
        """
        处理缺失价格

        根据配置的处理规则获取替代价格。

        Args:
            prices: 价格数据列表
            missing_date: 缺失日期 (YYYY-MM-DD)
            handling: 处理方式 (SHIFT_DAY / AVERAGE_PREV_NEXT / LAST_MONTH)

        Returns:
            float: 替代价格，如无法处理返回 0.0

        处理规则：
        - SHIFT_DAY: 顺延1天，取下一个有数据的工作日价格
        - AVERAGE_PREV_NEXT: 取前后日均价
        - LAST_MONTH: 取上月最后一天价格
        """
        logger.info(
            f"[handle_missing_price] 处理缺失价格 | date={missing_date}, "
            f"handling={handling.value}"
        )

        if handling == HolidayHandling.SHIFT_DAY:
            return self._shift_day(prices, missing_date)

        elif handling == HolidayHandling.AVERAGE_PREV_NEXT:
            return self._average_prev_next(prices, missing_date)

        elif handling == HolidayHandling.LAST_MONTH:
            return self._last_month_price(prices, missing_date)

        else:
            logger.warning(f"[handle_missing_price] 未知处理方式，返回 0.0 | handling={handling}")
            return 0.0

    def _shift_day(self, prices: List[PriceData], missing_date: str) -> float:
        """
        顺延1天处理缺失价格

        顺延到下一个有数据的日期（最多顺延30天）。
        """
        logger.debug(f"[_shift_day] 顺延处理 | missing={missing_date}")

        # 解析缺失日期
        try:
            current = datetime.strptime(missing_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"[_shift_day] 日期格式错误 | date={missing_date}, error={e}")
            return 0.0

        # 构建日期->价格映射
        date_price_map = {p.date: p.price for p in prices}

        # 顺延查找（最多30天）
        for i in range(1, 31):
            next_date = current + timedelta(days=i)
            next_date_str = next_date.strftime("%Y-%m-%d")

            if next_date_str in date_price_map:
                price = date_price_map[next_date_str]
                logger.info(f"[_shift_day] 找到顺延价格 | original={missing_date}, shifted={next_date_str}, price={price}")
                return price

        logger.warning(f"[_shift_day] 顺延30天内无数据 | missing={missing_date}")
        return 0.0

    def _average_prev_next(self, prices: List[PriceData], missing_date: str) -> float:
        """
        取前后日均价处理缺失价格

        计算前后日价格的算术平均值。
        如果只有一边有数据，返回单边价格。
        如果两边都无数据，返回0。
        """
        logger.debug(f"[_average_prev_next] 前后日均价处理 | missing={missing_date}")

        # 解析缺失日期
        try:
            current = datetime.strptime(missing_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"[_average_prev_next] 日期格式错误 | date={missing_date}, error={e}", exc_info=True)
            return 0.0

        # 构建日期->价格映射
        date_price_map = {p.date: p.price for p in prices}

        # 获取前一天和后一天
        prev_date = current - timedelta(days=1)
        next_date = current + timedelta(days=1)

        prev_price = date_price_map.get(prev_date.strftime("%Y-%m-%d"))
        next_price = date_price_map.get(next_date.strftime("%Y-%m-%d"))

        # 计算均值
        if prev_price is not None and next_price is not None:
            avg = (prev_price + next_price) / 2
            logger.info(f"[_average_prev_next] 前后日均价 | prev={prev_price}, next={next_price}, avg={avg}")
            return avg
        elif prev_price is not None:
            logger.info(f"[_average_prev_next] 仅前一日有数据 | prev={prev_price}")
            return prev_price
        elif next_price is not None:
            logger.info(f"[_average_prev_next] 仅后一日有数据 | next={next_price}")
            return next_price
        else:
            logger.warning(f"[_average_prev_next] 前后日都无数据 | missing={missing_date}")
            return 0.0

    def _last_month_price(self, prices: List[PriceData], missing_date: str) -> float:
        """
        取上月价处理缺失价格

        获取上月最后一天的价格。
        """
        logger.debug(f"[_last_month_price] 取上月价处理 | missing={missing_date}")

        # 解析缺失日期
        try:
            current = datetime.strptime(missing_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"[_last_month_price] 日期格式错误 | date={missing_date}, error={e}", exc_info=True)
            return 0.0

        # 计算上月最后一天
        first_of_current = current.replace(day=1)
        last_of_prev_month = first_of_current - timedelta(days=1)
        last_month_date_str = last_of_prev_month.strftime("%Y-%m-%d")

        # 查找上月最后一天的价格
        for p in prices:
            if p.date == last_month_date_str:
                logger.info(f"[_last_month_price] 找到上月价格 | last_month={last_month_date_str}, price={p.price}")
                return p.price

        logger.warning(f"[_last_month_price] 上月无数据 | missing={missing_date}, last_month={last_month_date_str}")
        return 0.0

    def validate_prices(
        self,
        prices: List[PriceData],
        material_name: str,
        start_date: str,
        end_date: str,
        anomaly_threshold: float = 0.5,  # 偏离均值50%视为异常
    ) -> PriceValidationResult:
        """
        校验价格数据

        检查数据完整性，检测异常价格。

        Args:
            prices: 价格数据列表
            material_name: 材料名称
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            anomaly_threshold: 异常阈值（偏离均值比例），默认50%

        Returns:
            PriceValidationResult: 校验结果

        校验项目：
        - 统计有效数据天数
        - 计算缺失天数和日期
        - 检测异常价格（偏离均值 > threshold）
        - 计算数据完整率
        """
        logger.info(
            f"[validate_prices] 校验价格数据 | material={material_name}, "
            f"range={start_date} to {end_date}, total_prices={len(prices)}"
        )

        # 解析日期范围
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"[validate_prices] 日期格式错误 | error={e}", exc_info=True)
            return PriceValidationResult(
                material_name=material_name,
                warnings=[f"日期格式错误: {e}"],
                is_valid=False,
            )

        # 计算总天数
        total_days = (end - start).days + 1

        # 构建日期->价格映射
        date_price_map = {p.date: p.price for p in prices}

        # 统计有效天数和缺失日期
        valid_count = 0
        missing_dates_list = []

        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in date_price_map:
                valid_count += 1
            else:
                missing_dates_list.append(date_str)
            current += timedelta(days=1)

        missing_count = total_days - valid_count

        # 计算数据完整率
        completeness = valid_count / total_days if total_days > 0 else 0.0

        # 检测异常价格
        warnings = []
        if prices:
            all_prices = [p.price for p in prices]
            avg_price = sum(all_prices) / len(all_prices)

            for p in prices:
                if avg_price > 0:
                    deviation = abs(p.price - avg_price) / avg_price
                    if deviation > anomaly_threshold:
                        warning_msg = (
                            f"异常价格: {p.date} {material_name} "
                            f"价格={p.price}元，偏离均价={deviation*100:.1f}%"
                        )
                        warnings.append(warning_msg)
                        logger.warning(f"[validate_prices] {warning_msg}")

        # 判断有效性：完整率 >= 80% 视为有效
        is_valid = completeness >= 0.8

        if not is_valid:
            warnings.append(f"数据完整率不足: {completeness*100:.1f}% < 80%")

        result = PriceValidationResult(
            material_name=material_name,
            total_days=total_days,
            valid_days=valid_count,
            missing_days=missing_count,
            missing_dates=missing_dates_list,
            data_completeness=round(completeness, 4),
            warnings=warnings,
            is_valid=is_valid,
        )

        logger.info(
            f"[validate_prices] 校验完成 | valid={valid_count}, missing={missing_count}, "
            f"completeness={completeness*100:.1f}%, is_valid={is_valid}"
        )

        return result

    def get_price_by_date_range(
        self,
        prices: List[PriceData],
        start_date: str,
        end_date: str,
    ) -> List[PriceData]:
        """
        获取日期范围内的所有价格数据

        Args:
            prices: 价格数据列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            List[PriceData]: 筛选后的价格数据列表
        """
        logger.debug(
            f"[get_price_by_date_range] 筛选价格数据 | "
            f"range={start_date} to {end_date}, total={len(prices)}"
        )

        filtered = [p for p in prices if start_date <= p.date <= end_date]
        logger.debug(f"[get_price_by_date_range] 筛选完成 | filtered={len(filtered)}")
        return filtered

    def fill_missing_prices(
        self,
        prices: List[PriceData],
        start_date: str,
        end_date: str,
        handling: HolidayHandling = HolidayHandling.SHIFT_DAY,
    ) -> List[PriceData]:
        """
        填充缺失价格

        根据日期范围填充所有缺失日期的价格。

        Args:
            prices: 价格数据列表
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            handling: 缺失处理方式

        Returns:
            List[PriceData]: 包含填充后价格的完整列表
        """
        logger.info(
            f"[fill_missing_prices] 填充缺失价格 | "
            f"range={start_date} to {end_date}, handling={handling.value}"
        )

        # 获取日期范围内的所有价格
        existing_prices = self.get_price_by_date_range(prices, start_date, end_date)

        # 构建日期->价格映射
        date_price_map = {p.date: p.price for p in existing_prices}

        # 填充缺失日期
        result_prices = list(existing_prices)

        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"[fill_missing_prices] 日期格式错误 | error={e}", exc_info=True)
            return result_prices

        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in date_price_map:
                # 处理缺失价格
                filled_price = self.handle_missing_price(
                    prices=prices,
                    missing_date=date_str,
                    handling=handling,
                )
                if filled_price > 0:
                    result_prices.append(PriceData(
                        date=date_str,
                        price=filled_price,
                        source=f"filled_{handling.value}",
                    ))
                    logger.debug(f"[fill_missing_prices] 填充价格 | date={date_str}, price={filled_price}")
            current += timedelta(days=1)

        logger.info(f"[fill_missing_prices] 填充完成 | original={len(existing_prices)}, filled={len(result_prices)}")
        return result_prices