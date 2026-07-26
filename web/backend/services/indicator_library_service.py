"""
指标库业务服务层
整合 LocalIndicatorService、ExcelParserService 和 IndicatorValidator
提供完整的指标库 CRUD、验证和导入功能
"""

import logging
import tempfile
import os
import sys
from typing import Optional, List, Dict, Any, Union, Tuple

# 兼容直接运行和包导入
if __name__.startswith('services.'):
    from models.indicator_library import (
        IndicatorLibrarySummary,
        IndicatorLibraryDetail,
        IndicatorLibraryCreate,
        ValidationResult,
        ImportResult,
        ImportPreviewResult,
        ImportPreviewItem,
        ImportFieldError,
    )
else:
    from ..models.indicator_library import (
        IndicatorLibrarySummary,
        IndicatorLibraryDetail,
        IndicatorLibraryCreate,
        ValidationResult,
        ImportResult,
        ImportPreviewResult,
        ImportPreviewItem,
        ImportFieldError,
    )

from services.local_indicator_service import LocalIndicatorService
from services.excel_parser_service import ExcelParserService
from services.indicator_validator import IndicatorValidator

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

    def get_full_projects(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        获取全字段项目列表（用于数据导出）。

        直接透传存储层 SELECT * 结果，不做 Summary 裁剪，保留所有 db 字段，
        供导出端点按 DETAIL_HEADERS 映射回填，保证导出→导入闭环。
        """
        logger.info(
            f"[IndicatorLibraryService] 获取全字段列表 | category={category} | location={location} | limit={limit}"
        )
        try:
            projects = self._storage_service.get_indicator_projects(
                limit=limit,
                category=category,
                location=location,
            )
            logger.info(f"[IndicatorLibraryService] 全字段列表查询完成 | count={len(projects)}")
            return projects
        except Exception as e:
            logger.error(
                f"[IndicatorLibraryService] 获取全字段列表失败 | error={e}", exc_info=True
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
        self, data: Union[Dict[str, Any], IndicatorLibraryCreate], account: Optional[str] = None
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

            # 上传留痕
            project_data["uploaded_by"] = account

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

            # 反向映射：前端展示字段名 → 数据库存储字段名（与 _to_detail 正向映射对应）
            self._apply_reverse_mapping(update_data)

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

    def _apply_reverse_mapping(self, data: Dict[str, Any]) -> None:
        """
        将前端展示字段名反向映射为数据库存储字段名（update 专用）。

        与 _to_detail 的正向映射严格对应：
        - 钢筋：前端 kg/㎡ ↔ 数据库 t/㎡（÷1000）
        - 混凝土/模板/砌体：单位一致，仅改名
        - 专项费用简化名：pile/foundation_support/curtain_wall/decoration → cost_xxx

        就地修改 data；CostSection/BasicInfoSection 编辑的字段（above_structure/roof/
        unit_cost 等）本身就是数据库名，无需处理。
        """
        logger.debug(f"[IndicatorLibraryService] 反向映射前 | keys={list(data.keys())}")
        # 砌体
        if "block_total" in data:
            data["block"] = data.pop("block_total")
        # 钢筋：前端 kg/㎡ → 数据库 t/㎡
        for front_field, db_field in (
            ("rebar_above", "above_rebar_unit"),
            ("rebar_below", "underground_rebar_unit"),
        ):
            if front_field in data:
                val = data.pop(front_field)
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    data[db_field] = round(val / 1000, 6)
                else:
                    data[db_field] = val
        # 混凝土/模板（单位一致，仅改名）
        for front_field, db_field in (
            ("concrete_above", "above_concrete_unit"),
            ("concrete_below", "underground_concrete_unit"),
            ("formwork_above", "above_formwork_unit"),
            ("formwork_below", "underground_formwork_unit"),
        ):
            if front_field in data:
                data[db_field] = data.pop(front_field)
        # 专项费用简化名
        for front_field, db_field in (
            ("pile", "cost_pile"),
            ("foundation_support", "cost_foundation_support"),
            ("curtain_wall", "cost_curtain_wall"),
            ("decoration", "cost_decoration"),
        ):
            if front_field in data:
                data[db_field] = data.pop(front_field)
        logger.debug(f"[IndicatorLibraryService] 反向映射后 | keys={list(data.keys())}")

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
                    row_index = project.get("_row_index")

                    # 验证数据
                    validation_result = self._validator.validate(project)

                    status = "valid"
                    warnings_list: List[str] = []
                    errors_list: List[str] = []
                    warning_details: List[ImportFieldError] = []
                    error_details: List[ImportFieldError] = []

                    if validation_result.errors:
                        status = "error"
                        error_count += 1
                        errors_list = [e.message for e in validation_result.errors]
                        error_details = [
                            self._to_error_detail(row_index, e) for e in validation_result.errors
                        ]
                    elif validation_result.warnings:
                        status = "warning"
                        warning_count += 1
                        warnings_list = [w.message for w in validation_result.warnings]
                        warning_details = [
                            self._to_error_detail(row_index, w) for w in validation_result.warnings
                        ]
                    else:
                        valid_count += 1

                    item = ImportPreviewItem(
                        index=idx + 1,
                        name=str(project.get("name", f"项目{idx + 1}")).strip(),
                        category=project.get("category"),
                        location=project.get("location"),
                        unit_cost=project.get("unit_cost"),
                        row=row_index,
                        status=status,
                        warnings=warnings_list,
                        errors=errors_list,
                        warning_details=warning_details,
                        error_details=error_details,
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
        self, file_content: bytes, filename: str, account: Optional[str] = None
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
                error_details: List[ImportFieldError] = []

                for idx, project in enumerate(projects):
                    row_index = project.get("_row_index")
                    display_row = row_index if row_index else idx + 1
                    name = project.get("name", "未知")
                    logger.info(f"[IndicatorLibraryService] 处理第{idx+1}条 | row={display_row} | name={name}")
                    try:
                        # 添加元数据
                        project["source"] = "Excel导入"
                        project["source_file"] = source_file
                        project["uploaded_by"] = account
                        if entry_date:
                            project["entry_date"] = entry_date

                        # 验证数据
                        validation_result = self._validator.validate(project)
                        logger.info(f"[IndicatorLibraryService] 验证完成 | passed={validation_result.passed} | errors={len(validation_result.errors)} | warnings={len(validation_result.warnings)}")
                        if validation_result.errors:
                            for e in validation_result.errors:
                                logger.warning(f"  错误: {e.field} - {e.message}")

                        # 记录警告但仍然导入
                        if validation_result.warnings:
                            warnings_list.append({
                                "row": display_row,
                                "name": name,
                                "warnings": [w.message for w in validation_result.warnings],
                            })

                        # 验证失败则跳过
                        if not validation_result.passed:
                            errors_list.append(
                                f"第{display_row}行 ({name}): "
                                f"{', '.join([e.message for e in validation_result.errors])}"
                            )
                            for e in validation_result.errors:
                                error_details.append(self._to_error_detail(row_index, e))
                            logger.warning(f"[IndicatorLibraryService] 跳过第{display_row}行（验证失败）")
                            continue

                        # 创建项目
                        logger.info(f"[IndicatorLibraryService] 开始创建项目 | name={name}")
                        result = self._storage_service.create_indicator_project(project)
                        logger.info(f"[IndicatorLibraryService] 创建结果 | result={'成功 id='+str(result.get('id')) if result else '失败(None)'}")
                        if result:
                            imported += 1
                        else:
                            errors_list.append(
                                f"第{display_row}行 ({name}): 创建失败"
                            )
                            error_details.append(ImportFieldError(
                                row=row_index,
                                field="name",
                                field_label=ExcelParserService.get_field_label("name"),
                                value=name,
                                message="入库失败：创建项目失败（数据库未写入）",
                                suggestion=self._make_db_suggestion(None, None, "创建失败"),
                            ))

                    except Exception as e:
                        errors_list.append(
                            f"第{display_row}行 ({name}): {str(e)}"
                        )
                        error_details.append(ImportFieldError(
                            row=row_index,
                            message=f"处理异常：{type(e).__name__}: {str(e)}",
                            suggestion="请核对数据后重试；若反复失败请联系管理员查看后端日志",
                        ))
                        logger.error(
                            f"[IndicatorLibraryService] 导入单条失败 | row={display_row} | error={e}", exc_info=True
                        )

                result = ImportResult(
                    success=imported > 0,
                    imported=imported,
                    total=len(projects),
                    warnings=warnings_list,
                    errors=errors_list,
                    error_details=error_details,
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

    # ==================== 自动导入（先校验后入库） ====================

    def auto_import(self, file_content: bytes, filename: str, account: Optional[str] = None) -> ImportResult:
        """
        自动导入 Excel 数据（先预览校验，有错误返回，无错误直接入库）

        流程：解析Excel → 逐行校验 → 有错返回错误列表 → 无错直接入库

        Args:
            file_content: Excel 文件内容
            filename: 文件名

        Returns:
            ImportResult 导入结果
        """
        logger.info(f"[IndicatorLibraryService] 自动导入 | filename={filename}")

        try:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
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

                # 校验所有数据
                valid_projects = []
                errors_list = []        # [{row,name,errors:[msg]}] 兼容旧文本展示
                warnings_list = []
                error_details: List[ImportFieldError] = []  # 结构化错误（带行列定位）

                for idx, project in enumerate(projects):
                    # 添加元数据
                    project["source"] = "Excel导入"
                    project["source_file"] = filename
                    project["uploaded_by"] = account
                    row_index = project.get("_row_index")
                    display_row = row_index if row_index else idx + 1
                    name = project.get("name", f"项目{idx + 1}")

                    # 验证数据
                    validation_result = self._validator.validate(project)

                    if validation_result.errors:
                        # 有错误，记录并跳过
                        errors_list.append({
                            "row": display_row,
                            "name": name,
                            "errors": [e.message for e in validation_result.errors]
                        })
                        for e in validation_result.errors:
                            error_details.append(self._to_error_detail(row_index, e))
                    else:
                        # 验证通过（可能有警告但仍可导入）
                        if validation_result.warnings:
                            warnings_list.append({
                                "row": display_row,
                                "name": name,
                                "warnings": [w.message for w in validation_result.warnings]
                            })
                        valid_projects.append(project)

                # 如果有校验错误，返回错误列表让用户处理
                if errors_list:
                    logger.info(f"[IndicatorLibraryService] 校验有误 | error_count={len(errors_list)}, valid_count={len(valid_projects)}")
                    return ImportResult(
                        success=False,
                        imported=0,
                        total=len(projects),
                        warnings=warnings_list,
                        errors=[f"第{e['row']}行 ({e['name']}): {', '.join(e['errors'])}" for e in errors_list],
                        error_details=error_details,
                    )

                # 无校验错误，直接入库
                imported = 0
                imported_details = []
                import_errors: List[ImportFieldError] = []  # 入库阶段失败（不再静默丢弃）

                for project in valid_projects:
                    row_index = project.get("_row_index")
                    insert_result = self._storage_service.auto_import_project(project, filename)
                    if insert_result.get('success'):
                        imported += 1
                        imported_details.append({
                            "id": insert_result.get('id'),
                            "name": project.get('name'),
                            "version": insert_result.get('version'),
                            "is_update": insert_result.get('is_update', False)
                        })
                    else:
                        # 入库失败：解析为结构化错误（避免静默丢弃）
                        err_msg = insert_result.get('error', '入库失败')
                        field, label = self._parse_db_error(err_msg)
                        import_errors.append(ImportFieldError(
                            row=row_index,
                            field=field,
                            field_label=label or field or "（未知列）",
                            value=project.get(field) if field else None,
                            message=f"入库失败：{err_msg}",
                            suggestion=self._make_db_suggestion(field, label, err_msg),
                        ))
                        logger.warning(
                            f"[IndicatorLibraryService] 入库失败 | row={row_index} | name={project.get('name')} | error={err_msg}"
                        )

                # 记录导入历史（fail_count 修正为实际入库失败数）
                self._storage_service.record_import_history(
                    filename=filename,
                    total_count=len(projects),
                    success_count=imported,
                    fail_count=len(import_errors),
                    details=imported_details
                )

                # 合并入库阶段错误
                error_details.extend(import_errors)

                result = ImportResult(
                    success=imported > 0,
                    imported=imported,
                    total=len(projects),
                    warnings=[f"第{w['row']}行: {', '.join(w['warnings'])}" for w in warnings_list] if warnings_list else [],
                    errors=[f"第{e.row}行: {e.message}" for e in import_errors],
                    error_details=error_details,
                )

                logger.info(f"[IndicatorLibraryService] 自动导入完成 | imported={imported}")
                return result

            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"[IndicatorLibraryService] 自动导入失败 | error={e}", exc_info=True)
            raise ValueError(f"自动导入失败: {str(e)}")

    # ==================== 导入历史 ====================

    def get_import_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取导入历史列表

        Args:
            limit: 返回数量限制

        Returns:
            导入历史列表
        """
        logger.info(f"[IndicatorLibraryService] 获取导入历史 | limit={limit}")
        return self._storage_service.get_import_history(limit)

    def get_import_detail(self, import_id: int) -> Optional[Dict[str, Any]]:
        """
        获取导入详情

        Args:
            import_id: 导入记录ID

        Returns:
            导入详情或 None
        """
        logger.info(f"[IndicatorLibraryService] 获取导入详情 | import_id={import_id}")
        return self._storage_service.get_import_detail(import_id)

    # ==================== 版本历史 ====================

    def get_version_history(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目版本历史

        Args:
            project_id: 项目ID

        Returns:
            版本历史列表
        """
        logger.info(f"[IndicatorLibraryService] 获取版本历史 | project_id={project_id}")
        return self._storage_service.get_version_history(project_id)

    def get_snapshot_detail(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        获取快照详情

        Args:
            snapshot_id: 快照ID

        Returns:
            快照数据或 None
        """
        logger.info(f"[IndicatorLibraryService] 获取快照详情 | snapshot_id={snapshot_id}")
        return self._storage_service.get_snapshot_detail(snapshot_id)

    def rollback_version(self, snapshot_id: str) -> bool:
        """
        回滚到指定快照

        Args:
            snapshot_id: 快照ID

        Returns:
            是否回滚成功
        """
        logger.info(f"[IndicatorLibraryService] 回滚版本 | snapshot_id={snapshot_id}")
        return self._storage_service.rollback_to_snapshot(snapshot_id)

    # ==================== 数据一致性校验 ====================

    def sync_check(self) -> Dict[str, Any]:
        """
        前后端数据一致性校验

        Returns:
            校验结果
        """
        logger.info("[IndicatorLibraryService] 执行数据一致性校验")
        return self._storage_service.sync_check()

    # ==================== 错误定位与修改建议 ====================

    def _to_error_detail(
        self, row_index: Optional[int], vw
    ) -> ImportFieldError:
        """将 validator 的 ValidationWarning 转为带行列定位的 ImportFieldError"""
        field = vw.field
        return ImportFieldError(
            row=row_index,
            field=field,
            field_label=ExcelParserService.get_field_label(field) or field,
            value=vw.value,
            message=vw.message,
            suggestion=self._make_suggestion(field, vw),
        )

    def _make_suggestion(self, field: Optional[str], vw) -> Optional[str]:
        """根据字段与错误信息生成中文修改建议"""
        label = ExcelParserService.get_field_label(field) or field or "该字段"
        msg = vw.message or ""
        expected = vw.expected

        # 必填为空
        if field in IndicatorValidator.REQUIRED_FIELDS and (
            vw.value is None or (isinstance(vw.value, str) and not vw.value.strip())
        ):
            return f'请填写“{label}”（必填项，不能为空）'
        # 数值类型错误（"25000元" 这类）
        if "纯数字" in msg:
            return f'请在“{label}”列只填数字，去掉单位/文字/逗号（如 25000）'
        # 日期格式
        if "日期格式" in msg or "YYYY-MM" in msg:
            return "请改为 YYYY-MM 格式，例如 2024-01"
        if "不能早于" in msg:
            return f'请将“{label}”改为晚于开工时间'
        # 范围/逻辑一致性，复用 validator 的 expected
        if expected:
            return f"建议改为：{expected}"
        return f'请检查“{label}”列的取值'

    def _parse_db_error(self, err_msg: str) -> Tuple[Optional[str], Optional[str]]:
        """从数据库异常文本提取字段名与中文列名

        如 'NOT NULL constraint failed: indicator_projects.name' -> ('name', '项目名称')
        """
        import re
        m = re.search(r"NOT NULL constraint failed: \w+\.(\w+)", err_msg)
        if m:
            field = m.group(1)
            return field, ExcelParserService.get_field_label(field) or field
        return None, None

    def _make_db_suggestion(
        self, field: Optional[str], label: Optional[str], err_msg: str
    ) -> str:
        """入库失败时的修改建议"""
        if field:
            return f'请补填“{label}”后再导入（数据库要求该字段非空）'
        return "请核对数据完整性后重试；若反复失败请联系管理员查看后端日志"

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
            "unit_structure", "unit_installation", "unit_decoration", "unit_measure", "above_cost_ratio", "below_cost_ratio",
            "cost_above_structure", "cost_above_installation",
            "unit_cost_above_structure", "unit_cost_above_installation",
            "cost_underground_structure", "cost_underground_installation",
            "unit_cost_underground_structure", "unit_cost_underground_installation",
            "cost_measures", "unit_cost_measures",
            "cost_outdoor", "unit_cost_outdoor",
            # 经济指标（直接费平米造价）
            "above_structure", "underground_structure",
            "roof", "exterior_wall", "interior_wall", "floor",
            "electrical", "plumbing", "hvac", "elevator", "fire", "measures",
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

        # 专项费用字段映射：数据库名 → 前端期望简化名
        detail_data["pile"] = project.get("cost_pile")
        detail_data["foundation_support"] = project.get("cost_foundation_support")
        detail_data["curtain_wall"] = project.get("cost_curtain_wall")
        detail_data["decoration"] = project.get("cost_decoration")
        # landscape/intelligent/gas/solar 数据库暂无，跳过或填0

        # 材料含量
        # 前端期望字段名: rebar_above(concrete_above...) + 单位换算: t→kg (×1000)
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

        # 字段映射：存储层 → 前端期望（字段名 + 单位换算）
        # 钢筋：数据库存 t，前端期望 kg/㎡ (above_rebar_unit × 1000 = rebar_above)
        rebar_above = project.get("above_rebar_unit")
        if rebar_above is not None and rebar_above > 0:
            detail_data["rebar_above"] = round(rebar_above * 1000, 3)
        rebar_below = project.get("underground_rebar_unit")
        if rebar_below is not None and rebar_below > 0:
            detail_data["rebar_below"] = round(rebar_below * 1000, 3)
        # 混凝土：数据库存 m³/㎡，前端直接用
        detail_data["concrete_above"] = project.get("above_concrete_unit")
        detail_data["concrete_below"] = project.get("underground_concrete_unit")
        # 模板：数据库存 m²/㎡，前端直接用
        detail_data["formwork_above"] = project.get("above_formwork_unit")
        detail_data["formwork_below"] = project.get("underground_formwork_unit")
        # 砌体
        detail_data["block_total"] = project.get("block")
        # 电缆/管道/风管
        detail_data["cable"] = project.get("cable")
        detail_data["pipe"] = project.get("pipe")
        detail_data["duct"] = project.get("duct")

        # 建筑指标字段
        detail_data["wall_floor_ratio"] = project.get("wall_floor_ratio")
        detail_data["window_wall_ratio"] = project.get("window_wall_ratio")
        detail_data["window_content"] = project.get("window_content")
        detail_data["door_content"] = project.get("door_content")
        detail_data["interior_wall_content"] = project.get("interior_wall_content")
        detail_data["balcony_ratio"] = project.get("balcony_ratio")
        detail_data["assembly_rate"] = project.get("assembly_rate")
        detail_data["assembly_content"] = project.get("assembly_content")

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