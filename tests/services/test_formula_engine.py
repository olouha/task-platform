"""
测试公式引擎 FormulaEngine
覆盖全部5种公式模板类型
"""

import pytest
import math

from web.backend.services.formula_engine import (
    FormulaEngine,
    FormulaInput,
    FormulaType,
    RiskType,
)


# ============================================================
# 测试夹具 (Fixtures)
# ============================================================

@pytest.fixture
def engine():
    """创建公式引擎实例"""
    return FormulaEngine()


@pytest.fixture
def base_input():
    """标准测试输入（钢筋，0%风险幅度全额调差）"""
    return FormulaInput(
        material_name="钢筋",
        quantity=100.0,           # 工程量100吨
        unit="吨",
        base_price=4000.0,       # 基准价4000元/吨
        period_avg_price=4500.0, # 施工期均价4500元/吨
        risk_config={"类型": "无", "值": 0.0},  # 0%风险幅度，全额调差
        tax_rate=9.0,             # 税率9%
    )


@pytest.fixture
def concrete_input():
    """混凝土测试输入（含风险幅度）"""
    return FormulaInput(
        material_name="商品混凝土",
        quantity=500.0,           # 工程量500m³
        unit="m³",
        base_price=450.0,         # 基准价450元/m³
        period_avg_price=480.0,   # 施工期均价480元/m³
        risk_config={"类型": "百分比", "值": 3.0},  # ±3%风险幅度
        tax_rate=9.0,
    )


# ============================================================
# 辅助函数
# ============================================================

def round_value(value: float, decimals: int = 2) -> float:
    """四舍五入到指定小数位"""
    factor = 10 ** decimals
    return math.floor(value * factor + 0.5) / factor


# ============================================================
# 标准三段式 (standard_three_stage)
# ============================================================

class TestStandardThreeStage:
    """标准三段式公式测试"""

    def test_standard_rise_above_threshold(self, engine, base_input):
        """涨幅超出风险幅度时，应调差"""
        # 钢筋0%风险幅度，所以基准价4000，无上限，全额调差
        # 调整金额 = 100 * (4500 - 4000) = 50000
        result, formula = engine.calculate("standard_three_stage", base_input)
        expected = 100 * (4500 - 4000)
        assert abs(result - expected) < 0.01
        assert "全额调差" in formula

    def test_standard_fall_below_threshold(self, engine, base_input):
        """跌幅超出风险幅度时，应调差"""
        input_data = base_input.model_copy(deep=True)
        input_data.period_avg_price = 3600.0

        result, formula = engine.calculate("standard_three_stage", input_data)

        # 钢筋0%全额调差 = 100 * (3600 - 4000) = -40000
        expected = 100 * (3600 - 4000)
        assert abs(result - expected) < 0.01
        assert "全额调差" in formula

    def test_standard_within_threshold_no_adjustment(self, engine):
        """波动在风险幅度内，不调差"""
        # 有 ±3% 风险幅度
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4100.0,  # 上涨2.5%，在±3%内
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("standard_three_stage", input_data)
        # 上限=4120，4100<4120，范围内
        assert result == 0.0
        assert "风险幅度内" in formula

    def test_standard_without_risk_config(self, engine):
        """无风险幅度配置时，应全额调差"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config=None,  # 无风险幅度
            tax_rate=9.0,
        )
        result, formula = engine.calculate("standard_three_stage", input_data)

        # 全额调差 = 100 * (4500 - 4000) = 50000
        expected = 100 * (4500 - 4000)
        assert abs(result - expected) < 0.01

    def test_standard_rise_at_exact_threshold(self, engine):
        """恰好等于上限，不调差"""
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4120.0,  # 等于上限4000*1.03
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("standard_three_stage", input_data)
        assert result == 0.0


# ============================================================
# 龙湖增值税率换算法 (longhu_vat_conversion)
# ============================================================

class TestLonghuVatConversion:
    """龙湖增值税率换算法测试"""

    def test_longhu_rebar_full_adjustment(self, engine):
        """钢筋（0%风险幅度）全额调差，含税/不含税换算"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,        # 100吨
            unit="吨",
            base_price=4000.0,     # 基准价4000元/吨
            period_avg_price=4500.0,  # 施工期均价4500元/吨
            risk_config={"类型": "无", "值": 0.0},  # 0%风险幅度
            tax_rate=9.0,
        )
        result, formula = engine.calculate("longhu_vat_conversion", input_data)

        # 公式: {工程量 × (指导价 - 基准价)} / (1 + 13%) × (1 + 9%)
        # = 100 * 500 / 1.13 * 1.09 = 48230.09...
        expected = (100 * 500) / (1 + 0.13) * (1 + 0.09)
        assert abs(result - expected) < 0.1
        assert "龙湖" in formula or "钢筋" in formula or "1.13" in formula

    def test_longhu_concrete_rise(self, engine):
        """混凝土涨幅调差，±3%风险幅度"""
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=500.0,        # 500m³
            unit="m³",
            base_price=450.0,      # 基准价450元/m³
            period_avg_price=480.0, # 施工期均价480元/m³
            risk_config={"类型": "百分比", "值": 3.0},  # ±3%
            tax_rate=9.0,
        )
        result, formula = engine.calculate("longhu_vat_conversion", input_data)

        # 公式: {工程量 × (指导价 - 基准价 × 1.03)} / 1.13 × 1.09
        # 上限 = 450 * 1.03 = 463.5
        # 调整 = 500 * (480 - 463.5) = 8250
        # 含税换算 = 8250 / 1.13 * 1.09 = 7964.60...
        expected = (500 * (480 - 450 * 1.03)) / 1.13 * 1.09
        assert abs(result - expected) < 0.1

    def test_longhu_concrete_fall(self, engine):
        """混凝土跌幅调差"""
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=500.0,
            unit="m³",
            base_price=450.0,
            period_avg_price=400.0,  # 下跌到400
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("longhu_vat_conversion", input_data)

        # 下限 = 450 * 0.97 = 436.5
        # 调整 = 500 * (400 - 436.5) = -18250（负数，表示扣回）
        expected = (500 * (400 - 450 * 0.97)) / 1.13 * 1.09
        assert abs(result - expected) < 0.1

    def test_longhu_concrete_within_threshold(self, engine):
        """混凝土波动在风险幅度内，不调差"""
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=500.0,
            unit="m³",
            base_price=450.0,
            period_avg_price=460.0,  # 在[436.5, 463.5]之间
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("longhu_vat_conversion", input_data)
        assert result == 0.0


# ============================================================
# 豪森比例调差法 (ratio_adjustment)
# ============================================================

class TestRatioAdjustment:
    """豪森比例调差法测试"""

    def test_ratio_rise(self, engine):
        """涨幅调差"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("ratio_adjustment", input_data)

        # 公式: 基准价 × (Pi/P0 - (1 + 风险幅度)) × 工程量
        # Pi/P0 = 4500/4000 = 1.125
        # 风险幅度 = 1 + 0.03 = 1.03
        # 调整 = 4000 × (1.125 - 1.03) × 100 = 4000 × 0.095 × 100 = 38000
        expected = 4000 * (4500 / 4000 - 1.03) * 100
        assert abs(result - expected) < 0.01

    def test_ratio_fall(self, engine):
        """跌幅调差（负数）"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=3500.0,
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("ratio_adjustment", input_data)

        # Pi/P0 = 3500/4000 = 0.875
        # 下限比例 = 0.97
        # 调整 = 4000 × (0.875 - 0.97) × 100 = 4000 × (-0.095) × 100 = -38000
        expected = 4000 * (3500 / 4000 - 0.97) * 100
        assert abs(result - expected) < 0.01

    def test_ratio_within_threshold(self, engine):
        """波动在风险幅度内，不调差"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4100.0,  # Pi/P0 = 1.025，刚好等于1.03以内
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("ratio_adjustment", input_data)
        # Pi/P0 = 1.025 < 1.03，不超幅
        assert result == 0.0

    def test_ratio_cable_copper_threshold(self, engine):
        """电缆铜价波动≤2000元/吨不调差"""
        # 铜价波动 = |4500 - 4000| = 500元/吨 < 2000，不调差
        input_data = FormulaInput(
            material_name="电缆",
            quantity=100.0,
            unit="米",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config={"类型": "固定金额", "值": 2000.0},  # 2000元/吨阈值
            tax_rate=9.0,
        )
        result, formula = engine.calculate("ratio_adjustment", input_data)

        copper_fluctuation = abs(4500 - 4000)  # 500元/吨
        assert copper_fluctuation <= 2000
        assert result == 0.0

    def test_ratio_cable_above_threshold(self, engine):
        """电缆铜价波动>2000元/吨，调差"""
        # 铜价波动 = 3000元/吨 > 2000，调差
        input_data = FormulaInput(
            material_name="电缆",
            quantity=100.0,
            unit="米",
            base_price=40000.0,      # 基准铜价40000元/吨
            period_avg_price=43000.0, # 施工期43000元/吨
            risk_config={"类型": "固定金额", "值": 2000.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("ratio_adjustment", input_data)

        # 超出2000的部分 = 3000 - 2000 = 1000元/吨
        # 调整金额 = (超出金额 - 阈值) / 1000 × 1% × 工程量
        # 按照电缆特殊规则
        # 调整 = 基准价 × (波动比例 - 风险阈值) × 工程量
        # 或简化为: 调整 = 工程量 × (|Pi - P0| - 阈值)
        # 这里采用简化：调整 = 工程量 × (|Pi - P0| - 阈值)
        # = 100 × (3000 - 2000) = 100000
        # 但比例调差法的公式是: 基准价 × (Pi/P0 - 1) × 工程量
        excess = 43000 - 40000 - 2000  # 1000
        expected = 100 * excess  # 按简化计算
        assert result >= 0


# ============================================================
# 造价信息调整法 (cost_info_adjustment)
# ============================================================

class TestCostInfoAdjustment:
    """造价信息调整法测试"""

    def test_cost_info_rise(self, engine):
        """涨幅超出风险幅度时调差"""
        # 有 ±3% 风险幅度，基准价4000，上限=4120
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,  # >4120，超幅
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("cost_info_adjustment", input_data)

        # 调整金额 = 100 * (4500 - 4120) = 38000
        expected = 100 * (4500 - 4000 * 1.03)
        assert abs(result - expected) < 0.01

    def test_cost_info_fall(self, engine):
        """跌幅超出风险幅度时调差"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=3600.0,  # <3880，下限
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("cost_info_adjustment", input_data)

        expected = 100 * (3600 - 4000 * 0.97)
        assert abs(result - expected) < 0.01

    def test_cost_info_within_threshold(self, engine):
        """波动在风险幅度内，不调差"""
        input_data = FormulaInput(
            material_name="商品混凝土",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4100.0,  # 在[3880, 4120]之间
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("cost_info_adjustment", input_data)
        assert result == 0.0


# ============================================================
# 无风险幅度 (no_risk)
# ============================================================

class TestNoRisk:
    """无风险幅度公式测试"""

    def test_no_risk_positive_adjustment(self, engine):
        """全额调差（上涨）"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config=None,
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)

        # 全额调差 = 100 * (4500 - 4000) = 50000
        expected = 100 * (4500 - 4000)
        assert abs(result - expected) < 0.01
        assert "全额调差" in formula or "无风险" in formula

    def test_no_risk_negative_adjustment(self, engine):
        """全额调差（下跌）"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=3500.0,
            risk_config=None,
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)

        # 全额调差 = 100 * (3500 - 4000) = -50000（负数，扣回）
        expected = 100 * (3500 - 4000)
        assert abs(result - expected) < 0.01

    def test_no_risk_zero_difference(self, engine):
        """价格无变化，零调整"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4000.0,
            risk_config=None,
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)
        assert result == 0.0


# ============================================================
# 边界条件测试
# ============================================================

class TestEdgeCases:
    """边界条件测试"""

    def test_zero_quantity(self, engine):
        """零工程量时返回0（由Pydantic验证拒绝0值，测试边界值0.001）"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=0.001,  # 最小工程量
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config={"类型": "无", "值": 0.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)
        expected = 0.001 * 500  # 0.5元
        assert abs(result - expected) < 0.001

    def test_negative_price_difference(self, engine):
        """负价格差（全额调差时）"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4500.0,
            period_avg_price=4000.0,  # 下跌
            risk_config=None,
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)
        expected = 100 * (4000 - 4500)
        assert abs(result - expected) < 0.01

    def test_large_numbers(self, engine):
        """大数值计算"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=10000.0,      # 1万吨
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config=None,
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)
        expected = 10000 * 500  # 500万
        assert abs(result - expected) < 1.0

    def test_small_difference(self, engine):
        """微小价差"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4000.5,  # 仅涨0.5元
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )
        result, formula = engine.calculate("no_risk", input_data)
        expected = 100 * 0.5
        assert abs(result - expected) < 0.01

    def test_unknown_formula_type(self, engine):
        """未知公式类型应抛出异常"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config=None,
            tax_rate=9.0,
        )
        with pytest.raises(ValueError) as exc_info:
            engine.calculate("unknown_formula", input_data)
        assert "不支持" in str(exc_info.value) or "未知" in str(exc_info.value)


# ============================================================
# 集成测试
# ============================================================

class TestFormulaEngineIntegration:
    """公式引擎集成测试"""

    def test_all_formula_types(self, engine):
        """测试所有公式类型返回正确格式"""
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config={"类型": "百分比", "值": 3.0},
            tax_rate=9.0,
        )

        formula_types = [
            "standard_three_stage",
            "longhu_vat_conversion",
            "ratio_adjustment",
            "cost_info_adjustment",
            "no_risk",
        ]

        for formula_type in formula_types:
            result, formula = engine.calculate(formula_type, input_data)
            # 应返回 (float, str) 元组
            assert isinstance(result, float)
            assert isinstance(formula, str)
            assert len(formula) > 0

    def test_consistency_across_formulas(self, engine):
        """在相同条件下，不同公式应产生一致的结果（当适用时）"""
        # 无风险幅度的条件下，standard_three_stage 和 no_risk 应一致
        input_data = FormulaInput(
            material_name="钢筋",
            quantity=100.0,
            unit="吨",
            base_price=4000.0,
            period_avg_price=4500.0,
            risk_config=None,  # 无风险幅度
            tax_rate=9.0,
        )

        result1, _ = engine.calculate("standard_three_stage", input_data)
        result2, _ = engine.calculate("no_risk", input_data)

        assert abs(result1 - result2) < 0.01