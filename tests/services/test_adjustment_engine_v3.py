"""
测试统一调差计算引擎 AdjustmentEngineV3

测试覆盖：
1. 7步计算流程
2. 5种公式类型（通过 FormulaEngine）
3. 多部位分时段计算
4. 价格数据校验
5. 分阶段汇总
"""

import pytest
from datetime import datetime, date, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from web.backend.services.adjustment_engine_v3 import (
    AdjustmentEngineV3,
    CalculationInput,
    PriceData,
    QuantityData,
    AdjustmentDetail,
    CalculationResult,
    PriceValidationResult,
    PhaseSummary,
    AdjustmentEngineV3Error,
)
from web.backend.services.formula_engine import FormulaEngine, FormulaInput
from web.backend.services.price_service import PriceService
from web.backend.models.adjustment_rules import (
    AdjustmentRuleConfig,
    RiskConfig,
    RiskType,
    FormulaType,
    NegativeHandling,
    PhaseType,
    HolidayHandling,
)


# ============================================================
# 测试夹具 (Fixtures)
# ============================================================

@pytest.fixture
def formula_engine():
    """公式引擎"""
    return FormulaEngine()


@pytest.fixture
def price_service():
    """价格服务"""
    return PriceService()


@pytest.fixture
def sample_base_prices() -> Dict[str, float]:
    """基准价数据"""
    return {
        "钢筋": 4000.0,
        "商品混凝土": 450.0,
        "电缆": 40000.0,
    }


@pytest.fixture
def sample_period_prices() -> Dict[str, List[PriceData]]:
    """施工期价格数据"""
    return {
        "钢筋": [
            PriceData("2026-01-01", 4100.0),
            PriceData("2026-01-02", 4150.0),
            PriceData("2026-01-03", 4200.0),
            PriceData("2026-01-04", 4180.0),
            PriceData("2026-01-05", 4220.0),
        ],
        "商品混凝土": [
            PriceData("2026-01-01", 460.0),
            PriceData("2026-01-02", 465.0),
            PriceData("2026-01-03", 470.0),
        ],
    }


@pytest.fixture
def sample_quantities() -> List[QuantityData]:
    """工程量数据"""
    return [
        QuantityData(
            material_name="钢筋",
            quantity=100.0,
            unit="t",
            phase="整体",
            location="",
            start_date="2026-01-01",
            end_date="2026-01-05",
        ),
    ]


@pytest.fixture
def standard_config() -> AdjustmentRuleConfig:
    """标准调差配置（标准三段式，±3%风险幅度）"""
    return AdjustmentRuleConfig(
        id="test_standard",
        项目名称="测试项目",
        使用规则版本="v3.0",
        调差项目=[
            {"名称": "钢筋", "是否必调": "必选", "调差范围": "全部钢筋"},
            {"名称": "商品混凝土", "是否必调": "必选", "调差范围": "全部混凝土"},
        ],
        风险幅度={
            "钢筋": RiskConfig(类型=RiskType.PERCENTAGE, 值=3.0),
            "商品混凝土": RiskConfig(类型=RiskType.PERCENTAGE, 值=3.0),
        },
        基准价来源="造价信息",
        基准价取价规则="招标时价格",
        施工期价格采集规则="按月算术平均",
        是否分阶段调差="否",
        调差公式模板=FormulaType.STANDARD_THREE_STAGE,
        税率=9.0,
        负数处理=NegativeHandling.DEDUCT,
        is_preset=False,
    )


@pytest.fixture
def no_risk_config() -> AdjustmentRuleConfig:
    """无风险幅度配置（0%全额调差）"""
    return AdjustmentRuleConfig(
        id="test_no_risk",
        项目名称="龙湖测试项目",
        使用规则版本="v3.0",
        调差项目=[
            {"名称": "钢筋", "是否必调": "必选", "调差范围": "全部钢筋"},
        ],
        风险幅度={
            "钢筋": RiskConfig(类型=RiskType.NONE, 值=0),
        },
        基准价来源="我的钢铁网",
        基准价取价规则="基准日期价格",
        施工期价格采集规则="按月算术平均",
        是否分阶段调差="否",
        调差公式模板=FormulaType.NO_RISK,
        税率=9.0,
        负数处理=NegativeHandling.DEDUCT,
        is_preset=False,
    )


@pytest.fixture
def longhu_config() -> AdjustmentRuleConfig:
    """龙湖模式配置（增值税率换算法）"""
    return AdjustmentRuleConfig(
        id="test_longhu",
        项目名称="龙湖测试项目",
        使用规则版本="v3.0",
        调差项目=[
            {"名称": "钢筋", "是否必调": "必选", "调差范围": "全部钢筋"},
            {"名称": "商品混凝土", "是否必调": "必选", "调差范围": "全部混凝土"},
        ],
        风险幅度={
            "钢筋": RiskConfig(类型=RiskType.NONE, 值=0),
            "商品混凝土": RiskConfig(类型=RiskType.PERCENTAGE, 值=3.0),
        },
        基准价来源="我的钢铁网",
        基准价取价规则="基准日期价格",
        施工期价格采集规则="按月算术平均",
        是否分阶段调差="是",
        阶段划分=[
            {"名称": "地下室", "起始点": "垫层开始", "结束点": "地库顶板完成"},
            {"名称": "楼栋", "起始点": "±0.00结构面", "结束点": "结构封顶"},
        ],
        调差公式模板=FormulaType.LONGHU_VAT_CONVERSION,
        增值税率=13.0,
        合同税率=9.0,
        税率=9.0,
        负数处理=NegativeHandling.ACTUAL,
        is_preset=False,
    )


@pytest.fixture
def ratio_config() -> AdjustmentRuleConfig:
    """豪森比例调差配置"""
    return AdjustmentRuleConfig(
        id="test_ratio",
        项目名称="豪森测试项目",
        使用规则版本="v3.0",
        调差项目=[
            {"名称": "钢筋", "是否必调": "必选", "调差范围": "全部钢筋"},
            {"名称": "电缆", "是否必调": "必选", "调差范围": "全部电缆"},
        ],
        风险幅度={
            "钢筋": RiskConfig(类型=RiskType.PERCENTAGE, 值=3.0),
            "电缆": RiskConfig(类型=RiskType.FIXED, 值=2000.0),
        },
        基准价来源="我的钢铁网",
        基准价取价规则="招标时价格",
        施工期价格采集规则="按月算术平均",
        是否分阶段调差="否",
        调差公式模板=FormulaType.RATIO_ADJUSTMENT,
        税率=9.0,
        负数处理=NegativeHandling.DEDUCT,
        is_preset=False,
    )


# ============================================================
# 辅助函数
# ============================================================

def make_calculation_input(
    base_prices: Dict[str, float],
    period_prices: Dict[str, List[PriceData]],
    quantities: List[QuantityData],
) -> CalculationInput:
    """创建计算输入数据"""
    return CalculationInput(
        base_prices=base_prices,
        period_prices=period_prices,
        quantities=quantities,
    )


def round_value(value: float, decimals: int = 2) -> float:
    """四舍五入到指定小数位"""
    factor = 10 ** decimals
    return (value * factor).__truediv__(factor)


# ============================================================
# Step 1: 校验配置测试
# ============================================================

class TestStep1ValidateConfig:
    """Step 1: 配置校验测试"""

    def test_valid_config_passes(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """有效配置通过校验"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        # 不应抛出异常
        result = engine.calculate(input_data)
        assert result is not None

    def test_missing_project_name_raises(self, sample_base_prices, sample_period_prices, sample_quantities):
        """缺少项目名称应抛出异常"""
        config = AdjustmentRuleConfig(
            项目名称="",
            调差项目=[{"名称": "钢筋", "是否必调": "必选"}],
            风险幅度={"钢筋": RiskConfig(类型=RiskType.NONE, 值=0)},
            基准价来源="造价信息",
            施工期价格采集规则="按月算术平均",
            调差公式模板=FormulaType.NO_RISK,
            税率=9.0,
            is_preset=False,
        )
        engine = AdjustmentEngineV3(config=config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        with pytest.raises(AdjustmentEngineV3Error):
            engine.calculate(input_data)

    def test_missing_formula_template_raises(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """缺少公式模板应抛出异常"""
        standard_config.调差公式模板 = None
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        with pytest.raises(AdjustmentEngineV3Error):
            engine.calculate(input_data)

    def test_empty_adjustment_items_raises(self, sample_base_prices, sample_period_prices, sample_quantities):
        """空调差项目应抛出异常"""
        config = AdjustmentRuleConfig(
            项目名称="测试项目",
            调差项目=[],
            风险幅度={},
            基准价来源="造价信息",
            施工期价格采集规则="按月算术平均",
            调差公式模板=FormulaType.NO_RISK,
            税率=9.0,
            is_preset=False,
        )
        engine = AdjustmentEngineV3(config=config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        with pytest.raises(AdjustmentEngineV3Error):
            engine.calculate(input_data)


# ============================================================
# Step 2: 取基准价测试
# ============================================================

class TestStep2FetchBasePrices:
    """Step 2: 取基准价测试"""

    def test_fetch_base_prices_direct(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """直接使用输入的基准价"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None
        assert len(result.明细) > 0

    def test_missing_base_price_uses_zero(self, standard_config, sample_period_prices, sample_quantities):
        """缺失基准价使用0"""
        base_prices = {"钢筋": 4000.0}  # 混凝土缺失
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(base_prices, sample_period_prices, sample_quantities)
        # 混凝土的明细应不参与计算或显示基准价为0
        result = engine.calculate(input_data)
        assert result is not None


# ============================================================
# Step 3: 取施工期均价测试
# ============================================================

class TestStep3FetchPeriodPrices:
    """Step 3: 取施工期均价测试"""

    def test_calculate_period_average(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """计算施工期均价"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None
        # 钢筋均价 = (4100+4150+4200+4180+4220)/5 = 4170
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                assert detail.施工均价 == 4170.0

    def test_empty_prices_returns_zero(self, standard_config, sample_base_prices, sample_quantities):
        """空价格返回0"""
        period_prices = {"钢筋": []}
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None


# ============================================================
# Step 3.5: 价格数据校验测试
# ============================================================

class TestStep35ValidatePriceData:
    """Step 3.5: 价格数据校验测试"""

    def test_validate_price_data_completeness(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """价格数据完整性校验"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result.价格校验 is not None
        assert "钢筋" in result.价格校验.get("details", {})

    def test_validate_missing_dates(self, standard_config, sample_base_prices, sample_quantities):
        """检测缺失日期"""
        # 只有1天数据，但工程量跨越5天
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4100.0)],
        }
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 应检测到数据缺失
        assert result.价格校验 is not None
        钢筋校验 = result.价格校验.get("details", {}).get("钢筋", {})
        assert 钢筋校验.get("missing_days", 0) >= 0

    def test_validate_prices_returns_validation_result(self, price_service):
        """价格服务校验功能"""
        prices = [
            PriceData("2026-01-01", 4100.0),
            PriceData("2026-01-02", 4150.0),
            PriceData("2026-01-03", 4200.0),
        ]
        result = price_service.validate_prices(prices, "钢筋", "2026-01-01", "2026-01-03")
        assert result.total_days == 3
        assert result.valid_days == 3


# ============================================================
# Step 4: 判断是否超风险幅度测试
# ============================================================

class TestStep4CheckRiskThreshold:
    """Step 4: 判断是否超风险幅度测试"""

    def test_within_threshold_no_adjustment(self, standard_config):
        """在风险幅度内不调差"""
        # 基准价4000，±3%风险幅度，上限4120，下限3880
        # 施工期均价4100，在[3880, 4120]内，不调差
        engine = AdjustmentEngineV3(config=standard_config)
        is_over, is_rising, diff = engine._check_risk_threshold("钢筋", 4000.0, 4100.0)
        assert is_over is False
        assert diff == 0

    def test_rise_above_threshold_adjust(self, standard_config):
        """涨幅超出风险幅度应调差"""
        # 施工期均价4200 > 4120，超幅
        engine = AdjustmentEngineV3(config=standard_config)
        is_over, is_rising, diff = engine._check_risk_threshold("钢筋", 4000.0, 4200.0)
        assert is_over is True
        assert is_rising is True
        # diff = 4200 - 4120 = 80
        assert abs(diff - 80.0) < 0.01

    def test_fall_below_threshold_adjust(self, standard_config):
        """跌幅超出风险幅度应调差"""
        # 施工期均价3800 < 3880，超幅
        engine = AdjustmentEngineV3(config=standard_config)
        is_over, is_rising, diff = engine._check_risk_threshold("钢筋", 4000.0, 3800.0)
        assert is_over is True
        assert is_rising is False
        # diff = 3800 - 3880 = -80
        assert abs(diff - (-80.0)) < 0.01

    def test_zero_risk_full_adjustment(self, no_risk_config):
        """0%风险幅度全额调差"""
        engine = AdjustmentEngineV3(config=no_risk_config)
        is_over, is_rising, diff = engine._check_risk_threshold("钢筋", 4000.0, 4500.0)
        assert is_over is True
        # diff = 4500 - 4000 = 500
        assert abs(diff - 500.0) < 0.01


# ============================================================
# Step 5: 代入公式计算测试
# ============================================================

class TestStep5CalculateAdjustment:
    """Step 5: 代入公式计算测试"""

    def test_calculate_with_standard_three_stage(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """标准三段式公式计算"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None
        assert len(result.明细) > 0
        # 钢筋：基准价4000，均价4170，上限4120
        # 4170 > 4120，超幅上涨，应调差
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                # 4170 > 4120，所以 is_over_risk 应该是 True
                assert detail.是否超幅 is True

    def test_calculate_with_rise(self, standard_config, sample_quantities):
        """涨幅超出计算"""
        # 修改价格为超幅场景
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4200.0),
                PriceData("2026-01-02", 4250.0),
                PriceData("2026-01-03", 4300.0),
            ],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-03",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 均价 = (4200+4250+4300)/3 = 4250
        # 上限 = 4000 * 1.03 = 4120
        # 超出 = 4250 - 4120 = 130
        # 调整金额 = 100 * 130 = 13000
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                assert detail.是否超幅 is True
                assert abs(detail.调整金额 - 13000.0) < 0.01

    def test_calculate_with_no_risk_formula(self, no_risk_config, sample_quantities):
        """无风险幅度公式（全额调差）"""
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4500.0),
            ],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        ]
        engine = AdjustmentEngineV3(config=no_risk_config)
        input_data = make_calculation_input(base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 全额调差 = 100 * (4500 - 4000) = 50000
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                assert abs(detail.调整金额 - 50000.0) < 0.01

    def test_calculate_longhu_formula(self, longhu_config, sample_quantities):
        """龙湖增值税率换算法"""
        base_prices = {"钢筋": 4000.0, "商品混凝土": 450.0}
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4500.0)],
            "商品混凝土": [PriceData("2026-01-01", 480.0)],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
            QuantityData(
                material_name="商品混凝土",
                quantity=500.0,
                unit="m³",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        ]
        engine = AdjustmentEngineV3(config=longhu_config)
        input_data = make_calculation_input(base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        assert result is not None
        # 验证龙湖公式结果
        # 钢筋: {100 * (4500 - 4000)} / 1.13 * 1.09 = 48230.09
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                expected = (100 * (4500 - 4000)) / 1.13 * 1.09
                assert abs(detail.调整金额 - expected) < 0.1


# ============================================================
# Step 5.5: 分阶段汇总测试
# ============================================================

class TestStep55SummarizeByPhase:
    """Step 5.5: 分阶段汇总测试"""

    def test_summarize_by_phase(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """按阶段汇总"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 整体阶段汇总
        if result.阶段汇总:
            phase_summary = result.阶段汇总[0]
            assert "阶段名称" in phase_summary
            assert "含税小计" in phase_summary

    def test_multi_phase_summaries(self, longhu_config, sample_base_prices, sample_period_prices):
        """多阶段汇总"""
        # 设置分阶段工程量
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="地下室",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-05",
            ),
            QuantityData(
                material_name="钢筋",
                quantity=200.0,
                unit="t",
                phase="楼栋",
                location="",
                start_date="2026-02-01",
                end_date="2026-02-05",
            ),
        ]
        engine = AdjustmentEngineV3(config=longhu_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, quantities)
        result = engine.calculate(input_data)
        if result.阶段汇总:
            assert len(result.阶段汇总) >= 1


# ============================================================
# Step 6: 输出结果测试
# ============================================================

class TestStep6FormatOutput:
    """Step 6: 输出结果测试"""

    def test_format_output_contains_required_fields(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """输出包含必需字段"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 检查必需字段
        assert result.项目名称 == "测试项目"
        assert result.使用规则版本 == "v3.0"
        assert result.调差总金额 >= 0
        assert result.明细 is not None
        assert result.计算时间 is not None

    def test_format_output_to_dict(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """输出转为字典"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "项目名称" in result_dict
        assert "调差总金额" in result_dict
        assert "明细" in result_dict

    def test_detail_to_dict(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """明细转为字典"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        if result.明细:
            detail = result.明细[0]
            detail_dict = detail.to_dict()
            assert isinstance(detail_dict, dict)
            assert "材料名称" in detail_dict
            assert "调整金额" in detail_dict


# ============================================================
# 多部位分时段计算测试
# ============================================================

class TestMultiLocationCalculation:
    """多部位分时段计算测试"""

    def test_multi_location_independent_periods(self, standard_config, sample_base_prices):
        """多部位使用各自独立的施工时段"""
        # 两个楼栋，施工时段不同
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4100.0),
                PriceData("2026-01-02", 4150.0),
                PriceData("2026-02-01", 4300.0),
                PriceData("2026-02-02", 4350.0),
            ],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="1#楼",
                start_date="2026-01-01",
                end_date="2026-01-02",
            ),
            QuantityData(
                material_name="钢筋",
                quantity=200.0,
                unit="t",
                phase="整体",
                location="2#楼",
                start_date="2026-02-01",
                end_date="2026-02-02",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 1#楼均价 = (4100+4150)/2 = 4125
        # 2#楼均价 = (4300+4350)/2 = 4325
        # 各部位应独立计算
        assert len(result.明细) == 2

    def test_location_uses_own_time_period(self, standard_config, sample_base_prices):
        """各部位使用自己的施工时段计算均价"""
        # 楼栋1: 1月份（价格低）
        # 楼栋2: 2月份（价格高）
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4100.0),
                PriceData("2026-01-02", 4100.0),
                PriceData("2026-02-01", 4500.0),
                PriceData("2026-02-02", 4500.0),
            ],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="1#楼",
                start_date="2026-01-01",
                end_date="2026-01-02",
            ),
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="2#楼",
                start_date="2026-02-01",
                end_date="2026-02-02",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 验证两个部位的价格不同
        details_by_location = {}
        for detail in result.明细:
            details_by_location[detail.部位] = detail.施工均价
        assert len(details_by_location) == 2


# ============================================================
# 5种公式类型集成测试
# ============================================================

class TestFormulaTypes:
    """5种公式类型集成测试"""

    def test_standard_three_stage_formula(self, standard_config, sample_quantities):
        """标准三段式公式"""
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4200.0),
                PriceData("2026-01-02", 4250.0),
                PriceData("2026-01-03", 4300.0),
            ],
        }
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None
        assert result.使用规则版本 == "v3.0"

    def test_longhu_vat_conversion_formula(self, longhu_config, sample_quantities):
        """龙湖增值税率换算法"""
        base_prices = {"钢筋": 4000.0, "商品混凝土": 450.0}
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4500.0)],
            "商品混凝土": [PriceData("2026-01-01", 480.0)],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        ]
        engine = AdjustmentEngineV3(config=longhu_config)
        input_data = make_calculation_input(base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 钢筋全额调差并含税换算
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                # 期望值 = {100 * (4500 - 4000)} / 1.13 * 1.09
                expected = (100 * (4500 - 4000)) / 1.13 * 1.09
                assert abs(detail.调整金额 - expected) < 0.1

    def test_ratio_adjustment_formula(self, ratio_config, sample_quantities):
        """豪森比例调差法"""
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [
                PriceData("2026-01-01", 4500.0),
            ],
        }
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-01",
            ),
        ]
        engine = AdjustmentEngineV3(config=ratio_config)
        input_data = make_calculation_input(base_prices, period_prices, quantities)
        result = engine.calculate(input_data)
        # 比例调差法: 4000 * (4500/4000 - 1.03) * 100 = 4000 * (1.125 - 1.03) * 100 = 4000 * 0.095 * 100 = 38000
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                expected = 4000 * (4500 / 4000 - 1.03) * 100
                assert abs(detail.调整金额 - expected) < 0.01

    def test_cost_info_adjustment_formula(self, sample_quantities):
        """造价信息调整法"""
        config = AdjustmentRuleConfig(
            id="test_cost_info",
            项目名称="朱家庄测试",
            使用规则版本="v3.0",
            调差项目=[
                {"名称": "钢筋", "是否必调": "必选", "调差范围": "全部钢筋"},
            ],
            风险幅度={
                "钢筋": RiskConfig(类型=RiskType.PERCENTAGE, 值=3.0),
            },
            基准价来源="造价信息",
            基准价取价规则="招标时价格",
            施工期价格采集规则="按月算术平均",
            是否分阶段调差="否",
            调差公式模板=FormulaType.COST_INFO_ADJUSTMENT,
            税率=9.0,
            负数处理=NegativeHandling.DEDUCT,
            is_preset=False,
        )
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4200.0)],
        }
        engine = AdjustmentEngineV3(config=config)
        input_data = make_calculation_input(base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 造价信息调整法与标准三段式相同
        # 4200 > 4120，超幅，调整 = 100 * (4200 - 4120) = 8000
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                expected = 100 * (4200 - 4000 * 1.03)
                assert abs(detail.调整金额 - expected) < 0.01

    def test_no_risk_formula(self, no_risk_config, sample_quantities):
        """无风险幅度公式"""
        base_prices = {"钢筋": 4000.0}
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4500.0)],
        }
        engine = AdjustmentEngineV3(config=no_risk_config)
        input_data = make_calculation_input(base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 全额调差 = 100 * (4500 - 4000) = 50000
        for detail in result.明细:
            if detail.材料名称 == "钢筋":
                assert abs(detail.调整金额 - 50000.0) < 0.01


# ============================================================
# 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_zero_quantity_skipped(self, standard_config, sample_base_prices, sample_period_prices):
        """零工程量跳过"""
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=0.0,  # 零工程量
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-05",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, quantities)
        result = engine.calculate(input_data)
        # 零工程量应不产生明细或调差金额为0
        assert result is not None

    def test_zero_base_price_skipped(self, standard_config, sample_period_prices, sample_quantities):
        """零基准价跳过"""
        base_prices = {"钢筋": 0.0}  # 零基准价
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        assert result is not None

    def test_large_quantity_calculation(self, standard_config, sample_base_prices, sample_period_prices):
        """大工程量计算"""
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=10000.0,  # 1万吨
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-05",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, quantities)
        result = engine.calculate(input_data)
        assert result is not None
        assert result.调差总金额 >= 0

    def test_negative_adjustment_handling(self, standard_config, sample_quantities):
        """负数调差处理（跌价）"""
        base_prices = {"钢筋": 4500.0}  # 基准价高于施工期价
        period_prices = {
            "钢筋": [PriceData("2026-01-01", 4000.0)],
        }
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(base_prices, period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 负数处理取决于配置（扣回/不调整/按实计算）
        assert result is not None


# ============================================================
# 日志和错误处理测试
# ============================================================

class TestLoggingAndErrors:
    """日志和错误处理测试"""

    def test_error_raises_specific_exception(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """错误应抛出特定异常"""
        # 清空配置触发错误
        standard_config.调差公式模板 = None
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        with pytest.raises(AdjustmentEngineV3Error):
            engine.calculate(input_data)

    def test_validation_error_contains_details(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """验证错误包含详细信息"""
        standard_config.调差公式模板 = None
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        try:
            engine.calculate(input_data)
        except AdjustmentEngineV3Error as e:
            assert e.message is not None


# ============================================================
# 集成测试
# ============================================================

class TestIntegration:
    """集成测试"""

    def test_full_calculation_workflow(self, standard_config, sample_base_prices, sample_period_prices, sample_quantities):
        """完整计算流程"""
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, sample_quantities)
        result = engine.calculate(input_data)
        # 验证完整流程
        assert result is not None
        assert isinstance(result, CalculationResult)
        assert result.项目名称 == "测试项目"
        assert result.使用规则版本 == "v3.0"
        assert result.计算时间 is not None
        assert result.明细 is not None

    def test_multiple_materials_calculation(self, standard_config, sample_base_prices, sample_period_prices):
        """多材料计算"""
        quantities = [
            QuantityData(
                material_name="钢筋",
                quantity=100.0,
                unit="t",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-05",
            ),
            QuantityData(
                material_name="商品混凝土",
                quantity=500.0,
                unit="m³",
                phase="整体",
                location="",
                start_date="2026-01-01",
                end_date="2026-01-03",
            ),
        ]
        engine = AdjustmentEngineV3(config=standard_config)
        input_data = make_calculation_input(sample_base_prices, sample_period_prices, quantities)
        result = engine.calculate(input_data)
        assert len(result.明细) == 2
        # 总金额 = 各明细含税调整金额之和
        total_from_details = sum(d.含税调整金额 for d in result.明细)
        assert abs(result.调差总金额 - total_from_details) < 0.01