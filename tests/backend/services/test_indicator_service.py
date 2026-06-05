"""
测试指标库服务 IndicatorService
覆盖修正系数、匹配算法、质量审核等核心功能
"""

import pytest
import sys
sys.path.insert(0, 'web/backend')

from services.indicator_service import IndicatorService, CORRECTION_FACTORS  # noqa: E402


class TestHeightCorrection:
    def test_under_30(self):
        assert IndicatorService.get_height_correction(25.0) == 1.00

    def test_30_to_60(self):
        assert IndicatorService.get_height_correction(50.0) == 1.03

    def test_60_to_100(self):
        assert IndicatorService.get_height_correction(80.0) == 1.08

    def test_over_100(self):
        assert IndicatorService.get_height_correction(120.0) == 1.15

    def test_boundary_30(self):
        assert IndicatorService.get_height_correction(30.0) == 1.00  # 30m 属于 ≤30 区间

    def test_boundary_60(self):
        assert IndicatorService.get_height_correction(60.0) == 1.03  # 60m 属于 30-60 区间（≤60）


class TestStructureCorrection:
    def test_frame(self):
        result = IndicatorService.get_structure_correction("框架结构")
        assert result["steel"] == 1.00
        assert result["concrete"] == 1.00

    def test_shear_wall(self):
        result = IndicatorService.get_structure_correction("剪力墙结构")
        assert result["steel"] == 1.25
        assert result["concrete"] == 1.15

    def test_frame_shear(self):
        result = IndicatorService.get_structure_correction("框架剪力墙结构")
        assert result["steel"] == 1.25  # 匹配"剪力墙结构"
        assert result["concrete"] == 1.15

    def test_frame_core(self):
        result = IndicatorService.get_structure_correction("框架核心筒")
        assert result["steel"] == 1.20
        assert result["concrete"] == 1.12

    def test_steel_structure(self):
        result = IndicatorService.get_structure_correction("钢结构")
        assert result["steel"] == 0.90
        assert result["concrete"] == 0.70

    def test_unknown_structure(self):
        result = IndicatorService.get_structure_correction("其他")
        assert result["steel"] == 1.00
        assert result["concrete"] == 1.00


class TestRegionCorrection:
    def test_beijing(self):
        assert IndicatorService.get_region_correction("北京") == 1.00

    def test_shanghai(self):
        assert IndicatorService.get_region_correction("上海") == 1.00

    def test_guangzhou(self):
        assert IndicatorService.get_region_correction("广州") == 1.00

    def test_shenzhen(self):
        assert IndicatorService.get_region_correction("深圳") == 1.00

    def test_jinan(self):
        assert IndicatorService.get_region_correction("济南") == 0.92

    def test_qingdao(self):
        assert IndicatorService.get_region_correction("青岛") == 0.92

    def test_hangzhou(self):
        assert IndicatorService.get_region_correction("杭州") == 0.92

    def test_shandong(self):
        assert IndicatorService.get_region_correction("山东") == 0.92

    def test_unknown(self):
        assert IndicatorService.get_region_correction("某地") == 0.92


class TestCorrectedIndicators:
    def test_all_params(self):
        result = IndicatorService.calculate_corrected_indicators(
            base_unit_cost=3000.0,
            base_steel=55.0,
            base_concrete=0.45,
            target_height=85.0,
            target_structure="剪力墙结构",
            target_location="北京"
        )
        assert "corrected_unit_cost" in result
        assert "corrected_steel" in result
        assert "corrected_concrete" in result
        assert result["correction_factors"]["height_factor"] == 1.08
        assert result["correction_factors"]["region_factor"] == 1.00

    def test_no_optional(self):
        result = IndicatorService.calculate_corrected_indicators(
            base_unit_cost=3000.0,
            base_steel=None,
            base_concrete=None,
            target_height=50.0,
            target_structure="框架结构",
            target_location="济南"
        )
        assert "corrected_unit_cost" in result
        assert "corrected_steel" not in result
        assert "corrected_concrete" not in result
        assert result["correction_factors"]["region_factor"] == 0.92


class TestMatchScore:
    def test_full_match(self):
        target = {
            "category": "商业",
            "structure": "框架结构",
            "location": "北京",
            "height": 35.0
        }
        db_item = {
            "category": "商业",
            "structure": "框架结构",
            "location": "北京",
            "height": 35.0,
            "indicators": {"unit_cost": 3000},
            "material_content": {"steel": 55, "concrete": 0.45}
        }
        result = IndicatorService.calculate_match_score(target, db_item)
        assert result["total_score"] == 100
        assert result["recommendation"] == "推荐使用"

    def test_height_diff_5(self):
        target = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0}
        db_item = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 40.0}
        result = IndicatorService.calculate_match_score(target, db_item)
        assert result["height_score"] == 25  # diff=5, 完全匹配层高
        assert result["height_diff"] == 5.0

    def test_height_diff_25(self):
        target = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 100.0}
        db_item = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 75.0}
        result = IndicatorService.calculate_match_score(target, db_item)
        assert result["height_score"] == 12

    def test_category_mismatch(self):
        target = {"category": "住宅", "structure": "框架结构", "location": "北京", "height": 35.0}
        db_item = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0}
        result = IndicatorService.calculate_match_score(target, db_item)
        assert result["category_score"] == 0
        # structure="框架结构" 匹配 → 25分; location="北京" 匹配 → 20分; height diff=0 → 25分
        # total = 0 + 25 + 20 + 25 = 70
        assert result["total_score"] == 70


class TestFindMatchedIndicators:
    def test_basic_match(self):
        target = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0}
        database = [
            {"id": "1", "name": "项目A", "category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0,
             "indicators": {"unit_cost": 3000}, "material_content": {"steel": 55, "concrete": 0.45}},
            {"id": "2", "name": "项目B", "category": "住宅", "structure": "剪力墙结构", "location": "北京", "height": 85.0,
             "indicators": {"unit_cost": 2800}, "material_content": {"steel": 52, "concrete": 0.42}},
        ]
        result = IndicatorService.find_matched_indicators(target, database, limit=5)
        assert len(result) == 1
        assert result[0]["project_id"] == "1"

    def test_limit(self):
        target = {"category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0}
        database = [
            {"id": str(i), "name": f"项目{i}", "category": "商业", "structure": "框架结构", "location": "北京", "height": 35.0 + i,
             "indicators": {"unit_cost": 3000}, "material_content": {"steel": 55, "concrete": 0.45}}
            for i in range(10)
        ]
        result = IndicatorService.find_matched_indicators(target, database, limit=3)
        assert len(result) == 3


class TestCostBreakdown:
    def test_complete(self):
        indicators = {
            "unit_cost": 3000,
            "unit_structure": 1800,
            "unit_installation": 600,
            "unit_decoration": 500,
            "unit_measure": 100
        }
        result = IndicatorService.generate_cost_breakdown(indicators)
        assert len(result) == 4
        assert result[0]["category"] == "土建工程"
        assert result[0]["amount"] == 1800.0
        assert result[0]["proportion"] == 60.0

    def test_estimated(self):
        indicators = {"unit_cost": 3000}
        result = IndicatorService.generate_cost_breakdown(indicators)
        assert len(result) == 4
        assert result[0]["amount"] == 1800.0  # 60% of total

    def test_zero_cost(self):
        result = IndicatorService.generate_cost_breakdown({})
        assert result == []


class TestQualityCheck:
    def test_area_consistent(self):
        project = {
            "name": "测试项目",
            "category": "住宅",
            "location": "北京",
            "structure": "剪力墙结构",
            "floor_above": 27,
            "floor_below": 2,
            "area_total": 80000,
            "area_above": 72000,
            "area_below": 8000,
            "height": 85.0
        }
        indicators = {
            "unit_cost": 2800,
            "unit_structure": 1700,
            "unit_installation": 550,
            "unit_decoration": 450,
            "unit_measure": 100
        }
        result = IndicatorService.quality_check(project, indicators)
        assert result["passed"] == True
        area_check = next((c for c in result["checks"] if c["check_type"] == "area"), None)
        assert area_check is not None
        assert area_check["status"] == "pass"

    def test_area_inconsistent(self):
        project = {
            "name": "测试项目",
            "category": "住宅",
            "location": "北京",
            "structure": "剪力墙结构",
            "floor_above": 27,
            "floor_below": 2,
            "area_total": 80000,
            "area_above": 72000,
            "area_below": 20000,  # 不等于 80000
            "height": 85.0
        }
        indicators = {
            "unit_cost": 2800,
            "unit_structure": 1700,
            "unit_installation": 550,
            "unit_decoration": 450,
            "unit_measure": 100
        }
        result = IndicatorService.quality_check(project, indicators)
        assert result["passed"] == False
        area_check = next((c for c in result["checks"] if c["check_type"] == "area"), None)
        assert area_check["status"] == "error"

    def test_unit_cost_out_of_range(self):
        project = {
            "name": "测试项目",
            "category": "住宅",
            "location": "北京",
            "structure": "框架结构",
            "floor_above": 10,
            "area_total": 20000,
            "height": 30.0
        }
        indicators = {"unit_cost": 5000}  # 超出框架结构住宅参考范围 1800-2500
        result = IndicatorService.quality_check(project, indicators)
        range_check = next((c for c in result["checks"] if c["check_type"] == "range"), None)
        assert range_check is not None
        assert range_check["status"] == "warn"

    def test_steel_out_of_range(self):
        project = {
            "name": "测试项目",
            "category": "住宅",
            "location": "北京",
            "structure": "框架结构",
            "floor_above": 10,
            "area_total": 20000,
            "height": 30.0
        }
        indicators = {"unit_cost": 2200, "steel": 100}  # 超出合理范围 15-80
        result = IndicatorService.quality_check(project, indicators)
        steel_check = next((c for c in result["checks"] if c["check_type"] == "range" and "钢筋" in c["description"]), None)
        assert steel_check is not None
        assert steel_check["status"] == "warn"


class TestLegacyFormat:
    def test_flat_to_nested(self):
        flat = {
            "id": "test-id",
            "name": "测试项目",
            "category": "商业",
            "location": "北京",
            "structure": "框架结构",
            "floor_above": 6,
            "floor_below": 2,
            "area_total": 150000,
            "height": 35,
            "unit_cost": 3000,
            "steel": 55,
            "concrete": 0.45,
        }
        result = IndicatorService._to_legacy_format(flat)
        assert result["indicators"]["unit_cost"] == 3000
        assert result["material_content"]["steel"] == 55
        assert result["material_content"]["concrete"] == 0.45