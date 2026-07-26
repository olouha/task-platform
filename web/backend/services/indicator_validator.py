"""
指标库数据验证服务
提供三层验证：基础验证、逻辑验证、参考范围验证
"""

import logging
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# 处理导入路径：支持直接运行和包内导入
if "web.backend.models.indicator_library" in sys.modules:
    from web.backend.models.indicator_library import (
        IndicatorLibraryDetail,
        IndicatorLibraryCreate,
        ValidationWarning,
        ValidationResult,
    )
else:
    try:
        from ..models.indicator_library import (
            IndicatorLibraryDetail,
            IndicatorLibraryCreate,
            ValidationWarning,
            ValidationResult,
        )
    except ImportError:
        # 直接运行时使用绝对导入
        from models.indicator_library import (
            IndicatorLibraryDetail,
            IndicatorLibraryCreate,
            ValidationWarning,
            ValidationResult,
        )

logger = logging.getLogger(__name__)


class REFERENCE_RANGES:
    """
    各业态参考范围数据
    基于行业经验和典型项目数据
    """

    # 业态定义
    CATEGORIES = ["住宅", "商业", "办公", "工业"]

    # 平米造价参考范围 (元/㎡)
    UNIT_COST = {
        "住宅": {"min": 1500, "max": 4500, "typical": 2500},
        "商业": {"min": 3000, "max": 8000, "typical": 5000},
        "办公": {"min": 2500, "max": 6000, "typical": 4000},
        "工业": {"min": 1500, "max": 3500, "typical": 2200},
    }

    # 地上砼含量参考范围 (m³/㎡)
    ABOVE_CONCRETE_UNIT = {
        "住宅": {"min": 0.25, "max": 0.45, "typical": 0.35},
        "商业": {"min": 0.30, "max": 0.55, "typical": 0.42},
        "办公": {"min": 0.28, "max": 0.50, "typical": 0.38},
        "工业": {"min": 0.20, "max": 0.40, "typical": 0.30},
    }

    # 地下砼含量参考范围 (m³/㎡)
    UNDERGROUND_CONCRETE_UNIT = {
        "住宅": {"min": 0.80, "max": 1.50, "typical": 1.10},
        "商业": {"min": 1.00, "max": 2.00, "typical": 1.40},
        "办公": {"min": 0.90, "max": 1.80, "typical": 1.25},
        "工业": {"min": 0.70, "max": 1.30, "typical": 1.00},
    }

    # 地上钢筋含量参考范围 (t/㎡)
    ABOVE_REBAR_UNIT = {
        "住宅": {"min": 0.035, "max": 0.065, "typical": 0.050},
        "商业": {"min": 0.045, "max": 0.085, "typical": 0.065},
        "办公": {"min": 0.040, "max": 0.075, "typical": 0.055},
        "工业": {"min": 0.030, "max": 0.060, "typical": 0.045},
    }

    # 地下钢筋含量参考范围 (t/㎡)
    UNDERGROUND_REBAR_UNIT = {
        "住宅": {"min": 0.100, "max": 0.180, "typical": 0.140},
        "商业": {"min": 0.120, "max": 0.220, "typical": 0.165},
        "办公": {"min": 0.110, "max": 0.200, "typical": 0.150},
        "工业": {"min": 0.090, "max": 0.160, "typical": 0.125},
    }

    # 地上模板含量参考范围 (m²/㎡)
    ABOVE_FORMWORK_UNIT = {
        "住宅": {"min": 2.0, "max": 3.5, "typical": 2.8},
        "商业": {"min": 2.5, "max": 4.0, "typical": 3.2},
        "办公": {"min": 2.2, "max": 3.8, "typical": 3.0},
        "工业": {"min": 1.8, "max": 3.0, "typical": 2.4},
    }

    # 地下模板含量参考范围 (m²/㎡)
    UNDERGROUND_FORMWORK_UNIT = {
        "住宅": {"min": 3.5, "max": 5.5, "typical": 4.5},
        "商业": {"min": 4.0, "max": 6.5, "typical": 5.2},
        "办公": {"min": 3.8, "max": 6.0, "typical": 4.8},
        "工业": {"min": 3.0, "max": 5.0, "typical": 4.0},
    }

    # 措施费占直接费比例参考范围
    MEASURES_RATIO = {
        "住宅": {"min": 0.08, "max": 0.15, "typical": 0.11},
        "商业": {"min": 0.10, "max": 0.18, "typical": 0.14},
        "办公": {"min": 0.09, "max": 0.16, "typical": 0.12},
        "工业": {"min": 0.07, "max": 0.14, "typical": 0.10},
    }

    # 室外工程占直接费比例参考范围
    OUTDOOR_RATIO = {
        "住宅": {"min": 0.03, "max": 0.08, "typical": 0.05},
        "商业": {"min": 0.04, "max": 0.10, "typical": 0.06},
        "办公": {"min": 0.03, "max": 0.08, "typical": 0.05},
        "工业": {"min": 0.02, "max": 0.06, "typical": 0.04},
    }

    # 桩基工程占直接费比例参考范围
    PILE_RATIO = {
        "住宅": {"min": 0.05, "max": 0.15, "typical": 0.10},
        "商业": {"min": 0.08, "max": 0.20, "typical": 0.13},
        "办公": {"min": 0.06, "max": 0.18, "typical": 0.11},
        "工业": {"min": 0.04, "max": 0.12, "typical": 0.08},
    }


class IndicatorValidator:
    """
    指标库数据验证器

    提供三层验证：
    1. 基础验证：必填字段、值范围、日期格式
    2. 逻辑验证：字段间一致性（总面积≈地上+地下，总造价≈地上+地下等）
    3. 参考范围验证：与同类项目的典型范围对比
    """

    # 必填字段列表
    REQUIRED_FIELDS = ["name", "category", "location", "structure"]

    # 非数值字段（字符串/日期/枚举/元数据）；未列入的字段默认按数值校验
    STRING_FIELDS = {
        "index", "name", "category", "location", "structure", "delivery_type",
        "foundation_type", "floor_info", "start_date", "end_date", "remarks",
        "source", "source_file", "entry_date", "id", "_row_index", "uploaded_by",
        "created_at", "updated_at", "verified_at", "verified_by", "snapshot_id",
    }

    # 日期格式正则
    DATE_PATTERN = re.compile(r"^\d{4}-\d{2}$")  # YYYY-MM
    DATE_FULL_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")  # YYYY-MM-DDTHH:MM:SS

    # 数值精度容差（用于逻辑验证）
    TOLERANCE_RATIO = 0.02  # 2% 容差
    TOLERANCE_ABSOLUTE = 1000  # 绝对值容差 1000 元

    def __init__(self, strict_mode: bool = False):
        """
        初始化验证器

        Args:
            strict_mode: 严格模式，会将更多问题标记为错误而非警告
        """
        self.strict_mode = strict_mode
        logger.info(f"[IndicatorValidator] 初始化验证器 | strict_mode={strict_mode}")

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        执行完整的三层验证

        Args:
            data: 待验证的数据字典

        Returns:
            ValidationResult: 验证结果
        """
        logger.info(f"[IndicatorValidator] 开始验证 | name={data.get('name', 'N/A')}")

        errors: List[ValidationWarning] = []
        warnings: List[ValidationWarning] = []
        checks: Dict[str, str] = {}

        # 第一层：基础验证
        basic_result = self._validate_basic(data)
        errors.extend(basic_result.errors)
        warnings.extend(basic_result.warnings)
        checks["required_fields"] = "PASS" if not basic_result.errors else "FAIL"
        checks["value_ranges"] = "PASS" if not any(
            w.severity == "error" for w in basic_result.warnings
        ) else "FAIL"

        # 第二层：逻辑验证
        logical_result = self._validate_logical(data)
        errors.extend(logical_result.errors)
        warnings.extend(logical_result.warnings)
        checks["logical_consistency"] = "PASS" if not logical_result.errors else "FAIL"

        # 第三层：参考范围验证
        reference_result = self._validate_reference_range(data)
        warnings.extend(reference_result.warnings)
        checks["reference_ranges"] = "PASS" if not reference_result.warnings else "WARNING"

        # 判断是否通过
        passed = len(errors) == 0

        logger.info(
            f"[IndicatorValidator] 验证完成 | passed={passed} | errors={len(errors)} | warnings={len(warnings)}"
        )

        return ValidationResult(
            passed=passed,
            warnings=warnings,
            errors=errors,
            checks=checks,
        )

    def _normalize_numeric_fields(
        self, data: Dict[str, Any], errors: List[ValidationWarning]
    ) -> None:
        """数值字段类型规范化：字符串数字转 float，无法转换的记 error 并置 None

        入库层（SQLite 动态类型）不会因类型不符报错，"25000元" 会被静默存为文本，
        因此必须在验证层拦截。同时防止后续 `value <= 0` 在收到字符串时抛 TypeError
        导致整个导入失败。
        """
        for field in list(data.keys()):
            if field in self.STRING_FIELDS:
                continue
            value = data.get(field)
            # bool 是 int 子类，跳过
            if isinstance(value, bool):
                continue
            if isinstance(value, str) and value.strip():
                raw = value.strip().replace(",", "")  # 兼容千分位 "25,000"
                try:
                    data[field] = float(raw)
                except (ValueError, TypeError):
                    errors.append(
                        ValidationWarning(
                            field=field,
                            message="应填纯数字，不要带单位或文字（如 \"25000元\" 应写 \"25000\"）",
                            severity="error",
                            value=value,
                            expected="纯数字（不要单位、不要千分位逗号）",
                        )
                    )
                    logger.warning(
                        f"[IndicatorValidator] 数值字段类型错误 | field={field} | value={value!r}"
                    )
                    data[field] = None  # 防止后续数值比较崩溃

    def _validate_basic(self, data: Dict[str, Any]) -> ValidationResult:
        """
        第一层验证：基础验证

        检查：
        - 必填字段是否完整
        - 值范围是否合理
        - 日期格式是否正确

        Args:
            data: 待验证的数据字典

        Returns:
            ValidationResult: 基础验证结果
        """
        logger.debug(f"[IndicatorValidator] 执行基础验证")
        errors: List[ValidationWarning] = []
        warnings: List[ValidationWarning] = []

        # 0. 数值字段类型规范化（字符串数字转 float，非法值记错并防崩溃）
        self._normalize_numeric_fields(data, errors)

        # 1. 检查必填字段
        for field in self.REQUIRED_FIELDS:
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(
                    ValidationWarning(
                        field=field,
                        message=f"必填字段不能为空",
                        severity="error",
                        value=value,
                        expected="非空字符串",
                    )
                )
                logger.warning(f"[IndicatorValidator] 必填字段为空 | field={field}")

        # 2. 检查字段值范围
        # 建筑面积检查
        if data.get("area_total") is not None:
            area_total = data["area_total"]
            if area_total <= 0:
                errors.append(
                    ValidationWarning(
                        field="area_total",
                        message="建筑面积必须大于0",
                        severity="error",
                        value=area_total,
                        expected="> 0",
                    )
                )
            elif area_total < 100:
                warnings.append(
                    ValidationWarning(
                        field="area_total",
                        message="建筑面积过小，可能数据有误",
                        severity="warning",
                        value=area_total,
                        expected=">= 100 ㎡",
                    )
                )
            elif area_total > 500000:
                warnings.append(
                    ValidationWarning(
                        field="area_total",
                        message="建筑面积过大，请确认",
                        severity="warning",
                        value=area_total,
                        expected="<= 500000 ㎡",
                    )
                )

        # 地上/地下建筑面积检查
        area_above = data.get("area_above")
        area_below = data.get("area_below")
        area_total = data.get("area_total")

        if area_above is not None and area_above < 0:
            errors.append(
                ValidationWarning(
                    field="area_above",
                    message="地上建筑面积不能为负",
                    severity="error",
                    value=area_above,
                    expected=">= 0",
                )
            )

        if area_below is not None and area_below < 0:
            errors.append(
                ValidationWarning(
                    field="area_below",
                    message="地下建筑面积不能为负",
                    severity="error",
                    value=area_below,
                    expected=">= 0",
                )
            )

        # 造价字段检查
        if data.get("unit_cost") is not None:
            unit_cost = data["unit_cost"]
            if unit_cost <= 0:
                errors.append(
                    ValidationWarning(
                        field="unit_cost",
                        message="平米造价必须大于0",
                        severity="error",
                        value=unit_cost,
                        expected="> 0",
                    )
                )

        if data.get("total_cost") is not None:
            total_cost = data["total_cost"]
            if total_cost <= 0:
                errors.append(
                    ValidationWarning(
                        field="total_cost",
                        message="总造价必须大于0",
                        severity="error",
                        value=total_cost,
                        expected="> 0",
                    )
                )

        # 3. 日期格式检查
        date_fields = ["start_date", "end_date"]
        for field in date_fields:
            value = data.get(field)
            if value:
                if not self._validate_date_format(value):
                    errors.append(
                        ValidationWarning(
                            field=field,
                            message="日期格式不正确，应为 YYYY-MM 格式",
                            severity="error",
                            value=value,
                            expected="YYYY-MM (如: 2024-01)",
                        )
                    )
                    logger.warning(f"[IndicatorValidator] 日期格式错误 | field={field} | value={value}")

        # 开工/竣工时间逻辑检查
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        # 只有两个都是字符串时才做日期比较（Excel 可能返回 int/float）
        if isinstance(start_date, str) and isinstance(end_date, str):
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m")
                end_dt = datetime.strptime(end_date, "%Y-%m")
                if start_dt > end_dt:
                    errors.append(
                        ValidationWarning(
                            field="end_date",
                            message="竣工时间不能早于开工时间",
                            severity="error",
                            value=end_date,
                            expected=f"> {start_date}",
                        )
                    )
            except ValueError:
                pass  # 日期格式已在上一步检查

        # 4. 层数检查
        floor_above = data.get("floor_above")
        floor_below = data.get("floor_below")

        if floor_above is not None and floor_above < 0:
            errors.append(
                ValidationWarning(
                    field="floor_above",
                    message="地上层数不能为负",
                    severity="error",
                    value=floor_above,
                    expected=">= 0",
                )
            )

        if floor_below is not None and floor_below < 0:
            errors.append(
                ValidationWarning(
                    field="floor_below",
                    message="地下层数不能为负",
                    severity="error",
                    value=floor_below,
                    expected=">= 0",
                )
            )

        logger.debug(f"[IndicatorValidator] 基础验证完成 | errors={len(errors)} | warnings={len(warnings)}")

        return ValidationResult(
            passed=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            checks={"basic_validation": "PASS" if len(errors) == 0 else "FAIL"},
        )

    def _validate_logical(self, data: Dict[str, Any]) -> ValidationResult:
        """
        第二层验证：逻辑验证

        检查字段间的一致性：
        - area_total ≈ area_above + area_below
        - total_cost ≈ cost_above + cost_underground
        - unit_cost × area_total ≈ total_cost
        - 单位含量的一致性（如 above_rebar / above_rebar_unit ≈ area_above）

        Args:
            data: 待验证的数据字典

        Returns:
            ValidationResult: 逻辑验证结果
        """
        logger.debug(f"[IndicatorValidator] 执行逻辑验证")
        errors: List[ValidationWarning] = []
        warnings: List[ValidationWarning] = []

        # 1. 建筑面积逻辑检查
        area_above = data.get("area_above")
        area_below = data.get("area_below")
        area_total = data.get("area_total")

        if all(v is not None for v in [area_above, area_below, area_total]):
            area_sum = area_above + area_below
            area_diff = abs(area_total - area_sum)

            # 使用相对容差或绝对容差
            tolerance = max(area_total * self.TOLERANCE_RATIO, 10)

            if area_diff > tolerance:
                error_msg = f"总面积与地上+地下面积之和不符，差异: {area_diff:.2f} ㎡"
                if self.strict_mode:
                    errors.append(
                        ValidationWarning(
                            field="area_total",
                            message=error_msg,
                            severity="error",
                            value=area_total,
                            expected=f"≈ {area_sum:.2f} (地上+地下)",
                        )
                    )
                else:
                    warnings.append(
                        ValidationWarning(
                            field="area_total",
                            message=error_msg,
                            severity="warning",
                            value=area_total,
                            expected=f"≈ {area_sum:.2f} (地上+地下)",
                        )
                    )
                logger.warning(
                    f"[IndicatorValidator] 建筑面积不一致 | area_total={area_total} | sum={area_sum} | diff={area_diff}"
                )

        # 2. 造价逻辑检查 - 平米造价与总面积计算总造价
        unit_cost = data.get("unit_cost")
        if unit_cost is not None and area_total is not None and area_total > 0:
            calculated_total = unit_cost * area_total
            actual_total = data.get("total_cost")

            if actual_total is not None and actual_total > 0:
                cost_diff_ratio = abs(actual_total - calculated_total) / calculated_total

                if cost_diff_ratio > self.TOLERANCE_RATIO:
                    error_msg = f"平米造价×面积计算的总额与填写的总造价不符，差异: {cost_diff_ratio*100:.1f}%"
                    if self.strict_mode:
                        errors.append(
                            ValidationWarning(
                                field="total_cost",
                                message=error_msg,
                                severity="error",
                                value=actual_total,
                                expected=f"≈ {calculated_total:.2f} (平米造价×面积)",
                            )
                        )
                    else:
                        warnings.append(
                            ValidationWarning(
                                field="total_cost",
                                message=error_msg,
                                severity="warning",
                                value=actual_total,
                                expected=f"≈ {calculated_total:.2f} (平米造价×面积)",
                            )
                        )
                    logger.warning(
                        f"[IndicatorValidator] 总造价不一致 | actual={actual_total} | calculated={calculated_total} | diff={cost_diff_ratio*100:.1f}%"
                    )

        # 3. 地上/地下造价逻辑检查
        cost_above_total = self._sum_costs(data, "above")
        cost_underground_total = self._sum_costs(data, "underground")
        total_cost = data.get("total_cost")

        if cost_above_total is not None and cost_underground_total is not None:
            sub_cost_sum = cost_above_total + cost_underground_total

            if total_cost is not None and total_cost > 0:
                cost_diff_ratio = abs(total_cost - sub_cost_sum) / total_cost

                if cost_diff_ratio > self.TOLERANCE_RATIO:
                    error_msg = f"地上+地下造价之和与总造价不符，差异: {cost_diff_ratio*100:.1f}%"
                    if self.strict_mode:
                        errors.append(
                            ValidationWarning(
                                field="total_cost",
                                message=error_msg,
                                severity="error",
                                value=total_cost,
                                expected=f"≈ {sub_cost_sum:.2f}",
                            )
                        )
                    else:
                        warnings.append(
                            ValidationWarning(
                                field="total_cost",
                                message=error_msg,
                                severity="warning",
                                value=total_cost,
                                expected=f"≈ {sub_cost_sum:.2f}",
                            )
                        )
                    logger.warning(
                        f"[IndicatorValidator] 地上地下造价和不一致 | total={total_cost} | sum={sub_cost_sum} | diff={cost_diff_ratio*100:.1f}%"
                    )

        # 4. 单位含量逻辑检查
        # 地上钢筋
        self._validate_unit_content(
            data, "above_rebar", "above_rebar_unit", "area_above", errors, warnings
        )
        # 地下钢筋
        self._validate_unit_content(
            data, "underground_rebar", "underground_rebar_unit", "area_below", errors, warnings
        )
        # 地上砼
        self._validate_unit_content(
            data, "above_concrete", "above_concrete_unit", "area_above", errors, warnings
        )
        # 地下砼
        self._validate_unit_content(
            data, "underground_concrete", "underground_concrete_unit", "area_below", errors, warnings
        )
        # 地上模板
        self._validate_unit_content(
            data, "above_formwork", "above_formwork_unit", "area_above", errors, warnings
        )
        # 地下模板
        self._validate_unit_content(
            data, "underground_formwork", "underground_formwork_unit", "area_below", errors, warnings
        )

        # 5. 单位造价逻辑检查
        self._validate_unit_cost(data, "cost_above_structure", "area_above", "unit_cost_above_structure", errors, warnings)
        self._validate_unit_cost(data, "cost_underground_structure", "area_below", "unit_cost_underground_structure", errors, warnings)
        self._validate_unit_cost(data, "cost_above_installation", "area_above", "unit_cost_above_installation", errors, warnings)
        self._validate_unit_cost(data, "cost_underground_installation", "area_below", "unit_cost_underground_installation", errors, warnings)

        logger.debug(f"[IndicatorValidator] 逻辑验证完成 | errors={len(errors)} | warnings={len(warnings)}")

        return ValidationResult(
            passed=len(errors) == 0,
            warnings=warnings,
            errors=errors,
            checks={"logical_validation": "PASS" if len(errors) == 0 else "FAIL"},
        )

    def _validate_reference_range(self, data: Dict[str, Any]) -> ValidationResult:
        """
        第三层验证：参考范围验证

        将数据与同类项目的典型范围进行对比，检查是否在合理范围内

        Args:
            data: 待验证的数据字典

        Returns:
            ValidationResult: 参考范围验证结果
        """
        logger.debug(f"[IndicatorValidator] 执行参考范围验证")
        warnings: List[ValidationWarning] = []

        category = data.get("category", "住宅")  # 默认住宅

        if category not in REFERENCE_RANGES.CATEGORIES:
            warnings.append(
                ValidationWarning(
                    field="category",
                    message=f"未知的业态类型，将使用住宅参考范围",
                    severity="warning",
                    value=category,
                    expected=f"可选值: {', '.join(REFERENCE_RANGES.CATEGORIES)}",
                )
            )
            category = "住宅"

        # 1. 平米造价检查
        unit_cost = data.get("unit_cost")
        if unit_cost is not None:
            range_info = REFERENCE_RANGES.UNIT_COST.get(category, REFERENCE_RANGES.UNIT_COST["住宅"])
            self._check_value_in_range(
                "unit_cost", unit_cost, range_info, "平米造价", "元/㎡", warnings
            )

        # 2. 材料含量检查
        self._check_reference_field(
            data, "above_concrete_unit", REFERENCE_RANGES.ABOVE_CONCRETE_UNIT, category, "地上砼含量", warnings
        )
        self._check_reference_field(
            data, "underground_concrete_unit", REFERENCE_RANGES.UNDERGROUND_CONCRETE_UNIT, category, "地下砼含量", warnings
        )
        self._check_reference_field(
            data, "above_rebar_unit", REFERENCE_RANGES.ABOVE_REBAR_UNIT, category, "地上钢筋含量", warnings
        )
        self._check_reference_field(
            data, "underground_rebar_unit", REFERENCE_RANGES.UNDERGROUND_REBAR_UNIT, category, "地下钢筋含量", warnings
        )
        self._check_reference_field(
            data, "above_formwork_unit", REFERENCE_RANGES.ABOVE_FORMWORK_UNIT, category, "地上模板含量", warnings
        )
        self._check_reference_field(
            data, "underground_formwork_unit", REFERENCE_RANGES.UNDERGROUND_FORMWORK_UNIT, category, "地下模板含量", warnings
        )

        logger.debug(f"[IndicatorValidator] 参考范围验证完成 | warnings={len(warnings)}")

        return ValidationResult(
            passed=True,  # 参考范围验证不产生错误，只产生警告
            warnings=warnings,
            errors=[],
            checks={"reference_range_validation": "PASS" if len(warnings) == 0 else "WARNING"},
        )

    def _validate_date_format(self, value: str) -> bool:
        """
        验证日期格式

        Args:
            value: 日期字符串

        Returns:
            bool: 是否有效
        """
        if not isinstance(value, str):
            return False
        if self.DATE_PATTERN.match(value):
            return True
        if self.DATE_FULL_PATTERN.match(value):
            return True
        if self.DATETIME_PATTERN.match(value):
            return True
        return False

    def _sum_costs(self, data: Dict[str, Any], prefix: str) -> Optional[float]:
        """
        计算指定前缀的造价总和

        Args:
            data: 数据字典
            prefix: 前缀 (above/underground)

        Returns:
            造价总和，如果相关字段都不存在则返回None
        """
        structure_field = f"cost_{prefix}_structure"
        installation_field = f"cost_{prefix}_installation"

        total = 0.0
        has_value = False

        for field in [structure_field, installation_field]:
            value = data.get(field)
            if value is not None and value > 0:
                total += value
                has_value = True

        return total if has_value else None

    def _validate_unit_content(
        self,
        data: Dict[str, Any],
        total_field: str,
        unit_field: str,
        area_field: str,
        errors: List[ValidationWarning],
        warnings: List[ValidationWarning],
    ) -> None:
        """
        验证单位含量的一致性

        Args:
            data: 数据字典
            total_field: 总量字段名
            unit_field: 单位含量字段名
            area_field: 面积字段名
            errors: 错误列表
            warnings: 警告列表
        """
        total = data.get(total_field)
        unit = data.get(unit_field)
        area = data.get(area_field)

        # 如果同时有总量和面积，检查单位含量
        if total is not None and area is not None and area > 0:
            calculated_unit = total / area
            if unit is not None and unit > 0:
                diff_ratio = abs(calculated_unit - unit) / unit
                if diff_ratio > self.TOLERANCE_RATIO:
                    msg = f"{total_field} / {area_field} 计算的单位含量与填写的 {unit_field} 不符"
                    warnings.append(
                        ValidationWarning(
                            field=unit_field,
                            message=msg,
                            severity="warning",
                            value=unit,
                            expected=f"≈ {calculated_unit:.6f}",
                        )
                    )
                    logger.warning(
                        f"[IndicatorValidator] 单位含量不一致 | {unit_field}={unit} | calculated={calculated_unit} | diff={diff_ratio*100:.1f}%"
                    )

        # 如果有单位含量和面积，检查总量
        if unit is not None and area is not None and area > 0:
            calculated_total = unit * area
            if total is not None and total > 0:
                diff_ratio = abs(calculated_total - total) / total
                if diff_ratio > self.TOLERANCE_RATIO:
                    msg = f"{unit_field} × {area_field} 计算的总量与填写的 {total_field} 不符"
                    warnings.append(
                        ValidationWarning(
                            field=total_field,
                            message=msg,
                            severity="warning",
                            value=total,
                            expected=f"≈ {calculated_total:.2f}",
                        )
                    )

    def _validate_unit_cost(
        self,
        data: Dict[str, Any],
        cost_field: str,
        area_field: str,
        unit_cost_field: str,
        errors: List[ValidationWarning],
        warnings: List[ValidationWarning],
    ) -> None:
        """
        验证单位造价的一致性

        Args:
            data: 数据字典
            cost_field: 总造价字段名
            area_field: 面积字段名
            unit_cost_field: 平米造价字段名
            errors: 错误列表
            warnings: 警告列表
        """
        cost = data.get(cost_field)
        area = data.get(area_field)
        unit_cost = data.get(unit_cost_field)

        # 如果同时有总造价和面积，检查平米造价
        if cost is not None and area is not None and area > 0:
            calculated_unit = cost / area
            if unit_cost is not None and unit_cost > 0:
                diff_ratio = abs(calculated_unit - unit_cost) / unit_cost
                if diff_ratio > self.TOLERANCE_RATIO:
                    msg = f"{cost_field} / {area_field} 计算的平米造价与填写的 {unit_cost_field} 不符"
                    warnings.append(
                        ValidationWarning(
                            field=unit_cost_field,
                            message=msg,
                            severity="warning",
                            value=unit_cost,
                            expected=f"≈ {calculated_unit:.2f}",
                        )
                    )
                    logger.warning(
                        f"[IndicatorValidator] 单位造价不一致 | {unit_cost_field}={unit_cost} | calculated={calculated_unit} | diff={diff_ratio*100:.1f}%"
                    )

    def _check_value_in_range(
        self,
        field_name: str,
        value: float,
        range_info: Dict[str, float],
        field_desc: str,
        unit: str,
        warnings: List[ValidationWarning],
    ) -> None:
        """
        检查值是否在参考范围内

        Args:
            field_name: 字段名
            value: 当前值
            range_info: 范围信息 {"min": x, "max": y, "typical": z}
            field_desc: 字段描述
            unit: 单位
            warnings: 警告列表
        """
        min_val = range_info["min"]
        max_val = range_info["max"]
        typical = range_info["typical"]

        if value < min_val:
            warnings.append(
                ValidationWarning(
                    field=field_name,
                    message=f"{field_desc}低于参考范围下限",
                    severity="warning",
                    value=value,
                    expected=f"{min_val}-{max_val} {unit} (典型值: {typical} {unit})",
                )
            )
            logger.info(f"[IndicatorValidator] 值低于参考范围 | field={field_name} | value={value} | min={min_val}")
        elif value > max_val:
            warnings.append(
                ValidationWarning(
                    field=field_name,
                    message=f"{field_desc}高于参考范围上限",
                    severity="warning",
                    value=value,
                    expected=f"{min_val}-{max_val} {unit} (典型值: {typical} {unit})",
                )
            )
            logger.info(f"[IndicatorValidator] 值高于参考范围 | field={field_name} | value={value} | max={max_val}")

    def _check_reference_field(
        self,
        data: Dict[str, Any],
        field_name: str,
        range_data: Dict[str, Dict[str, float]],
        category: str,
        field_desc: str,
        warnings: List[ValidationWarning],
    ) -> None:
        """
        检查字段是否在参考范围内

        Args:
            data: 数据字典
            field_name: 字段名
            range_data: 参考范围数据
            category: 业态类别
            field_desc: 字段描述
            warnings: 警告列表
        """
        value = data.get(field_name)
        if value is not None and value >= 0:
            range_info = range_data.get(category, range_data.get("住宅", {}))
            if range_info:
                self._check_value_in_range(field_name, value, range_info, field_desc, "", warnings)


def validate_indicator_data(data: Dict[str, Any], strict_mode: bool = False) -> ValidationResult:
    """
    便捷函数：验证指标库数据

    Args:
        data: 待验证的数据字典
        strict_mode: 严格模式

    Returns:
        ValidationResult: 验证结果
    """
    logger.info(f"[validate_indicator_data] 验证指标数据 | name={data.get('name', 'N/A')}")
    validator = IndicatorValidator(strict_mode=strict_mode)
    return validator.validate(data)


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 测试数据
    test_data = {
        "name": "测试住宅项目",
        "category": "住宅",
        "location": "山东烟台",
        "structure": "框架结构",
        "start_date": "2023-01",
        "end_date": "2024-06",
        "floor_above": 12,
        "floor_below": 2,
        "area_total": 25000.0,
        "area_above": 20000.0,
        "area_below": 5000.0,
        "unit_cost": 2350.0,
        "total_cost": 58750000.0,
        "above_rebar": 1000.0,  # 地上钢筋 1000t
        "above_rebar_unit": 0.05,  # 地上钢筋含量 0.05t/㎡
        "underground_rebar": 700.0,  # 地下钢筋 700t
        "underground_rebar_unit": 0.14,  # 地下钢筋含量 0.14t/㎡
    }

    # 执行验证
    result = validate_indicator_data(test_data)

    print("\n" + "=" * 60)
    print("验证结果:")
    print(f"  通过: {result.passed}")
    print(f"  检查项:")
    for check, status in result.checks.items():
        print(f"    - {check}: {status}")
    print(f"  错误数: {len(result.errors)}")
    print(f"  警告数: {len(result.warnings)}")

    if result.errors:
        print("\n错误:")
        for error in result.errors:
            print(f"  - [{error.field}] {error.message}")

    if result.warnings:
        print("\n警告:")
        for warning in result.warnings:
            print(f"  - [{warning.field}] {warning.message}")

    # 测试异常数据
    print("\n" + "=" * 60)
    print("测试异常数据:")

    bad_data = {
        "name": "",  # 空名称
        "category": "住宅",
        "location": "山东烟台",
        "structure": "框架结构",
        "start_date": "2024-06",  # 开工晚于竣工
        "end_date": "2023-01",
        "area_total": 50.0,  # 过小
        "unit_cost": 2350.0,
        "total_cost": 117500.0,  # 与计算不符
    }

    result2 = validate_indicator_data(bad_data, strict_mode=True)

    print(f"  通过: {result2.passed}")
    print(f"  错误数: {len(result2.errors)}")
    print(f"  警告数: {len(result2.warnings)}")

    if result2.errors:
        print("\n错误:")
        for error in result2.errors:
            print(f"  - [{error.field}] {error.message}")

    if result2.warnings:
        print("\n警告:")
        for warning in result2.warnings:
            print(f"  - [{warning.field}] {warning.message}")