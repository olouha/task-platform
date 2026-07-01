"""
测试指标库数据验证器 IndicatorValidator
覆盖三层验证：基础验证、逻辑验证、参考范围验证
"""

import pytest
import sys
sys.path.insert(0, 'web/backend')

from services.indicator_validator import (
    IndicatorValidator,
    REFERENCE_RANGES,
    validate_indicator_data,
)


class TestBasicValidation:
    """第一层验证：基础验证测试"""

    def test_valid_data_passes(self):
        """完整有效数据应通过验证"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 25000.0,
            "unit_cost": 2350.0,
            "start_date": "2023-01",
            "end_date": "2024-06",
        }
        result = validator.validate(data)
        assert result.passed is True
        assert len(result.errors) == 0

    def test_missing_required_field_fails(self):
        """缺少必填字段应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            # 缺少 location 和 structure
        }
        result = validator.validate(data)
        assert result.passed is False
        assert len(result.errors) >= 2

    def test_empty_name_fails(self):
        """空名称应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
        }
        result = validator.validate(data)
        assert result.passed is False
        error_fields = [e.field for e in result.errors]
        assert "name" in error_fields

    def test_negative_area_fails(self):
        """负面积应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": -1000.0,
        }
        result = validator.validate(data)
        assert result.passed is False
        error_fields = [e.field for e in result.errors]
        assert "area_total" in error_fields

    def test_zero_unit_cost_fails(self):
        """零造价应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "unit_cost": 0,
        }
        result = validator.validate(data)
        assert result.passed is False

    def test_invalid_date_format_fails(self):
        """无效日期格式应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "start_date": "2023/01/01",  # 错误格式
        }
        result = validator.validate(data)
        assert result.passed is False
        error_fields = [e.field for e in result.errors]
        assert "start_date" in error_fields

    def test_end_date_before_start_date_fails(self):
        """竣工早于开工应失败"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "start_date": "2024-06",
            "end_date": "2023-01",
        }
        result = validator.validate(data)
        assert result.passed is False
        error_fields = [e.field for e in result.errors]
        assert "end_date" in error_fields

    def test_small_area_warning(self):
        """过小面积应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 50.0,  # 过小
        }
        result = validator.validate(data)
        warning_fields = [w.field for w in result.warnings]
        assert "area_total" in warning_fields


class TestLogicalValidation:
    """第二层验证：逻辑验证测试"""

    def test_area_consistency_warning(self):
        """总面积与地上+地下面积不符应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 10000.0,
            "area_above": 7000.0,
            "area_below": 4000.0,  # 7000+4000=11000 != 10000
        }
        result = validator.validate(data)
        # 差异约10%，应产生警告
        assert len(result.warnings) > 0 or len(result.errors) > 0

    def test_cost_calculation_consistency(self):
        """平米造价与总面积计算的总造价不符应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 10000.0,
            "unit_cost": 2000.0,  # 2000 * 10000 = 20000000
            "total_cost": 30000000.0,  # 差异50%
        }
        result = validator.validate(data)
        # 差异超过2%容差，应产生警告
        assert len(result.warnings) > 0

    def test_unit_content_consistency(self):
        """单位含量与总量/面积不符应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_above": 10000.0,
            "above_rebar": 1000.0,  # 1000t
            "above_rebar_unit": 0.05,  # 0.05 t/m², 应该是 1000/10000 = 0.1
        }
        result = validator.validate(data)
        # 差异应产生警告
        assert len(result.warnings) > 0


class TestReferenceRangeValidation:
    """第三层验证：参考范围验证测试"""

    def test_unit_cost_below_range_warns(self):
        """平米造价低于参考范围应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "unit_cost": 500.0,  # 远低于住宅参考范围 1500-4500
        }
        result = validator.validate(data)
        assert len(result.warnings) > 0

    def test_unit_cost_above_range_warns(self):
        """平米造价高于参考范围应产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "unit_cost": 10000.0,  # 远高于住宅参考范围
        }
        result = validator.validate(data)
        assert len(result.warnings) > 0

    def test_unit_cost_in_range_passes(self):
        """平米造价在参考范围内应通过"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "unit_cost": 2500.0,  # 在住宅参考范围内
        }
        result = validator.validate(data)
        # 不应有 unit_cost 相关的错误或警告
        unit_cost_warnings = [w for w in result.warnings if w.field == "unit_cost"]
        assert len(unit_cost_warnings) == 0

    def test_concrete_unit_content_in_range(self):
        """砼含量在参考范围内"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "above_concrete_unit": 0.35,  # 在住宅参考范围 0.25-0.45 内
        }
        result = validator.validate(data)
        # 不应有 above_concrete_unit 相关的严重警告
        concrete_warnings = [w for w in result.warnings if w.field == "above_concrete_unit"]
        assert len(concrete_warnings) == 0

    def test_rebar_unit_content_out_range(self):
        """钢筋含量超出参考范围应警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试住宅项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "above_rebar_unit": 0.200,  # 超出住宅参考范围 0.035-0.065
        }
        result = validator.validate(data)
        rebar_warnings = [w for w in result.warnings if "钢筋" in w.message]
        assert len(rebar_warnings) > 0

    def test_unknown_category_uses_default(self):
        """未知业态使用默认住宅参考范围"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "未知业态",
            "location": "山东烟台",
            "structure": "框架结构",
            "unit_cost": 500.0,  # 低于住宅下限
        }
        result = validator.validate(data)
        # 应产生警告（使用住宅范围）
        assert len(result.warnings) > 0
        # 应有关于业态的警告
        category_warnings = [w for w in result.warnings if w.field == "category"]
        assert len(category_warnings) > 0


class TestStrictMode:
    """严格模式测试"""

    def test_strict_mode_converts_warnings_to_errors(self):
        """严格模式下，部分警告应转为错误"""
        validator = IndicatorValidator(strict_mode=True)
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 10000.0,
            "area_above": 7000.0,
            "area_below": 4000.0,  # 与总面积不符
        }
        result = validator.validate(data)
        # 严格模式下，不一致应产生错误而非警告
        error_fields = [e.field for e in result.errors]
        assert "area_total" in error_fields


class TestReferenceRanges:
    """参考范围数据测试"""

    def test_categories_defined(self):
        """业态分类应已定义"""
        assert "住宅" in REFERENCE_RANGES.CATEGORIES
        assert "商业" in REFERENCE_RANGES.CATEGORIES
        assert "办公" in REFERENCE_RANGES.CATEGORIES
        assert "工业" in REFERENCE_RANGES.CATEGORIES

    def test_unit_cost_ranges_defined(self):
        """各业态平米造价范围应已定义"""
        assert "住宅" in REFERENCE_RANGES.UNIT_COST
        assert "商业" in REFERENCE_RANGES.UNIT_COST
        assert REFERENCE_RANGES.UNIT_COST["住宅"]["min"] < REFERENCE_RANGES.UNIT_COST["住宅"]["typical"]
        assert REFERENCE_RANGES.UNIT_COST["住宅"]["typical"] < REFERENCE_RANGES.UNIT_COST["住宅"]["max"]

    def test_concrete_unit_ranges_defined(self):
        """砼含量范围应已定义"""
        assert "住宅" in REFERENCE_RANGES.ABOVE_CONCRETE_UNIT
        assert "住宅" in REFERENCE_RANGES.UNDERGROUND_CONCRETE_UNIT
        assert REFERENCE_RANGES.UNDERGROUND_CONCRETE_UNIT["住宅"]["min"] > REFERENCE_RANGES.ABOVE_CONCRETE_UNIT["住宅"]["min"]

    def test_rebar_unit_ranges_defined(self):
        """钢筋含量范围应已定义"""
        assert "住宅" in REFERENCE_RANGES.ABOVE_REBAR_UNIT
        assert "住宅" in REFERENCE_RANGES.UNDERGROUND_REBAR_UNIT


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_validate_indicator_data(self):
        """便捷函数应正常工作"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
        }
        result = validate_indicator_data(data)
        assert result.passed is True

    def test_validate_indicator_data_strict(self):
        """便捷函数支持严格模式"""
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
        }
        result = validate_indicator_data(data, strict_mode=True)
        assert result.passed is True


class TestValidationResult:
    """验证结果结构测试"""

    def test_validation_result_has_checks(self):
        """验证结果应包含检查项"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
        }
        result = validator.validate(data)
        assert "checks" in result.model_dump()
        assert len(result.checks) > 0

    def test_validation_result_fields(self):
        """验证结果应包含所有必要字段"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
        }
        result = validator.validate(data)
        dumped = result.model_dump()
        assert "passed" in dumped
        assert "warnings" in dumped
        assert "errors" in dumped
        assert "checks" in dumped


class TestEdgeCases:
    """边界条件测试"""

    def test_empty_data(self):
        """空数据应失败"""
        validator = IndicatorValidator()
        result = validator.validate({})
        assert result.passed is False
        assert len(result.errors) >= 4  # 至少4个必填字段

    def test_all_required_fields_present(self):
        """所有必填字段存在时应通过基础验证"""
        validator = IndicatorValidator()
        data = {
            "name": "A",
            "category": "住宅",
            "location": "A",
            "structure": "A",
        }
        result = validator.validate(data)
        # 应通过基础验证（可能因其他原因有警告）
        assert len(result.errors) == 0

    def test_large_area_no_warning(self):
        """大面积在合理范围内不产生警告"""
        validator = IndicatorValidator()
        data = {
            "name": "测试项目",
            "category": "住宅",
            "location": "山东烟台",
            "structure": "框架结构",
            "area_total": 400000.0,  # 40万平方米，合理
        }
        result = validator.validate(data)
        # 不应有面积相关的警告
        area_warnings = [w for w in result.warnings if w.field == "area_total"]
        assert len(area_warnings) == 0
