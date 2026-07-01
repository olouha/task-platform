"""
指标库业务服务层
整合 LocalIndicatorService、ExcelParserService 和 IndicatorValidator
提供完整的指标库 CRUD、验证和导入功能
"""

import logging
import tempfile
import os
from typing import Optional, List, Dict, Any, Union

from ..models.indicator_library import (
    IndicatorLibrarySummary,
    IndicatorLibraryDetail,
    IndicatorLibraryCreate,
    ValidationResult,
    ImportResult,
    ImportPreviewResult,
    ImportPreviewItem,
)
from .local_indicator_service import LocalIndicatorService
from .excel_parser_service import ExcelParserService
from .indicator_validator import IndicatorValidator

logger = logging.getLogger(__name__)


class IndicatorLibraryService:
    """
    指标库业务服务

    整合存储、解析、验证服务，提供统一的业务接口
    """

    def __init__(
        self,
        storage_service: Optional[LocalIndicatorService] = None,
        validator: Optional[IndicatorValidator] = None,
    ):
        """
        初始化指标库业务服务

        Args:
            storage_service: 存储服务实例，默认创建 LocalIndicatorService
            validator: 验证器实例，默认创建 IndicatorValidator
        """
        self._storage_service = storage_service or LocalIndicatorService()
        self._validator = validator or IndicatorValidator()
        logger.info("[IndicatorLibraryService] 初始化完成")

    def get_summary_list(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 100,
    ) -> List[IndicatorLibrarySummary]:
        """
        获取指标库汇总列表

        Args:
            category: 业态筛选（可选）
            location: 所在地筛选（可选）
            limit: 返回数量限制，默认100

        Returns:
            IndicatorLibrarySummary 列表
        """
        logger.info(
            f"[IndicatorLibraryService] 获取汇总列表 | category={category} | location={location} | limit={limit}"
        )

        try:
            projects = self._storage_service.get_indicator_projects(
                limit=limit,
                category=category,
                location=location,
            )

            result = []
            for p in projects:
                summary = self._to_summary(p)
                result.append(summary)

            logger.info(f"[IndicatorLibraryService] 汇总列表查询完成 | count={len(result)}")
            return result

        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 获取汇总列表失败 | error={e}", exc_info=True
            )
            raise

    def get_detail(self, project_id: str) -> Optional[IndicatorLibraryDetail]:
        """
        获取指标库项目详情

        Args:
            project_id: 项目ID

        Returns:
            IndicatorLibraryDetail 或 None（不存在时）
        """
        logger.info(f"[IndicatorLibraryService] 获取详情 | project_id={project_id}")

        try:
            project = self._storage_service.get_indicator_project(project_id)

            if not project:
                logger.warning(f"[IndicatorLibraryService] 项目不存在 | project_id={project_id}")
                return None

            detail = self._to_detail(project)
            logger.info(f"[IndicatorLibraryService] 详情获取成功 | project_id={project_id}")
            return detail

        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 获取详情失败 | project_id={project_id} | error={e}",
                exc_info=True,
            )
            raise

    def create_project(
        self, data: Union[Dict[str, Any], IndicatorLibraryCreate]
    ) -> IndicatorLibraryDetail:
        """
        创建指标库项目

        Args:
            data: 项目数据

        Returns:
            创建的 IndicatorLibraryDetail

        Raises:
            ValueError: 验证失败时抛出
        """
        logger.info(f"[IndicatorLibraryService] 创建项目 | name={data.get('name', 'N/A')}")

        try:
            # 转换为字典
            if hasattr(data, "model_dump"):
                project_data = data.model_dump()
            else:
                project_data = dict(data)

            # 验证数据
            validation_result = self._validator.validate(project_data)
            if not validation_result.passed:
                errors = [e.message for e in validation_result.errors]
                logger.warning(f"[IndicatorLibraryService] 验证失败 | errors={errors}")
                raise ValueError(f"数据验证失败: {', '.join(errors)}")

            # 记录警告但不阻止创建
            if validation_result.warnings:
                warnings = [w.message for w in validation_result.warnings]
                logger.info(f"[IndicatorLibraryService] 验证警告 | warnings={warnings}")

            # 创建项目
            result = self._storage_service.create_indicator_project(project_data)

            if not result:
                raise ValueError("创建项目失败")

            detail = self._to_detail(result)
            logger.info(f"[IndicatorLibraryService] 创建成功 | id={detail.id}")
            return detail

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 创建项目失败 | error={e}", exc_info=True
            )
            raise ValueError(f"创建项目失败: {str(e)}")

    def update_project(
        self,
        project_id: str,
        data: Union[Dict[str, Any], IndicatorLibraryCreate],
    ) -> IndicatorLibraryDetail:
        """
        更新指标库项目

        Args:
            project_id: 项目ID
            data: 更新数据

        Returns:
            更新后的 IndicatorLibraryDetail

        Raises:
            ValueError: 验证失败或项目不存在时抛出
        """
        logger.info(f"[IndicatorLibraryService] 更新项目 | project_id={project_id}")

        try:
            # 检查项目是否存在
            existing = self._storage_service.get_indicator_project(project_id)
            if not existing:
                logger.warning(f"[IndicatorLibraryService] 项目不存在 | project_id={project_id}")
                raise ValueError(f"项目不存在: {project_id}")

            # 转换为字典
            if hasattr(data, "model_dump"):
                update_data = data.model_dump()
            else:
                update_data = dict(data)

            # 合并现有数据和更新数据
            merged_data = {**existing, **update_data}

            # 验证合并后的数据
            validation_result = self._validator.validate(merged_data)
            if not validation_result.passed:
                errors = [e.message for e in validation_result.errors]
                logger.warning(f"[IndicatorLibraryService] 验证失败 | errors={errors}")
                raise ValueError(f"数据验证失败: {', '.join(errors)}")

            # 更新项目
            success = self._storage_service.update_indicator_project(project_id, update_data)

            if not success:
                raise ValueError("更新项目失败")

            # 获取更新后的数据
            result = self._storage_service.get_indicator_project(project_id)
            detail = self._to_detail(result)
            logger.info(f"[IndicatorLibraryService] 更新成功 | project_id={project_id}")
            return detail

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 更新项目失败 | project_id={project_id} | error={e}",
                exc_info=True,
            )
            raise ValueError(f"更新项目失败: {str(e)}")

    def delete_project(self, project_id: str) -> bool:
        """
        删除指标库项目

        Args:
            project_id: 项目ID

        Returns:
            是否删除成功
        """
        logger.info(f"[IndicatorLibraryService] 删除项目 | project_id={project_id}")

        try:
            success = self._storage_service.delete_indicator_project(project_id)

            if success:
                logger.info(f"[IndicatorLibraryService] 删除成功 | project_id={project_id}")
            else:
                logger.warning(f"[IndicatorLibraryService] 项目不存在 | project_id={project_id}")

            return success

        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 删除项目失败 | project_id={project_id} | error={e}",
                exc_info=True,
            )
            return False

    def validate_data(
        self, data: Union[Dict[str, Any], IndicatorLibraryCreate]
    ) -> ValidationResult:
        """
        验证指标库数据

        Args:
            data: 待验证的数据

        Returns:
            ValidationResult 验证结果
        """
        logger.info(f"[IndicatorLibraryService] 验证数据 | name={data.get('name', 'N/A')}")

        try:
            # 转换为字典
            if hasattr(data, "model_dump"):
                data_dict = data.model_dump()
            else:
                data_dict = dict(data)

            result = self._validator.validate(data_dict)
            logger.info(
                f"[IndicatorLibraryService] 验证完成 | passed={result.passed} | errors={len(result.errors)} | warnings={len(result.warnings)}"
            )
            return result

        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 验证失败 | error={e}", exc_info=True
            )
            return ValidationResult(
                passed=False,
                warnings=[],
                errors=[],
                checks={"validation_error": str(e)},
            )

    def preview_import(
        self, file_content: bytes, filename: str
    ) -> ImportPreviewResult:
        """
        预览 Excel 导入内容（不实际导入）

        Args:
            file_content: Excel 文件内容（字节数据）
            filename: 文件名

        Returns:
            ImportPreviewResult 预览结果
        """
        logger.info(f"[IndicatorLibraryService] 预览导入 | filename={filename}")

        try:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(
                suffix=".xlsx", delete=False
            ) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            try:
                # 解析 Excel
                parser = ExcelParserService(tmp_path)
                parse_result = parser.parse()

                if not parse_result.get("success"):
                    raise ValueError(parse_result.get("error", "解析失败"))

                projects = parse_result.get("projects", [])
                logger.info(f"[IndicatorLibraryService] 解析完成 | count={len(projects)}")

                # 预览每条数据
                items: List[ImportPreviewItem] = []
                valid_count = 0
                warning_count = 0
                error_count = 0

                for idx, project in enumerate(projects):
                    # 验证数据
                    validation_result = self._validator.validate(project)

                    status = "valid"
                    warnings_list: List[str] = []
                    errors_list: List[str] = []

                    if validation_result.errors:
                        status = "error"
                        error_count += 1
                        errors_list = [e.message for e in validation_result.errors]
                    elif validation_result.warnings:
                        status = "warning"
                        warning_count += 1
                        warnings_list = [w.message for w in validation_result.warnings]
                    else:
                        valid_count += 1

                    item = ImportPreviewItem(
                        index=idx + 1,
                        name=project.get("name", f"项目{idx + 1}"),
                        category=project.get("category"),
                        location=project.get("location"),
                        unit_cost=project.get("unit_cost"),
                        status=status,
                        warnings=warnings_list,
                        errors=errors_list,
                    )
                    items.append(item)

                result = ImportPreviewResult(
                    total=len(projects),
                    valid_count=valid_count,
                    warning_count=warning_count,
                    error_count=error_count,
                    items=items,
                )

                logger.info(
                    f"[IndicatorLibraryService] 预览完成 | total={result.total} | valid={result.valid_count} | warning={result.warning_count} | error={result.error_count}"
                )
                return result

            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 预览导入失败 | error={e}", exc_info=True
            )
            raise ValueError(f"预览导入失败: {str(e)}")

    def import_from_excel(
        self, file_content: bytes, filename: str
    ) -> ImportResult:
        """
        从 Excel 文件导入指标库数据

        Args:
            file_content: Excel 文件内容（字节数据）
            filename: 文件名

        Returns:
            ImportResult 导入结果
        """
        logger.info(f"[IndicatorLibraryService] 开始导入 | filename={filename}")

        try:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(
                suffix=".xlsx", delete=False
            ) as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            try:
                # 解析 Excel
                parser = ExcelParserService(tmp_path)
                parse_result = parser.parse()

                if not parse_result.get("success"):
                    raise ValueError(parse_result.get("error", "解析失败"))

                projects = parse_result.get("projects", [])
                logger.info(f"[IndicatorLibraryService] 解析完成 | count={len(projects)}")

                # 添加来源信息
                source_file = parse_result.get("metadata", {}).get("source_file", filename)
                entry_date = parse_result.get("metadata", {}).get(
                    "entry_date"
                )

                imported = 0
                warnings_list: List[Dict[str, Any]] = []
                errors_list: List[str] = []

                for idx, project in enumerate(projects):
                    try:
                        # 添加元数据
                        project["source"] = "Excel导入"
                        project["source_file"] = source_file
                        if entry_date:
                            project["entry_date"] = entry_date

                        # 验证数据
                        validation_result = self._validator.validate(project)

                        # 记录警告但仍然导入
                        if validation_result.warnings:
                            warnings_list.append({
                                "row": idx + 1,
                                "name": project.get("name", f"项目{idx + 1}"),
                                "warnings": [w.message for w in validation_result.warnings],
                            })

                        # 验证失败则跳过
                        if not validation_result.passed:
                            errors_list.append(
                                f"第{idx + 1}行 ({project.get('name', '未知')}): "
                                f"{', '.join([e.message for e in validation_result.errors])}"
                            )
                            continue

                        # 创建项目
                        result = self._storage_service.create_indicator_project(project)
                        if result:
                            imported += 1
                        else:
                            errors_list.append(
                                f"第{idx + 1}行 ({project.get('name', '未知')}): 创建失败"
                            )

                    except Exception as e:
                        errors_list.append(
                            f"第{idx + 1}行 ({project.get('name', '未知')}): {str(e)}"
                        )
                        logger.warning(
                            f"[IndicatorLibraryService] 导入单条失败 | row={idx + 1} | error={e}"
                        )

                result = ImportResult(
                    success=imported > 0,
                    imported=imported,
                    total=len(projects),
                    warnings=warnings_list,
                    errors=errors_list,
                )

                logger.info(
                    f"[IndicatorLibraryService] 导入完成 | imported={imported} | total={len(projects)} | errors={len(errors_list)}"
                )
                return result

            finally:
                # 清理临时文件
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 导入失败 | error={e}", exc_info=True
            )
            raise ValueError(f"导入失败: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """
        获取指标库统计信息

        Returns:
            统计信息字典
        """
        logger.info("[IndicatorLibraryService] 获取统计信息")

        try:
            stats = self._storage_service.get_stats()
            logger.info(f"[IndicatorLibraryService] 统计完成 | total={stats.get('total', 0)}")
            return stats

        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 获取统计失败 | error={e}", exc_info=True
            )
            return {
                "total": 0,
                "by_category": {},
                "by_location": {},
                "error": str(e),
            }

    # ==================== 私有辅助方法 ====================

    def _to_summary(self, project: Dict[str, Any]) -> IndicatorLibrarySummary:
        """
        将数据库记录转换为 Summary 模型

        Args:
            project: 数据库记录

        Returns:
            IndicatorLibrarySummary
        """
        return IndicatorLibrarySummary(
            id=project.get("id", ""),
            name=project.get("name", ""),
            category=project.get("category", ""),
            location=project.get("location", ""),
            structure=project.get("structure", ""),
            start_date=project.get("start_date"),
            end_date=project.get("end_date"),
            area_total=project.get("area_total"),
            unit_cost=project.get("unit_cost"),
            entry_date=project.get("entry_date"),
            updated_at=project.get("updated_at", ""),
        )

    def _to_detail(self, project: Dict[str, Any]) -> IndicatorLibraryDetail:
        """
        将数据库记录转换为 Detail 模型

        Args:
            project: 数据库记录

        Returns:
            IndicatorLibraryDetail
        """
        # 提取所有字段
        detail_data = {}

        # 基本信息
        basic_fields = [
            "id", "name", "category", "location", "structure",
            "delivery_type", "foundation_type",
            "start_date", "end_date",
            "floor_above", "floor_below", "height",
            "area_total", "area_above", "area_below",
        ]
        for field in basic_fields:
            if field in project:
                detail_data[field] = project[field]

        # 造价指标
        cost_fields = [
            "unit_cost", "total_cost",
            "unit_structure", "unit_installation",
            "cost_above_structure", "cost_above_installation",
            "unit_cost_above_structure", "unit_cost_above_installation",
            "cost_underground_structure", "cost_underground_installation",
            "unit_cost_underground_structure", "unit_cost_underground_installation",
            "cost_measures", "unit_cost_measures",
            "cost_outdoor", "unit_cost_outdoor",
        ]
        for field in cost_fields:
            if field in project:
                detail_data[field] = project[field]

        # 专项工程
        special_fields = [
            "cost_pile", "unit_cost_pile",
            "cost_foundation_support", "unit_cost_foundation_support",
            "cost_curtain_wall", "unit_cost_curtain_wall",
            "cost_decoration", "unit_cost_decoration",
            "cost_exterior_insulation", "unit_cost_exterior_insulation",
            "cost_exterior_windows", "unit_cost_exterior_windows",
            "cost_water_drainage", "unit_cost_water_drainage",
            "cost_heating", "unit_cost_heating",
            "cost_electrical", "unit_cost_electrical",
            "cost_hvac", "unit_cost_hvac",
        ]
        for field in special_fields:
            if field in project:
                detail_data[field] = project[field]

        # 材料含量
        material_fields = [
            "above_concrete", "above_concrete_unit",
            "above_rebar", "above_rebar_unit",
            "above_formwork", "above_formwork_unit",
            "underground_concrete", "underground_concrete_unit",
            "underground_rebar", "underground_rebar_unit",
            "underground_formwork", "underground_formwork_unit",
        ]
        for field in material_fields:
            if field in project:
                detail_data[field] = project[field]

        # 元数据
        meta_fields = [
            "source", "source_file", "remarks",
            "entry_date", "created_at", "updated_at",
        ]
        for field in meta_fields:
            if field in project:
                detail_data[field] = project[field]

        return IndicatorLibraryDetail(**detail_data)


# ==================== 全局服务实例 ====================

_indicator_library_service: Optional[IndicatorLibraryService] = None


def get_indicator_library_service() -> IndicatorLibraryService:
    """
    获取指标库业务服务全局实例

    Returns:
        IndicatorLibraryService 实例
    """
    global _indicator_library_service
    if _indicator_library_service is None:
        _indicator_library_service = IndicatorLibraryService()
    return _indicator_library_service


def reset_indicator_library_service() -> None:
    """重置全局服务实例（用于测试）"""
    global _indicator_library_service
    _indicator_library_service = None