"""
指标库 API
提供指标库项目管理、导入导出、验证等功能的 RESTful 接口
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import io
import os

from models.indicator_library import (
    IndicatorLibrarySummary,
    IndicatorLibraryDetail,
    IndicatorLibraryCreate,
    ValidationResult,
    ImportResult,
    ImportPreviewResult,
)
from services.indicator_library_service import IndicatorLibraryService, get_indicator_library_service

router = APIRouter()
logger = logging.getLogger(__name__)


def get_service() -> IndicatorLibraryService:
    """获取指标库业务服务实例"""
    return get_indicator_library_service()


# ==================== 汇总列表 ====================

@router.get("/summary", response_model=List[Dict[str, Any]])
async def get_summary_list(
    category: Optional[str] = Query(None, description="业态筛选"),
    location: Optional[str] = Query(None, description="所在地筛选"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    service: IndicatorLibraryService = Depends(get_service),
) -> List[Dict[str, Any]]:
    """
    获取指标库汇总列表

    - 支持按业态和所在地筛选
    - 返回简化的汇总信息
    """
    logger.info(f"[get_summary_list] 获取汇总列表 | category={category} | location={location} | limit={limit}")

    try:
        summaries = service.get_summary_list(
            category=category,
            location=location,
            limit=limit,
        )

        result = [s.model_dump() for s in summaries]
        logger.info(f"[get_summary_list] 返回 {len(result)} 条记录")
        return result

    except Exception as e:
        logger.error(f"[get_summary_list] 获取汇总列表失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取汇总列表失败: {str(e)}")


# ==================== 项目详情 ====================

@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project_detail(
    project_id: str,
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    获取指标库项目详情

    - 返回项目的完整信息
    - 包含所有造价、材料含量等详细字段
    """
    logger.info(f"[get_project_detail] 获取项目详情 | project_id={project_id}")

    try:
        detail = service.get_detail(project_id)

        if not detail:
            logger.warning(f"[get_project_detail] 项目不存在 | project_id={project_id}")
            raise HTTPException(status_code=404, detail=f"项目不存在: {project_id}")

        logger.info(f"[get_project_detail] 获取成功 | project_id={project_id}")
        return detail.model_dump(exclude_none=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_project_detail] 获取项目详情失败 | project_id={project_id} | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


# ==================== 创建项目 ====================

@router.post("/", response_model=Dict[str, Any], status_code=201)
async def create_project(
    data: IndicatorLibraryCreate,
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    创建指标库项目

    - 验证必填字段和数据格式
    - 自动记录创建时间
    """
    logger.info(f"[create_project] 创建项目 | name={data.name} | category={data.category}")

    try:
        detail = service.create_project(data)
        logger.info(f"[create_project] 创建成功 | id={detail.id}")
        return detail.model_dump(exclude_none=True)

    except ValueError as e:
        logger.warning(f"[create_project] 创建失败 | error={e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[create_project] 创建项目失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


# ==================== 更新项目 ====================

@router.put("/{project_id}", response_model=Dict[str, Any])
async def update_project(
    project_id: str,
    data: IndicatorLibraryCreate,
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    更新指标库项目

    - 验证数据格式
    - 自动记录更新时间
    """
    logger.info(f"[update_project] 更新项目 | project_id={project_id}")

    try:
        detail = service.update_project(project_id, data)
        logger.info(f"[update_project] 更新成功 | project_id={project_id}")
        return detail.model_dump(exclude_none=True)

    except ValueError as e:
        error_msg = str(e)
        if "不存在" in error_msg:
            logger.warning(f"[update_project] 项目不存在 | project_id={project_id}")
            raise HTTPException(status_code=404, detail=error_msg)
        logger.warning(f"[update_project] 更新失败 | error={e}")
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"[update_project] 更新项目失败 | project_id={project_id} | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


# ==================== 删除项目 ====================

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, bool]:
    """
    删除指标库项目

    - 返回删除是否成功
    """
    logger.info(f"[delete_project] 删除项目 | project_id={project_id}")

    try:
        success = service.delete_project(project_id)

        if success:
            logger.info(f"[delete_project] 删除成功 | project_id={project_id}")
        else:
            logger.warning(f"[delete_project] 项目不存在 | project_id={project_id}")

        return {"success": success}

    except Exception as e:
        logger.error(f"[delete_project] 删除项目失败 | project_id={project_id} | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


# ==================== 数据验证 ====================

@router.post("/validate", response_model=Dict[str, Any])
async def validate_data(
    data: IndicatorLibraryCreate,
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    验证指标库数据

    - 执行三层验证：基础验证、逻辑验证、参考范围验证
    - 返回验证结果，包括错误和警告信息
    """
    logger.info(f"[validate_data] 验证数据 | name={data.name}")

    try:
        result = service.validate_data(data)
        logger.info(
            f"[validate_data] 验证完成 | passed={result.passed} | errors={len(result.errors)} | warnings={len(result.warnings)}"
        )
        return result.model_dump()

    except Exception as e:
        logger.error(f"[validate_data] 验证失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


# ==================== 导入预览 ====================

@router.post("/preview", response_model=Dict[str, Any])
async def preview_import(
    file: UploadFile = File(..., description="Excel文件"),
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    预览 Excel 导入内容

    - 解析 Excel 文件但不实际导入数据库
    - 返回每条数据的验证结果
    """
    logger.info(f"[preview_import] 预览导入 | filename={file.filename}")

    try:
        # 验证文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

        # 读取文件内容
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")

        # 执行预览
        result = service.preview_import(content, file.filename)
        logger.info(
            f"[preview_import] 预览完成 | total={result.total} | valid={result.valid_count} | error={result.error_count}"
        )
        return result.model_dump()

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"[preview_import] 预览失败 | error={e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[preview_import] 预览导入失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览导入失败: {str(e)}")


# ==================== 导入Excel ====================

@router.post("/import", response_model=Dict[str, Any])
async def import_from_excel(
    file: UploadFile = File(..., description="Excel文件"),
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    从 Excel 文件导入指标库数据

    - 解析并验证 Excel 内容
    - 实际写入数据库
    - 返回导入结果统计
    """
    logger.info(f"[import_from_excel] 开始导入 | filename={file.filename}")

    try:
        # 验证文件类型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .xls 格式的 Excel 文件")

        # 读取文件内容
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="文件为空")

        # 执行导入
        result = service.import_from_excel(content, file.filename)
        logger.info(
            f"[import_from_excel] 导入完成 | imported={result.imported} | total={result.total} | errors={len(result.errors)}"
        )
        return result.model_dump()

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"[import_from_excel] 导入失败 | error={e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[import_from_excel] 导入失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


# ==================== 导出Excel ====================

@router.get("/export")
async def export_to_excel(
    category: Optional[str] = Query(None, description="业态筛选"),
    location: Optional[str] = Query(None, description="所在地筛选"),
    service: IndicatorLibraryService = Depends(get_service),
) -> StreamingResponse:
    """
    导出指标库数据到 Excel 文件

    - 支持按业态和所在地筛选
    - 返回 Excel 文件流
    """
    logger.info(f"[export_to_excel] 开始导出 | category={category} | location={location}")

    try:
        # 获取要导出的数据
        summaries = service.get_summary_list(
            category=category,
            location=location,
            limit=10000,  # 导出较多数据
        )

        # 生成 Excel 文件
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "指标库数据"

            # 定义样式
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            thin_border = Border(
                left=Side(style="thin"),
                right=Side(style="thin"),
                top=Side(style="thin"),
                bottom=Side(style="thin"),
            )

            # 表头
            headers = [
                "序号", "项目名称", "业态", "所在地", "结构形式",
                "开工时间", "竣工时间", "总建筑面积(㎡)", "平米造价(元/㎡)",
                "录入时间", "更新时间",
            ]

            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

            # 数据行
            for row_idx, summary in enumerate(summaries, 2):
                ws.cell(row=row_idx, column=1, value=row_idx - 1)
                ws.cell(row=row_idx, column=2, value=summary.name)
                ws.cell(row=row_idx, column=3, value=summary.category)
                ws.cell(row=row_idx, column=4, value=summary.location)
                ws.cell(row=row_idx, column=5, value=summary.structure)
                ws.cell(row=row_idx, column=6, value=summary.start_date or "")
                ws.cell(row=row_idx, column=7, value=summary.end_date or "")
                ws.cell(row=row_idx, column=8, value=summary.area_total)
                ws.cell(row=row_idx, column=9, value=summary.unit_cost)
                ws.cell(row=row_idx, column=10, value=summary.entry_date or "")
                ws.cell(row=row_idx, column=11, value=summary.updated_at)

                # 应用边框
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col).border = thin_border

            # 调整列宽
            column_widths = [8, 25, 10, 15, 12, 12, 12, 15, 15, 18, 20]
            for col, width in enumerate(column_widths, 1):
                ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width

            # 保存到内存
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)

        except ImportError:
            # 如果没有 openpyxl，生成 CSV
            import csv

            output = io.StringIO()
            writer = csv.writer(output)

            # 表头
            headers = [
                "序号", "项目名称", "业态", "所在地", "结构形式",
                "开工时间", "竣工时间", "总建筑面积(㎡)", "平米造价(元/㎡)",
                "录入时间", "更新时间",
            ]
            writer.writerow(headers)

            # 数据行
            for row_idx, summary in enumerate(summaries, 1):
                writer.writerow([
                    row_idx,
                    summary.name,
                    summary.category,
                    summary.location,
                    summary.structure,
                    summary.start_date or "",
                    summary.end_date or "",
                    summary.area_total or "",
                    summary.unit_cost or "",
                    summary.entry_date or "",
                    summary.updated_at,
                ])

            output.seek(0)
            output = io.BytesIO(output.getvalue().encode("utf-8-sig"))

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"指标库导出_{timestamp}.xlsx" if "openpyxl" in dir() else f"指标库导出_{timestamp}.csv"
        media_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if filename.endswith(".xlsx")
            else "text/csv"
        )

        logger.info(f"[export_to_excel] 导出完成 | records={len(summaries)} | file={filename}")

        return StreamingResponse(
            output,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            },
        )

    except Exception as e:
        logger.error(f"[export_to_excel] 导出失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ==================== 统计信息 ====================

@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_stats_overview(
    service: IndicatorLibraryService = Depends(get_service),
) -> Dict[str, Any]:
    """
    获取指标库统计概览

    - 返回项目总数、各业态分布、各地区分布等信息
    """
    logger.info("[get_stats_overview] 获取统计概览")

    try:
        stats = service.get_stats()
        logger.info(f"[get_stats_overview] 统计完成 | total={stats.get('total', 0)}")
        return stats

    except Exception as e:
        logger.error(f"[get_stats_overview] 获取统计失败 | error={e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")