"""
指标库服务层
提供指标库CRUD、修正系数、匹配算法、质量审核等核心服务
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================
# 修正系数
# ============================================================

CORRECTION_FACTORS = {
    "height": {
        "30": 1.00,
        "60": 1.03,
        "100": 1.08,
        "150": 1.15
    },
    "structure": {
        "框架结构": {"steel": 1.00, "concrete": 1.00},
        "框剪结构": {"steel": 1.15, "concrete": 1.10},
        "剪力墙结构": {"steel": 1.25, "concrete": 1.15},
        "框架核心筒": {"steel": 1.20, "concrete": 1.12},
        "钢结构": {"steel": 0.90, "concrete": 0.70}
    },
    "region": {
        "一线城市": 1.00,
        "二线城市": 0.92,
        "三线城市": 0.85,
        "四线城市": 0.78
    }
}


class IndicatorService:
    """指标库服务"""

    # ========== 修正系数 ==========

    @staticmethod
    def get_height_correction(height: float) -> float:
        """获取高度修正系数"""
        if height <= 30:
            return CORRECTION_FACTORS["height"]["30"]
        elif height <= 60:
            return CORRECTION_FACTORS["height"]["60"]
        elif height <= 100:
            return CORRECTION_FACTORS["height"]["100"]
        else:
            return CORRECTION_FACTORS["height"]["150"]

    @staticmethod
    def get_structure_correction(structure: str) -> Dict[str, float]:
        """获取结构形式修正系数"""
        for key, factors in CORRECTION_FACTORS["structure"].items():
            if key in structure or structure in key:
                return factors
        return {"steel": 1.00, "concrete": 1.00}

    @staticmethod
    def get_region_correction(location: str) -> float:
        """获取地区修正系数"""
        loc_lower = location.lower()

        tier1_cities = ["北京", "上海", "广州", "深圳"]
        for city in tier1_cities:
            if city in loc_lower:
                return CORRECTION_FACTORS["region"]["一线城市"]

        province_capitals = ["济南", "青岛", "杭州", "南京", "武汉", "成都", "西安", "郑州", "长沙", "合肥"]
        for city in province_capitals:
            if city in loc_lower:
                return CORRECTION_FACTORS["region"]["二线城市"]

        if "山东" in loc_lower or "省" in loc_lower:
            return CORRECTION_FACTORS["region"]["二线城市"]

        return CORRECTION_FACTORS["region"]["二线城市"]

    # ========== 修正后指标计算 ==========

    @staticmethod
    def calculate_corrected_indicators(
        base_unit_cost: float,
        base_steel: Optional[float],
        base_concrete: Optional[float],
        target_height: float,
        target_structure: str,
        target_location: str
    ) -> Dict[str, float]:
        """计算修正后的指标"""
        height_factor = IndicatorService.get_height_correction(target_height)
        structure_factors = IndicatorService.get_structure_correction(target_structure)
        region_factor = IndicatorService.get_region_correction(target_location)
        total_factor = height_factor * region_factor

        result = {
            "corrected_unit_cost": round(base_unit_cost * total_factor, 2),
            "correction_factors": {
                "height_factor": round(height_factor, 2),
                "region_factor": round(region_factor, 2),
                "total_factor": round(total_factor, 2)
            }
        }

        if base_steel:
            steel_factor = structure_factors["steel"] * height_factor
            result["corrected_steel"] = round(base_steel * steel_factor, 2)
            result["correction_factors"]["steel_factor"] = round(steel_factor, 2)

        if base_concrete:
            concrete_factor = structure_factors["concrete"] * height_factor
            result["corrected_concrete"] = round(base_concrete * concrete_factor, 2)
            result["correction_factors"]["concrete_factor"] = round(concrete_factor, 2)

        return result

    # ========== 匹配算法 ==========

    @staticmethod
    def calculate_match_score(target: Dict, db_item: Dict) -> Dict:
        """计算匹配分数"""
        category_score = 30 if target.get("category") == db_item.get("category") else 0

        target_struct = (target.get("structure") or "").lower()
        db_struct = (db_item.get("structure") or "").lower()

        if target_struct == db_struct:
            structure_score = 25
        elif "框架" in target_struct and "框架" in db_struct:
            structure_score = 22
        elif "剪力墙" in target_struct and "剪力墙" in db_struct:
            structure_score = 22
        elif "核心筒" in target_struct and "核心筒" in db_struct:
            structure_score = 20
        else:
            structure_score = 10

        target_loc = (target.get("location") or "").lower()
        db_loc = (db_item.get("location") or "").lower()

        if target_loc == db_loc or target_loc in db_loc or db_loc in target_loc:
            location_score = 20
        elif ("北京" in target_loc and "北京" in db_loc) or \
             ("山东" in target_loc and "山东" in db_loc):
            location_score = 18
        else:
            location_score = 12

        height_diff = abs((target.get("height") or 0) - (db_item.get("height") or 0))
        height_diff_pct = (height_diff / (target.get("height") or 1) * 100) if target.get("height") else 0

        if height_diff <= 5:
            height_score = 25
        elif height_diff <= 10:
            height_score = 22
        elif height_diff <= 20:
            height_score = 18
        elif height_diff <= 30:
            height_score = 12
        else:
            height_score = 5

        score = category_score + structure_score + location_score + height_score

        if score >= 80:
            recommendation = "推荐使用"
        elif score >= 60:
            recommendation = "可参考"
        else:
            recommendation = "慎用"

        return {
            "total_score": score,
            "category_score": category_score,
            "structure_score": structure_score,
            "location_score": location_score,
            "height_score": height_score,
            "height_diff": round(height_diff, 2),
            "height_diff_pct": round(height_diff_pct, 2),
            "recommendation": recommendation
        }

    @staticmethod
    def find_matched_indicators(
        target: Dict,
        database: List[Dict],
        limit: int = 5
    ) -> List[Dict]:
        """查找匹配的指标项"""
        matches = []

        for item in database:
            if target.get("category") != item.get("category"):
                continue

            match_result = IndicatorService.calculate_match_score(target, item)

            indicators = item.get("indicators", {})
            material = item.get("material_content", {})

            corrected = IndicatorService.calculate_corrected_indicators(
                base_unit_cost=indicators.get("unit_cost", 0),
                base_steel=material.get("steel"),
                base_concrete=material.get("concrete"),
                target_height=target.get("height", 0),
                target_structure=target.get("structure", ""),
                target_location=target.get("location", "")
            )

            matches.append({
                "project_id": item.get("id"),
                "project_name": item.get("name"),
                "match_score": match_result["total_score"],
                "recommendation": match_result["recommendation"],
                "height_diff": match_result["height_diff"],
                "height_diff_pct": match_result["height_diff_pct"],
                "category_match": round(match_result["category_score"] / 30 * 100, 1),
                "structure_match": round(match_result["structure_score"] / 25 * 100, 1),
                "location_match": round(match_result["location_score"] / 20 * 100, 1),
                "corrected_unit_cost": corrected.get("corrected_unit_cost"),
                "corrected_steel": corrected.get("corrected_steel"),
                "corrected_concrete": corrected.get("corrected_concrete")
            })

        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches[:limit]

    # ========== 对比分析 ==========

    @staticmethod
    def analyze_comparison(
        target_unit_cost: float,
        target_steel: Optional[float],
        target_concrete: Optional[float],
        matched: List[Dict],
        database: List[Dict]
    ) -> List[Dict]:
        """分析指标对比"""
        comparisons = []

        if not matched:
            return comparisons

        ref_project = None
        for item in database:
            if item.get("id") == matched[0].get("project_id"):
                ref_project = item
                break

        if not ref_project:
            return comparisons

        ref = ref_project.get("indicators", {})
        ref_material = ref_project.get("material_content", {})

        if target_unit_cost and ref.get("unit_cost"):
            dev = (target_unit_cost - ref["unit_cost"]) / ref["unit_cost"] * 100
            corrected_dev = None
            if matched[0].get("corrected_unit_cost"):
                corrected_dev = (target_unit_cost - matched[0]["corrected_unit_cost"]) / matched[0]["corrected_unit_cost"] * 100

            status = "正常" if abs(corrected_dev or dev) <= 15 else ("偏高" if (corrected_dev or dev) > 0 else "偏低")
            comparisons.append({
                "indicator_name": "单方造价",
                "target_value": target_unit_cost,
                "reference_value": ref["unit_cost"],
                "corrected_reference": matched[0].get("corrected_unit_cost"),
                "deviation": round(dev, 2),
                "corrected_deviation": round(corrected_dev, 2) if corrected_dev else None,
                "status": status
            })

        if target_steel and ref_material.get("steel"):
            dev = (target_steel - ref_material["steel"]) / ref_material["steel"] * 100
            corrected_dev = None
            if matched[0].get("corrected_steel"):
                corrected_dev = (target_steel - matched[0]["corrected_steel"]) / matched[0]["corrected_steel"] * 100

            status = "正常" if abs(corrected_dev or dev) <= 20 else ("偏高" if (corrected_dev or dev) > 0 else "偏低")
            comparisons.append({
                "indicator_name": "钢筋含量(kg/㎡)",
                "target_value": target_steel,
                "reference_value": ref_material["steel"],
                "corrected_reference": matched[0].get("corrected_steel"),
                "deviation": round(dev, 2),
                "corrected_deviation": round(corrected_dev, 2) if corrected_dev else None,
                "status": status
            })

        if target_concrete and ref_material.get("concrete"):
            dev = (target_concrete - ref_material["concrete"]) / ref_material["concrete"] * 100
            corrected_dev = None
            if matched[0].get("corrected_concrete"):
                corrected_dev = (target_concrete - matched[0]["corrected_concrete"]) / matched[0]["corrected_concrete"] * 100

            status = "正常" if abs(corrected_dev or dev) <= 15 else ("偏高" if (corrected_dev or dev) > 0 else "偏低")
            comparisons.append({
                "indicator_name": "混凝土含量(m³/㎡)",
                "target_value": target_concrete,
                "reference_value": ref_material["concrete"],
                "corrected_reference": matched[0].get("corrected_concrete"),
                "deviation": round(dev, 2),
                "corrected_deviation": round(corrected_dev, 2) if corrected_dev else None,
                "status": status
            })

        return comparisons

    # ========== 造价分解 ==========

    @staticmethod
    def generate_cost_breakdown(indicators: Dict) -> List[Dict]:
        """生成造价分解"""
        breakdowns = []

        if indicators.get("unit_cost"):
            total = indicators["unit_cost"]

            struct = indicators.get("unit_structure") or total * 0.6
            breakdowns.append({
                "category": "土建工程",
                "amount": round(struct, 2),
                "proportion": round(struct / total * 100, 1)
            })

            install = indicators.get("unit_installation") or total * 0.2
            breakdowns.append({
                "category": "安装工程",
                "amount": round(install, 2),
                "proportion": round(install / total * 100, 1)
            })

            decor = indicators.get("unit_decoration") or total * 0.15
            breakdowns.append({
                "category": "装饰工程",
                "amount": round(decor, 2),
                "proportion": round(decor / total * 100, 1)
            })

            measures = total - struct - install - decor
            if measures > 0:
                breakdowns.append({
                    "category": "措施项目",
                    "amount": round(measures, 2),
                    "proportion": round(measures / total * 100, 1)
                })

        return breakdowns

    # ========== 修正系数说明 ==========

    @staticmethod
    def generate_corrections(target: Dict, matched: List[Dict]) -> List[Dict]:
        """生成修正系数说明"""
        corrections = []

        if not matched:
            return corrections

        height_correction = IndicatorService.get_height_correction(target.get("height", 0))
        if height_correction != 1.0:
            corrections.append({
                "factor_type": "height",
                "factor_value": height_correction,
                "reason": f"檐高{target.get('height')}m对应修正系数{height_correction}"
            })

        structure_correction = IndicatorService.get_structure_correction(target.get("structure", ""))
        if structure_correction["steel"] != 1.0:
            corrections.append({
                "factor_type": "structure",
                "factor_value": structure_correction["steel"],
                "reason": f"结构形式{target.get('structure')}钢筋修正系数{structure_correction['steel']}"
            })

        region_correction = IndicatorService.get_region_correction(target.get("location", ""))
        if region_correction != 1.0:
            corrections.append({
                "factor_type": "region",
                "factor_value": region_correction,
                "reason": f"地区{target.get('location')}造价修正系数{region_correction}"
            })

        return corrections

    # ========== 建议生成 ==========

    @staticmethod
    def generate_suggestions(
        target_indicators: Dict,
        comparison: List[Dict],
        matched: List[Dict]
    ) -> List[str]:
        """生成建议"""
        suggestions = []

        if not matched:
            suggestions.append("未找到完全匹配的参考指标，建议扩大搜索条件或选择相近业态进行对比")
            return suggestions

        for comp in comparison:
            dev = comp.get("corrected_deviation") or comp.get("deviation", 0)
            if comp.get("indicator_name") == "单方造价" and abs(dev) > 15:
                if dev > 0:
                    suggestions.append(f"单方造价偏高{abs(dev):.1f}%，建议核实设计标准或施工方案")
                else:
                    suggestions.append(f"单方造价偏低{abs(dev):.1f}%，建议核实材料价格或工程量")

            if comp.get("indicator_name") == "钢筋含量(kg/㎡)" and abs(dev) > 20:
                if dev > 0:
                    suggestions.append(f"钢筋含量偏高{abs(dev):.1f}%，建议核实结构设计或钢筋配置")
                else:
                    suggestions.append(f"钢筋含量偏低{abs(dev):.1f}%，建议核实是否存在优化空间")

        if matched and matched[0].get("match_score", 0) >= 80:
            suggestions.append("与参考项目匹配度较高，指标具有较高参考价值")
        elif matched and matched[0].get("match_score", 0) >= 60:
            suggestions.append("与参考项目存在一定差异，建议结合多个项目综合判断")

        return suggestions if suggestions else ["指标在合理范围内"]

    # ========== 风险提示 ==========

    @staticmethod
    def generate_risk_warnings(target: Dict, comparison: List[Dict]) -> List[str]:
        """生成风险提示"""
        warnings = []

        height = target.get("height", 0)
        if height > 100:
            warnings.append(f"超高建筑(檐高{height}m)，需考虑垂直运输、超高层修正等额外成本")
        elif height > 60:
            warnings.append(f"高层建筑(檐高{height}m)，垂直运输成本增加")

        floor_below = target.get("floor_below", 0)
        if floor_below >= 3:
            warnings.append(f"深基坑(地下{floor_below}层)，土方及基坑支护成本较高")

        area_total = target.get("area_total", 0)
        if area_total < 10000:
            warnings.append("建筑面积较小，单方指标可能偏高，建议适当上调")
        elif area_total > 200000:
            warnings.append("建筑面积较大，可发挥规模效应，单方指标可适度下调")

        for comp in comparison:
            dev = abs(comp.get("corrected_deviation") or comp.get("deviation", 0))
            if dev > 30:
                warnings.append(f"{comp.get('indicator_name')}偏差超过30%，建议重点复核")

        return warnings

    # ========== 质量审核 ==========

    @staticmethod
    def quality_check(project: Dict, indicators: Dict) -> Dict:
        """质量审核"""
        checks = []
        warnings = []
        passed = True

        area_above = project.get("area_above")
        area_below = project.get("area_below")
        if area_above and area_below:
            expected_total = area_above + area_below
            diff = abs(expected_total - project.get("area_total", 0))
            if diff > 1:
                checks.append({
                    "check_type": "area",
                    "description": f"地上面积+地下面积={expected_total}，总建筑面积={project.get('area_total')}",
                    "status": "error",
                    "detail": f"面积差异{diff}㎡"
                })
                passed = False
            else:
                checks.append({
                    "check_type": "area",
                    "description": "面积一致性检查",
                    "status": "pass",
                    "detail": "面积一致"
                })
        else:
            checks.append({
                "check_type": "area",
                "description": "面积数据不完整，跳过一致性检查",
                "status": "warn",
                "detail": "建议补充地上/地下面积"
            })

        ref_ranges = {
            "住宅": {"框架结构": (1800, 2500), "剪力墙结构": (2200, 3000)},
            "商业": {"框架结构": (2500, 4000)},
            "办公": {"框架结构": (2800, 4500)},
        }

        category = project.get("category")
        unit_cost = indicators.get("unit_cost", 0)
        if category in ref_ranges and unit_cost:
            struct_type = "框架结构"
            structure = project.get("structure", "")
            for s in ref_ranges[category]:
                if s in structure:
                    struct_type = s
                    break

            if struct_type in ref_ranges[category]:
                min_val, max_val = ref_ranges[category][struct_type]
                if unit_cost < min_val or unit_cost > max_val:
                    checks.append({
                        "check_type": "range",
                        "description": f"单方造价{unit_cost}元/㎡超出参考范围{min_val}-{max_val}",
                        "status": "warn",
                        "detail": "建议核实数据来源"
                    })
                    warnings.append("单方造价超出参考范围")
                else:
                    checks.append({
                        "check_type": "range",
                        "description": "单方造价在合理范围内",
                        "status": "pass",
                        "detail": f"{unit_cost}元/㎡"
                    })

        steel = indicators.get("steel") or indicators.get("material_content", {}).get("steel")
        if steel:
            if steel < 15 or steel > 80:
                checks.append({
                    "check_type": "range",
                    "description": f"钢筋含量{steel}kg/㎡超出合理范围15-80",
                    "status": "warn",
                    "detail": "建议核实"
                })
                warnings.append("钢筋含量可能异常")
            else:
                checks.append({
                    "check_type": "range",
                    "description": "钢筋含量在合理范围内",
                    "status": "pass",
                    "detail": f"{steel}kg/㎡"
                })

        if all([
            indicators.get("unit_structure"),
            indicators.get("unit_installation"),
            indicators.get("unit_decoration"),
            indicators.get("unit_measure")
        ]):
            sum_parts = (
                indicators["unit_structure"] +
                indicators["unit_installation"] +
                indicators["unit_decoration"] +
                indicators["unit_measure"]
            )
            diff = abs(sum_parts - unit_cost)
            if diff > 50:
                checks.append({
                    "check_type": "logic",
                    "description": f"分项之和={sum_parts}，单方造价={unit_cost}",
                    "status": "warn",
                    "detail": "分项和与单方造价差异较大"
                })
                warnings.append("分项造价之和不等于总单方造价")
            else:
                checks.append({
                    "check_type": "logic",
                    "description": "分项造价逻辑检查",
                    "status": "pass",
                    "detail": f"差异{diff}元/㎡"
                })

        return {
            "project_id": project.get("name", ""),
            "passed": passed,
            "checks": checks,
            "warnings": warnings
        }

    # ========== 格式转换 ==========

    @staticmethod
    def _to_legacy_format(project: Dict) -> Dict:
        """将 Supabase 扁平格式转换为嵌套格式（兼容原有算法）"""
        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "category": project.get("category"),
            "location": project.get("location"),
            "structure": project.get("structure"),
            "floor_above": project.get("floor_above", 0),
            "floor_below": project.get("floor_below", 0),
            "area_total": project.get("area_total", 0),
            "area_above": project.get("area_above"),
            "area_below": project.get("area_below"),
            "height": project.get("height", 0),
            "complete_date": project.get("complete_date"),
            "source": project.get("source", "结算文件"),
            "source_file": project.get("source_file"),
            "remarks": project.get("remarks"),
            "indicators": {
                "total_cost": project.get("total_cost"),
                "unit_cost": project.get("unit_cost", 0),
                "unit_structure": project.get("unit_structure"),
                "unit_installation": project.get("unit_installation"),
                "unit_decoration": project.get("unit_decoration"),
                "unit_measure": project.get("unit_measure"),
            },
            "material_content": {
                "steel": project.get("steel"),
                "concrete": project.get("concrete"),
                "formwork": project.get("formwork"),
                "block": project.get("block"),
                "cable": project.get("cable"),
                "pipe": project.get("pipe"),
                "duct": project.get("duct"),
            },
            "economical_indicators": {
                "underground_structure": project.get("underground_structure"),
                "above_structure": project.get("above_structure"),
                "roof": project.get("roof"),
                "exterior_wall": project.get("exterior_wall"),
                "interior_wall": project.get("interior_wall"),
                "floor": project.get("floor"),
                "electrical": project.get("electrical"),
                "plumbing": project.get("plumbing"),
                "hvac": project.get("hvac"),
                "elevator": project.get("elevator"),
                "fire": project.get("fire"),
                "measures": project.get("measures"),
            }
        }