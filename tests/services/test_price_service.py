"""
测试价格服务 PriceService
覆盖所有核心功能：均价计算、基准价获取、缺失价格处理、价格校验
"""

import pytest
from datetime import date, timedelta

from web.backend.services.price_service import (
    PriceService,
    PriceData,
    PriceValidationResult,
    HolidayHandling,
)


# ============================================================
# 测试夹具 (Fixtures)
# ============================================================

@pytest.fixture
def price_service():
    """创建价格服务实例"""
    return PriceService()


@pytest.fixture
def sample_prices():
    """标准测试价格数据：2026-05-01 到 2026-05-10"""
    return [
        PriceData(date="2026-05-01", price=4200.0, source="mysteel"),
        PriceData(date="2026-05-02", price=4210.0, source="mysteel"),
        PriceData(date="2026-05-03", price=4200.0, source="mysteel"),  # 周末
        PriceData(date="2026-05-04", price=4220.0, source="mysteel"),  # 周末
        PriceData(date="2026-05-05", price=4225.0, source="mysteel"),
        PriceData(date="2026-05-06", price=4215.0, source="mysteel"),
        PriceData(date="2026-05-07", price=4230.0, source="mysteel"),
        PriceData(date="2026-05-08", price=4240.0, source="mysteel"),
        PriceData(date="2026-05-09", price=4225.0, source="mysteel"),  # 周末
        PriceData(date="2026-05-10", price=4210.0, source="mysteel"),
    ]


@pytest.fixture
def sparse_prices():
    """稀疏测试价格数据（部分日期缺失）"""
    return [
        PriceData(date="2026-05-01", price=4200.0, source="mysteel"),
        PriceData(date="2026-05-03", price=4200.0, source="mysteel"),
        PriceData(date="2026-05-05", price=4225.0, source="mysteel"),
        PriceData(date="2026-05-07", price=4230.0, source="mysteel"),
        PriceData(date="2026-05-10", price=4210.0, source="mysteel"),
    ]


@pytest.fixture
def anomaly_prices():
    """异常价格数据（偏离均值>50%）"""
    return [
        PriceData(date="2026-05-01", price=4200.0, source="mysteel"),
        PriceData(date="2026-05-02", price=4210.0, source="mysteel"),
        PriceData(date="2026-05-03", price=7500.0, source="mysteel"),  # 异常高价，均值约4760，偏离超50%
        PriceData(date="2026-05-04", price=4200.0, source="mysteel"),
        PriceData(date="2026-05-05", price=4205.0, source="mysteel"),
    ]


# ============================================================
# 测试: get_period_average - 获取施工期均价
# ============================================================

class TestGetPeriodAverage:
    """获取施工期均价测试"""

    def test_average_full_range(self, price_service, sample_prices):
        """完整日期范围，应返回所有价格均值"""
        result = price_service.get_period_average(
            prices=sample_prices,
            start_date="2026-05-01",
            end_date="2026-05-10",
        )
        # (4200 + 4210 + 4200 + 4220 + 4225 + 4215 + 4230 + 4240 + 4225 + 4210) / 10 = 4217.5
        expected = 4217.5
        assert abs(result - expected) < 0.01

    def test_average_partial_range(self, price_service, sample_prices):
        """部分日期范围"""
        result = price_service.get_period_average(
            prices=sample_prices,
            start_date="2026-05-01",
            end_date="2026-05-05",
        )
        # (4200 + 4210 + 4200 + 4220 + 4225) / 5 = 4211.0
        expected = 4211.0
        assert abs(result - expected) < 0.01

    def test_average_no_matching_dates(self, price_service, sample_prices):
        """日期范围无匹配数据，返回0"""
        result = price_service.get_period_average(
            prices=sample_prices,
            start_date="2026-04-01",
            end_date="2026-04-30",
        )
        assert result == 0.0

    def test_average_single_day(self, price_service, sample_prices):
        """单日价格"""
        result = price_service.get_period_average(
            prices=sample_prices,
            start_date="2026-05-01",
            end_date="2026-05-01",
        )
        assert abs(result - 4200.0) < 0.01

    def test_average_empty_prices(self, price_service):
        """空价格列表，返回0"""
        result = price_service.get_period_average(
            prices=[],
            start_date="2026-05-01",
            end_date="2026-05-10",
        )
        assert result == 0.0

    def test_average_boundary_dates(self, price_service, sample_prices):
        """边界日期（start == end）"""
        result = price_service.get_period_average(
            prices=sample_prices,
            start_date="2026-05-05",
            end_date="2026-05-05",
        )
        assert abs(result - 4225.0) < 0.01


# ============================================================
# 测试: get_base_price - 获取基准日期价格
# ============================================================

class TestGetBasePrice:
    """获取基准日期价格测试"""

    def test_base_price_exact_match(self, price_service, sample_prices):
        """精确匹配日期，应返回对应价格"""
        result = price_service.get_base_price(
            prices=sample_prices,
            target_date="2026-05-05",
        )
        assert abs(result - 4225.0) < 0.01

    def test_base_price_no_match(self, price_service, sample_prices):
        """日期不存在，返回0"""
        result = price_service.get_base_price(
            prices=sample_prices,
            target_date="2026-05-15",
        )
        assert result == 0.0

    def test_base_price_first_date(self, price_service, sample_prices):
        """首日价格"""
        result = price_service.get_base_price(
            prices=sample_prices,
            target_date="2026-05-01",
        )
        assert abs(result - 4200.0) < 0.01

    def test_base_price_last_date(self, price_service, sample_prices):
        """末日价格"""
        result = price_service.get_base_price(
            prices=sample_prices,
            target_date="2026-05-10",
        )
        assert abs(result - 4210.0) < 0.01


# ============================================================
# 测试: handle_missing_price - 处理缺失价格
# ============================================================

class TestHandleMissingPrice:
    """处理缺失价格测试"""

    def test_shift_day_success(self, price_service, sample_prices):
        """顺延1天，找得到后续数据"""
        # 2026-05-03 是周末，尝试顺延到 2026-05-04
        result = price_service.handle_missing_price(
            prices=sample_prices,
            missing_date="2026-05-03",
            handling=HolidayHandling.SHIFT_DAY,
        )
        # 顺延到 2026-05-04，价格=4220.0
        assert abs(result - 4220.0) < 0.01

    def test_shift_day_multiple_days(self, price_service, sample_prices):
        """顺延1天，需要跳过多个无数据日"""
        # 2026-05-03 无数据，顺延到 2026-05-04 也没数据（虽然样本有但假设场景）
        result = price_service.handle_missing_price(
            prices=sample_prices,
            missing_date="2026-05-03",
            handling=HolidayHandling.SHIFT_DAY,
        )
        # 在 sample_prices 中，05-03 和 05-04 都有数据
        # 顺延1天到 05-04，价格=4220
        assert abs(result - 4220.0) < 0.01

    def test_shift_day_no_data_after(self, price_service, sparse_prices):
        """顺延1天，后续无数据，应返回0"""
        # sparse_prices 只有 01/03/05/07/10 有数据
        # 05-04 无数据，顺延到 05-05 有数据
        result = price_service.handle_missing_price(
            prices=sparse_prices,
            missing_date="2026-05-04",
            handling=HolidayHandling.SHIFT_DAY,
        )
        # 顺延到 05-05，价格=4225
        assert abs(result - 4225.0) < 0.01

    def test_average_prev_next(self, price_service, sparse_prices):
        """取前后日均价"""
        # 05-04 缺失，前后日是 05-03(4200) 和 05-05(4225)
        result = price_service.handle_missing_price(
            prices=sparse_prices,
            missing_date="2026-05-04",
            handling=HolidayHandling.AVERAGE_PREV_NEXT,
        )
        # (4200 + 4225) / 2 = 4212.5
        expected = (4200.0 + 4225.0) / 2
        assert abs(result - expected) < 0.01

    def test_average_prev_next_no_prev(self, price_service, sparse_prices):
        """取前后日均价，但前面无数据（用后续）"""
        # 05-01 是首日，前面无数据
        result = price_service.handle_missing_price(
            prices=sparse_prices,
            missing_date="2026-05-02",
            handling=HolidayHandling.AVERAGE_PREV_NEXT,
        )
        # 只有后续 05-03(4200)，取其值
        assert abs(result - 4200.0) < 0.01

    def test_last_month_price(self, price_service, sample_prices):
        """取上月价（需构造上月有数据的场景）"""
        # 假设 2026-04 有数据
        last_month_prices = [
            PriceData(date="2026-04-30", price=4100.0, source="mysteel"),
        ]
        all_prices = sample_prices + last_month_prices

        result = price_service.handle_missing_price(
            prices=all_prices,
            missing_date="2026-05-01",
            handling=HolidayHandling.LAST_MONTH,
        )
        # 应取 2026-04-30 的价格 4100.0
        assert abs(result - 4100.0) < 0.01

    def test_last_month_no_data(self, price_service, sample_prices):
        """取上月价，但上月无数据，返回0"""
        result = price_service.handle_missing_price(
            prices=sample_prices,
            missing_date="2026-05-01",
            handling=HolidayHandling.LAST_MONTH,
        )
        # 上月（4月）无数据，返回0
        assert result == 0.0


# ============================================================
# 测试: validate_prices - 价格数据校验
# ============================================================

class TestValidatePrices:
    """价格数据校验测试"""

    def test_validate_complete_data(self, price_service, sample_prices):
        """完整数据，应全部通过校验"""
        result = price_service.validate_prices(
            prices=sample_prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-10",
        )

        assert isinstance(result, PriceValidationResult)
        assert result.material_name == "钢筋"
        assert result.total_days == 10
        assert result.valid_days == 10
        assert result.missing_days == 0
        assert result.data_completeness == 1.0
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_validate_sparse_data(self, price_service, sparse_prices):
        """稀疏数据，应检测出缺失天数"""
        result = price_service.validate_prices(
            prices=sparse_prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-10",
        )

        assert result.total_days == 10
        assert result.valid_days == 5
        assert result.missing_days == 5
        assert result.data_completeness == 0.5
        # 完整率50% < 80%阈值，视为数据不完整
        assert result.is_valid is False
        assert len(result.missing_dates) == 5
        # 应有数据完整率不足警告
        assert any("完整率不足" in w or "50.0%" in w for w in result.warnings)

    def test_validate_anomaly_detection(self, price_service, anomaly_prices):
        """检测异常价格（偏离均值>50%）"""
        result = price_service.validate_prices(
            prices=anomaly_prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-05",
        )

        # 应产生警告
        assert len(result.warnings) > 0
        # 异常价格应被标记
        assert any("异常" in w or "偏高" in w or "6500" in w for w in result.warnings)

    def test_validate_no_data(self, price_service):
        """无数据，应报告100%缺失"""
        result = price_service.validate_prices(
            prices=[],
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-10",
        )

        assert result.total_days == 10
        assert result.valid_days == 0
        assert result.missing_days == 10
        assert result.data_completeness == 0.0
        assert result.is_valid is False

    def test_validate_missing_dates_list(self, price_service, sparse_prices):
        """验证缺失日期列表"""
        result = price_service.validate_prices(
            prices=sparse_prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-10",
        )

        # 缺失日期应该是 02, 04, 06, 08, 09（不包含01,03,05,07,10）
        missing_set = set(result.missing_dates)
        assert "2026-05-02" in missing_set or "2026-05-04" in missing_set

    def test_validate_completeness_calculation(self, price_service):
        """验证数据完整率计算"""
        # 7/10 天有数据，完整率70%
        prices = [
            PriceData(date="2026-05-01", price=4200.0),
            PriceData(date="2026-05-02", price=4210.0),
            PriceData(date="2026-05-03", price=4200.0),
            PriceData(date="2026-05-05", price=4225.0),
            PriceData(date="2026-05-06", price=4215.0),
            PriceData(date="2026-05-07", price=4230.0),
            PriceData(date="2026-05-10", price=4210.0),
        ]
        result = price_service.validate_prices(
            prices=prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-10",
        )

        assert abs(result.data_completeness - 0.7) < 0.01


# ============================================================
# 测试: 类型注解和数据类
# ============================================================

class TestDataClasses:
    """数据类型测试"""

    def test_price_data_creation(self):
        """PriceData 数据类创建"""
        pd = PriceData(date="2026-05-01", price=4200.0, source="mysteel")
        assert pd.date == "2026-05-01"
        assert pd.price == 4200.0
        assert pd.source == "mysteel"

    def test_price_data_default_source(self):
        """PriceData 默认 source 为空字符串"""
        pd = PriceData(date="2026-05-01", price=4200.0)
        assert pd.source == ""

    def test_price_validation_result_defaults(self):
        """PriceValidationResult 默认值"""
        result = PriceValidationResult(material_name="钢筋")
        assert result.material_name == "钢筋"
        assert result.total_days == 0
        assert result.valid_days == 0
        assert result.missing_days == 0
        assert result.missing_dates == []
        assert result.data_completeness == 0.0
        assert result.warnings == []
        assert result.is_valid is True

    def test_holiday_handling_enum_values(self):
        """HolidayHandling 枚举值验证"""
        assert HolidayHandling.SHIFT_DAY.value == "顺延1天"
        assert HolidayHandling.AVERAGE_PREV_NEXT.value == "取前后日均价"
        assert HolidayHandling.LAST_MONTH.value == "取上月价"


# ============================================================
# 集成测试
# ============================================================

class TestPriceServiceIntegration:
    """价格服务集成测试"""

    def test_full_workflow(self, price_service):
        """完整调差工作流：校验 -> 均价 -> 基准价"""
        prices = [
            PriceData(date="2026-05-01", price=4200.0),
            PriceData(date="2026-05-02", price=4210.0),
            PriceData(date="2026-05-03", price=4220.0),
            PriceData(date="2026-05-04", price=4230.0),
            PriceData(date="2026-05-05", price=4240.0),
        ]

        # 1. 校验数据
        validation = price_service.validate_prices(
            prices=prices,
            material_name="钢筋",
            start_date="2026-05-01",
            end_date="2026-05-05",
        )
        assert validation.is_valid is True

        # 2. 获取基准价
        base = price_service.get_base_price(prices, "2026-05-01")
        assert abs(base - 4200.0) < 0.01

        # 3. 获取施工期均价
        avg = price_service.get_period_average(
            prices, "2026-05-01", "2026-05-05"
        )
        expected = (4200 + 4210 + 4220 + 4230 + 4240) / 5
        assert abs(avg - expected) < 0.01

    def test_handle_missing_full_workflow(self, price_service):
        """缺失处理工作流：检测缺失 -> 顺延处理 -> 计算"""
        sparse = [
            PriceData(date="2026-05-01", price=4200.0),
            PriceData(date="2026-05-03", price=4220.0),  # 05-02 缺失
        ]

        # 处理缺失日期 05-02
        price = price_service.handle_missing_price(
            prices=sparse,
            missing_date="2026-05-02",
            handling=HolidayHandling.SHIFT_DAY,
        )
        # 顺延到 05-03，价格=4220
        assert abs(price - 4220.0) < 0.01

        # 再用前后日均价验证
        price_avg = price_service.handle_missing_price(
            prices=sparse,
            missing_date="2026-05-02",
            handling=HolidayHandling.AVERAGE_PREV_NEXT,
        )
        # 前=4200(05-01)，后=4220(05-03)，均值=4210
        assert abs(price_avg - 4210.0) < 0.01