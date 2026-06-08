"""
AI 工具定义模块
定义 AI 助手可调用的所有工具函数
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """工具分类"""
    PRICE_QUERY = "price_query"      # 价格查询
    PRICE_TREND = "price_trend"      # 价格趋势
    MATERIAL_SEARCH = "material_search"  # 材料搜索
    DATA_ANALYSIS = "data_analysis"  # 数据分析


# ==================== 工具定义 ====================

TOOLS_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_price_by_date",
            "description": "查询指定日期的材料价格数据。支持按日期、材料名称、规格查询价格。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "查询日期，支持格式：YYYY-MM-DD（2024-05-15）、中文日期（2024年5月15日）、相对日期（今天、昨天、本周一）"
                    },
                    "material": {
                        "type": "string",
                        "description": "材料名称，如：螺纹钢、水泥、砂石、混凝土等。可选，不填则返回所有材料价格。"
                    },
                    "spec": {
                        "type": "string",
                        "description": "规格型号，如：HRB400E Φ14、C30、中砂等。可选。"
                    },
                    "region": {
                        "type": "string",
                        "description": "地区，如：烟台、乳山等。可选，默认为烟台。"
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_price_range",
            "description": "查询指定日期范围内的价格数据，用于分析价格变化趋势。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "开始日期，格式：YYYY-MM-DD 或中文日期"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期，格式：YYYY-MM-DD 或中文日期。可选，默认为今天。"
                    },
                    "material": {
                        "type": "string",
                        "description": "材料名称，如：螺纹钢、水泥等。可选。"
                    },
                    "spec": {
                        "type": "string",
                        "description": "规格型号。可选。"
                    }
                },
                "required": ["start_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_price_trend",
            "description": "查询材料价格趋势分析，包括涨跌幅、最高价、最低价等统计数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material": {
                        "type": "string",
                        "description": "材料名称，如：螺纹钢、水泥等。可选，不填则分析所有材料。"
                    },
                    "spec": {
                        "type": "string",
                        "description": "规格型号。可选。"
                    },
                    "days": {
                        "type": "integer",
                        "description": "统计天数，如7表示最近7天，30表示最近30天。默认为30天。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_materials",
            "description": "搜索材料信息，获取可用的材料列表和规格信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，如：钢、水泥等。可选，不填则返回所有材料。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_latest_prices",
            "description": "获取最新的价格数据，即最近一次更新的价格信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "material": {
                        "type": "string",
                        "description": "材料名称，如：螺纹钢、水泥等。可选。"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数量限制。默认20条。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_prices",
            "description": "对比两个日期之间的价格变化，计算涨跌幅度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "date1": {
                        "type": "string",
                        "description": "第一个日期（基准日期），格式：YYYY-MM-DD 或中文日期"
                    },
                    "date2": {
                        "type": "string",
                        "description": "第二个日期（对比日期），格式：YYYY-MM-DD 或中文日期"
                    },
                    "material": {
                        "type": "string",
                        "description": "材料名称。可选。"
                    },
                    "spec": {
                        "type": "string",
                        "description": "规格型号。可选。"
                    }
                },
                "required": ["date1", "date2"]
            }
        }
    }
]


# ==================== 日期解析器 ====================

class DateParser:
    """智能日期解析器"""

    # 中文数字映射
    CN_NUMS = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10
    }

    # 月份映射
    CN_MONTHS = {
        '1月': 1, '2月': 2, '3月': 3, '4月': 4, '5月': 5, '6月': 6,
        '7月': 7, '8月': 8, '9月': 9, '10月': 10, '11月': 11, '12月': 12,
        '一月': 1, '二月': 2, '三月': 3, '四月': 4, '五月': 5, '六月': 6,
        '七月': 7, '八月': 8, '九月': 9, '十月': 10, '十一月': 11, '十二月': 12
    }

    # 相对日期映射
    RELATIVE_DATES = {
        '今天': 0,
        '今日': 0,
        '昨天': -1,
        '昨日': -1,
        '前天': -2,
        '大前天': -3,
        '明天': 1,
        '明日': 1,
        '后天': 2,
        '大后天': 3
    }

    # 星期映射
    WEEKDAYS = {
        '周一': 0, '星期一': 0,
        '周二': 1, '星期二': 1,
        '周三': 2, '星期三': 2,
        '周四': 3, '星期四': 3,
        '周五': 4, '星期五': 4,
        '周六': 5, '星期六': 5,
        '周日': 6, '星期日': 6, '周七': 6, '星期七': 6
    }

    @staticmethod
    def parse(date_str: str) -> Optional[str]:
        """
        解析日期字符串，返回 YYYY-MM-DD 格式

        支持格式：
        - 标准格式：2024-05-15
        - 中文日期：2024年5月15日、5月15日
        - 相对日期：今天、昨天、前天
        - 星期：本周一、上周五
        - 相对星期：这周一、上周三

        Args:
            date_str: 日期字符串

        Returns:
            YYYY-MM-DD 格式的日期字符串，解析失败返回 None
        """
        if not date_str:
            return None

        date_str = date_str.strip()
        logger.info(f"[DateParser] 解析日期 | input={date_str}")

        try:
            # 1. 标准格式 YYYY-MM-DD
            if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                return date_str

            # 2. 中文日期：2024年5月15日
            if '年' in date_str and '月' in date_str and '日' in date_str:
                parts = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                parts = parts.split('-')
                if len(parts) == 3:
                    year, month, day = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

            # 3. 简化中文日期：5月15日（当年）
            if '月' in date_str and '日' in date_str and '年' not in date_str:
                today = datetime.now()
                parts = date_str.replace('月', '-').replace('日', '')
                parts = parts.split('-')
                if len(parts) == 2:
                    month, day = parts
                    # 处理中文数字月份
                    if month in DateParser.CN_MONTHS:
                        month = DateParser.CN_MONTHS[month]
                    return f"{today.year}-{int(month):02d}-{int(day):02d}"

            # 4. 相对日期：今天、昨天
            if date_str in DateParser.RELATIVE_DATES:
                days = DateParser.RELATIVE_DATES[date_str]
                target_date = datetime.now() + timedelta(days=days)
                return target_date.strftime('%Y-%m-%d')

            # 5. 相对星期：本周一、上周五
            if date_str.startswith('本') or date_str.startswith('这') or date_str.startswith('上') or date_str.startswith('下'):
                return DateParser._parse_relative_weekday(date_str)

            # 6. 星期几：周一、星期五
            if date_str in DateParser.WEEKDAYS:
                return DateParser._parse_weekday(date_str)

            # 7. 数字格式：5.15、5/15
            if '.' in date_str or '/' in date_str:
                sep = '.' if '.' in date_str else '/'
                parts = date_str.split(sep)
                if len(parts) == 2:
                    month, day = parts
                    today = datetime.now()
                    return f"{today.year}-{int(month):02d}-{int(day):02d}"

            logger.warning(f"[DateParser] 日期格式无法识别 | input={date_str}")
            return None

        except Exception as e:
            logger.error(f"[DateParser] 解析失败 | input={date_str}, error={e}", exc_info=True)
            return None

    @staticmethod
    def _parse_weekday(weekday_str: str) -> str:
        """解析星期几（本周的）"""
        target_weekday = DateParser.WEEKDAYS.get(weekday_str)
        if target_weekday is None:
            return None

        today = datetime.now()
        current_weekday = today.weekday()

        # 计算日期差
        days_diff = target_weekday - current_weekday
        if days_diff <= 0:
            # 如果目标日期是今天或之前，可能需要找下周的
            # 但通常"周一"指的是本周的周一，如果今天周三，周一就是两天前
            pass

        target_date = today + timedelta(days=days_diff)
        return target_date.strftime('%Y-%m-%d')

    @staticmethod
    def _parse_relative_weekday(date_str: str) -> Optional[str]:
        """解析相对星期：本周一、上周五、下周三"""
        today = datetime.now()

        # 提取星期几
        weekday_str = None
        for wd in DateParser.WEEKDAYS.keys():
            if wd in date_str or date_str.endswith(wd):
                weekday_str = wd
                break

        if not weekday_str:
            return None

        target_weekday = DateParser.WEEKDAYS[weekday_str]
        current_weekday = today.weekday()

        # 计算周偏移
        week_offset = 0
        if date_str.startswith('上'):
            week_offset = -1
        elif date_str.startswith('下'):
            week_offset = 1

        # 计算日期差
        days_diff = target_weekday - current_weekday + (week_offset * 7)

        target_date = today + timedelta(days=days_diff)
        return target_date.strftime('%Y-%m-%d')


def get_tools_definitions() -> List[Dict[str, Any]]:
    """获取所有工具定义"""
    return TOOLS_DEFINITIONS


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """根据名称获取工具定义"""
    for tool in TOOLS_DEFINITIONS:
        if tool.get("function", {}).get("name") == name:
            return tool
    return None


def format_tool_result(tool_name: str, result: Any) -> str:
    """
    格式化工具执行结果为可读文本

    Args:
        tool_name: 工具名称
        result: 工具执行结果

    Returns:
        格式化后的文本
    """
    if result is None:
        return "查询失败，未返回结果。"

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if "error" in result:
            return f"查询出错：{result['error']}"

        if "data" in result:
            return _format_data_result(result["data"])

        return _format_dict_result(result)

    if isinstance(result, list):
        if not result:
            return "未找到相关数据。"
        return _format_list_result(result)

    return str(result)


def _format_data_result(data: Any) -> str:
    """格式化数据结果"""
    if isinstance(data, list):
        if not data:
            return "未找到相关数据。"
        lines = ["查询结果："]
        for item in data[:20]:  # 限制显示数量
            if isinstance(item, dict):
                lines.append(_format_dict_item(item))
            else:
                lines.append(f"- {item}")
        if len(data) > 20:
            lines.append(f"...（还有 {len(data) - 20} 条记录）")
        return "\n".join(lines)
    elif isinstance(data, dict):
        return _format_dict_result(data)
    return str(data)


def _format_dict_result(data: dict) -> str:
    """格式化字典结果"""
    lines = []
    for key, value in data.items():
        if value is not None and value != []:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) if lines else "无数据"


def _format_dict_item(item: dict) -> str:
    """格式化单个字典项"""
    # 优先显示有意义的信息
    key_order = ['date', 'material_name', 'spec', 'brand', 'price', 'am_price', 'pm_price',
                 'year', 'quarter', 'grade', 'price_change', 'region']

    parts = []
    for key in key_order:
        if key in item and item[key] is not None:
            # 中文key映射
            cn_key = {
                'date': '日期',
                'material_name': '材料',
                'spec': '规格',
                'brand': '品牌',
                'price': '价格',
                'am_price': '上午价',
                'pm_price': '下午价',
                'year': '年份',
                'quarter': '季度',
                'grade': '等级',
                'price_change': '涨跌',
                'region': '地区'
            }.get(key, key)

            value = item[key]
            # 价格格式化
            if 'price' in key and isinstance(value, (int, float)):
                parts.append(f"{cn_key}: {value:.2f}元/吨")
            else:
                parts.append(f"{cn_key}: {value}")

    return " | ".join(parts) if parts else str(item)


def _format_list_result(items: list) -> str:
    """格式化列表结果"""
    lines = ["查询结果："]
    for item in items[:20]:
        if isinstance(item, dict):
            lines.append(f"- {_format_dict_item(item)}")
        else:
            lines.append(f"- {item}")
    if len(items) > 20:
        lines.append(f"...（还有 {len(items) - 20} 条记录）")
    return "\n".join(lines)
