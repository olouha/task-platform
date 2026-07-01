# -*- coding: utf-8 -*-
"""
Excel解析服务
解析指标库Excel文件，包含汇总sheet和明细sheet
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.cell.cell import TYPE_FORMULA

logger = logging.getLogger(__name__)


class ExcelParserService:
    """Excel解析服务"""

    # 汇总sheet列映射: Excel列名 -> 数据库字段名
    SUMMARY_COLUMN_MAPPING = {
        "序号": "index",
        "项目名称": "name",
        "业态": "category",
        "项目所在地": "location",
        "结构形式": "structure",
        "交付形式": "delivery_form",
        "层数（地上/下）": "floor_info",
        "总面积（m2）": "area_total",
        "檐高（m）": "height",
        "总造价": "total_cost",
    }

    # 明细sheet列映射: Excel列名 -> 数据库字段名
    DETAIL_COLUMN_MAPPING = {
        "序号": "index",
        "项目名称": "name",
        "业态": "category",
        "项目所在地": "location",
        "结构形式": "structure",
        "层数（地上/下）": "floor_info",
        "总面积（m2）": "area_total",
        "檐高（m）": "height",
        "单方造价（元/m2）": "unit_cost",
        "土建工程": "unit_structure",
        "安装工程": "unit_installation",
        "装饰工程": "unit_decoration",
        "措施项目": "unit_measure",
        "钢筋": "steel",
        "混凝土": "concrete",
        "模板": "formwork",
        "砌体": "block",
        "电缆": "cable",
        "管道": "pipe",
        "风管": "duct",
        "地下结构": "underground_structure",
        "地上结构": "above_structure",
        "屋面": "roof",
        "外墙": "exterior_wall",
        "内墙": "interior_wall",
        "楼地面": "floor",
        "电气": "electrical",
        "给排水": "plumbing",
        "暖通": "hvac",
        "电梯": "elevator",
        "消防": "fire",
        "措施": "measures",
        "交付形式": "delivery_form",
        "总造价": "total_cost",
        "备注": "remarks",
    }

    def __init__(self, file_path: str):
        """
        初始化Excel解析服务

        Args:
            file_path: Excel文件路径
        """
        self.file_path = Path(file_path)
        logger.info(f"[ExcelParserService] 初始化解析器 | file_path={self.file_path}")

        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel文件不存在: {self.file_path}")

        self.workbook: Optional[openpyxl.Workbook] = None
        self.summary_headers: List[str] = []
        self.detail_headers: List[str] = []
        self.merged_headers: Dict[int, str] = {}

    def parse(self) -> Dict[str, Any]:
        """
        解析Excel文件

        Returns:
            包含projects列表和metadata的字典
        """
        logger.info(f"[ExcelParserService] 开始解析 | file={self.file_path.name}")

        try:
            # 加载工作簿
            self.workbook = openpyxl.load_workbook(
                self.file_path,
                data_only=True,  # 只读取值，不读取公式
                read_only=True
            )
            logger.info(f"[ExcelParserService] 工作簿加载成功 | sheets={self.workbook.sheetnames}")

            # 检查必要的sheet
            if "汇总" not in self.workbook.sheetnames:
                raise ValueError("Excel文件缺少'汇总'sheet")
            if "明细" not in self.workbook.sheetnames:
                raise ValueError("Excel文件缺少'明细'sheet")

            # 解析汇总sheet
            summary_data = self._parse_summary_sheet()
            logger.info(f"[ExcelParserService] 汇总sheet解析完成 | rows={len(summary_data)}")

            # 解析明细sheet
            detail_data = self._parse_detail_sheet()
            logger.info(f"[ExcelParserService] 明细sheet解析完成 | rows={len(detail_data)}")

            # 合并数据
            merged_data = self._merge_data(summary_data, detail_data)
            logger.info(f"[ExcelParserService] 数据合并完成 | rows={len(merged_data)}")

            # 构建返回结果
            result = {
                "success": True,
                "projects": merged_data,
                "metadata": {
                    "source_file": self.file_path.name,
                    "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "total_projects": len(merged_data),
                    "summary_rows": len(summary_data),
                    "detail_rows": len(detail_data),
                }
            }

            logger.info(f"[ExcelParserService] 解析完成 | total_projects={len(merged_data)}")
            return result

        except Exception as e:
            logger.error(f"[ExcelParserService] 解析失败 | error={e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "projects": [],
                "metadata": {
                    "source_file": self.file_path.name,
                    "entry_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error": str(e),
                }
            }
        finally:
            if self.workbook:
                self.workbook.close()

    def _parse_summary_sheet(self) -> List[Dict[str, Any]]:
        """
        解析汇总sheet

        Returns:
            汇总数据列表
        """
        logger.info("[ExcelParserService] 解析汇总sheet")

        ws = self.workbook["汇总"]
        rows = list(ws.iter_rows(values_only=True))

        if len(rows) < 2:
            logger.warning("[ExcelParserService] 汇总sheet数据行数不足")
            return []

        # 获取表头
        header_row = rows[0]
        self.summary_headers = [str(cell) if cell else "" for cell in header_row]
        logger.debug(f"[ExcelParserService] 汇总表头 | headers={self.summary_headers}")

        # 解析数据行
        data_rows = []
        for row_idx, row in enumerate(rows[1:], start=2):
            if self._is_empty_row(row):
                continue

            row_data = self._parse_summary_row(row)
            if row_data:
                row_data["_row_index"] = row_idx
                data_rows.append(row_data)

        return data_rows

    def _parse_summary_row(self, row: Tuple) -> Dict[str, Any]:
        """
        解析汇总sheet的单行数据

        Args:
            row: 行数据元组

        Returns:
            解析后的行数据字典
        """
        row_data = {}

        for col_idx, cell_value in enumerate(row):
            if col_idx >= len(self.summary_headers):
                break

            header = self.summary_headers[col_idx]
            if header not in self.SUMMARY_COLUMN_MAPPING:
                continue

            field_name = self.SUMMARY_COLUMN_MAPPING[header]
            value = self._clean_cell_value(cell_value)
            row_data[field_name] = value

        return row_data

    def _parse_detail_sheet(self) -> List[Dict[str, Any]]:
        """
        解析明细sheet，处理多级表头

        Returns:
            明细数据列表
        """
        logger.info("[ExcelParserService] 解析明细sheet")

        ws = self.workbook["明细"]
        rows = list(ws.iter_rows(values_only=True))

        if len(rows) < 4:
            logger.warning("[ExcelParserService] 明细sheet数据行数不足（需要至少4行表头）")
            return []

        # 构建合并后的表头（融合第2-4行的多级表头）
        self.merged_headers = self._build_merged_headers(rows[:4])
        logger.debug(f"[ExcelParserService] 明细合并表头 | headers={self.merged_headers}")

        # 解析数据行（从第5行开始，索引为4）
        data_rows = []
        for row_idx, row in enumerate(rows[4:], start=5):
            if self._is_empty_row(row):
                continue

            row_data = self._parse_detail_row(row)
            if row_data:
                row_data["_row_index"] = row_idx
                data_rows.append(row_data)

        return data_rows

    def _build_merged_headers(self, header_rows: List[Tuple]) -> Dict[int, str]:
        """
        构建合并后的多级表头

        Args:
            header_rows: 前4行表头数据

        Returns:
            列索引到合并后表头名称的映射
        """
        merged = {}

        if len(header_rows) < 4:
            # 如果没有足够的多级表头，直接使用第一行
            for col_idx, cell in enumerate(header_rows[0]):
                if cell:
                    merged[col_idx] = str(cell)
            return merged

        # 第1行: 大类分组（如：基本信息、造价指标、分部工程等）
        # 第2-4行: 具体列名
        group_row = header_rows[0]
        sub_rows = header_rows[1:4]

        for col_idx in range(max(len(row) for row in header_rows)):
            # 获取子类表头（从第2-4行）
            sub_header = ""
            for row in sub_rows:
                if col_idx < len(row) and row[col_idx]:
                    sub_val = str(row[col_idx]).strip()
                    if sub_val:
                        sub_header = sub_val
                        break

            # 如果没有子类表头，尝试使用第一行
            if not sub_header and col_idx < len(group_row):
                group_val = str(group_row[col_idx]).strip() if group_row[col_idx] else ""
                sub_header = group_val

            if sub_header:
                merged[col_idx] = sub_header

        return merged

    def _parse_detail_row(self, row: Tuple) -> Dict[str, Any]:
        """
        解析明细sheet的单行数据

        Args:
            row: 行数据元组

        Returns:
            解析后的行数据字典
        """
        row_data = {}

        for col_idx, cell_value in enumerate(row):
            if col_idx not in self.merged_headers:
                continue

            header = self.merged_headers[col_idx]
            if header not in self.DETAIL_COLUMN_MAPPING:
                continue

            field_name = self.DETAIL_COLUMN_MAPPING[header]
            value = self._clean_cell_value(cell_value)
            row_data[field_name] = value

        return row_data

    def _merge_data(
        self,
        summary_data: List[Dict[str, Any]],
        detail_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        合并汇总和明细数据

        Args:
            summary_data: 汇总数据
            detail_data: 明细数据

        Returns:
            合并后的数据列表
        """
        logger.info(f"[ExcelParserService] 合并数据 | summary={len(summary_data)}, detail={len(detail_data)}")

        merged = []

        # 使用行索引进行匹配
        summary_by_index = {row.get("_row_index", 0): row for row in summary_data}
        detail_by_index = {row.get("_row_index", 0): row for row in detail_data}

        # 获取所有唯一的行索引
        all_indices = set(summary_by_index.keys()) | set(detail_by_index.keys())

        for row_idx in sorted(all_indices):
            summary_row = summary_by_index.get(row_idx, {})
            detail_row = detail_by_index.get(row_idx, {})

            # 合并数据，detail优先（包含更详细的信息）
            merged_row = {**summary_row, **detail_row}

            # 移除内部使用的_row_index
            merged_row.pop("_row_index", None)

            # 解析楼层信息
            floor_info = merged_row.get("floor_info")
            if floor_info:
                floor_above, floor_below = self._parse_floor_info(str(floor_info))
                merged_row["floor_above"] = floor_above
                merged_row["floor_below"] = floor_below
                merged_row.pop("floor_info", None)

            merged.append(merged_row)

        logger.info(f"[ExcelParserService] 数据合并完成 | merged={len(merged)}")
        return merged

    def _parse_floor_info(self, floor_info: str) -> Tuple[Optional[int], Optional[int]]:
        """
        解析楼层信息字符串

        Args:
            floor_info: 楼层信息字符串，格式如 "地上30/地下3"

        Returns:
            (地上楼层数, 地下楼层数) 元组
        """
        floor_above = None
        floor_below = None

        try:
            # 匹配地上楼层
            above_match = re.search(r"地上\s*(\d+)", floor_info)
            if above_match:
                floor_above = int(above_match.group(1))

            # 匹配地下楼层
            below_match = re.search(r"地下\s*(\d+)", floor_info)
            if below_match:
                floor_below = int(below_match.group(1))
        except Exception as e:
            logger.warning(f"[ExcelParserService] 解析楼层信息失败 | floor_info={floor_info}, error={e}")

        return floor_above, floor_below

    def _clean_cell_value(self, value: Any) -> Any:
        """
        清理单元格值

        Args:
            value: 原始单元格值

        Returns:
            清理后的值
        """
        if value is None:
            return None

        # 如果是字符串，处理常见问题
        if isinstance(value, str):
            # 去除首尾空白
            value = value.strip()

            # 处理公式引用错误
            if "#REF!" in value or "#REF" in value:
                logger.debug(f"[ExcelParserService] 跳过公式错误值 | value={value}")
                return None

            # 处理其他Excel错误
            if value.startswith("#"):
                return None

            # 处理空字符串
            if not value:
                return None

            return value

        return value

    def _is_empty_row(self, row: Tuple) -> bool:
        """
        检查行是否为空

        Args:
            row: 行数据元组

        Returns:
            是否为空行
        """
        return all(cell is None or str(cell).strip() == "" for cell in row)

    @staticmethod
    def get_column_letter(col_idx: int) -> str:
        """
        获取列字母标识

        Args:
            col_idx: 列索引（从0开始）

        Returns:
            列字母（如：A, B, C, ...）
        """
        result = ""
        col_idx += 1  # 转换为从1开始
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def validate_excel_structure(file_path: str) -> Dict[str, Any]:
        """
        验证Excel文件结构

        Args:
            file_path: Excel文件路径

        Returns:
            验证结果
        """
        logger.info(f"[ExcelParserService] 验证Excel结构 | file={file_path}")

        try:
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheets = wb.sheetnames

            result = {
                "valid": True,
                "has_summary": "汇总" in sheets,
                "has_detail": "明细" in sheets,
                "sheets": sheets,
                "errors": []
            }

            if "汇总" not in sheets:
                result["valid"] = False
                result["errors"].append("缺少'汇总'sheet")

            if "明细" not in sheets:
                result["valid"] = False
                result["errors"].append("缺少'明细'sheet")

            wb.close()
            logger.info(f"[ExcelParserService] 验证完成 | valid={result['valid']}")
            return result

        except Exception as e:
            logger.error(f"[ExcelParserService] 验证失败 | error={e}", exc_info=True)
            return {
                "valid": False,
                "error": str(e),
                "errors": [str(e)]
            }