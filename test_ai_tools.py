"""
AI工具调用功能测试脚本
测试日期解析和工具执行功能
"""

import sys
import os

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web', 'backend'))

from services.ai_tools import DateParser, get_tools_definitions, format_tool_result
from services.tool_executor import ToolExecutor
import asyncio


def test_date_parser():
    """测试日期解析器"""
    print("=" * 50)
    print("测试日期解析器")
    print("=" * 50)

    test_dates = [
        "2024-05-15",
        "2024年5月15日",
        "5月15日",
        "今天",
        "昨天",
        "前天",
        "本周一",
        "上周五",
        "5.15",
        "5/15"
    ]

    for date_str in test_dates:
        parsed = DateParser.parse(date_str)
        print(f"  {date_str:15s} -> {parsed}")

    print()


def test_tools_definitions():
    """测试工具定义"""
    print("=" * 50)
    print("测试工具定义")
    print("=" * 50)

    tools = get_tools_definitions()
    print(f"工具数量: {len(tools)}")
    print()

    for tool in tools:
        func = tool.get("function", {})
        print(f"  工具名称: {func.get('name')}")
        print(f"  描述: {func.get('description')}")
        print()

    print()


async def test_tool_executor():
    """测试工具执行器"""
    print("=" * 50)
    print("测试工具执行器")
    print("=" * 50)

    executor = ToolExecutor()

    # 测试1: 获取最新价格
    print("\n[测试1] 获取最新价格")
    result = await executor.execute("get_latest_prices", {"limit": 5})
    print(f"结果: {result}")

    # 测试2: 搜索材料
    print("\n[测试2] 搜索材料")
    result = await executor.execute("search_materials", {"keyword": "钢"})
    print(f"结果: {result}")

    # 测试3: 查询今日价格
    print("\n[测试3] 查询今日价格")
    result = await executor.execute("query_price_by_date", {"date": "今天"})
    print(f"结果: {result}")

    # 测试4: 格式化结果
    print("\n[测试4] 格式化结果")
    from services.ai_tools import format_tool_result
    mock_result = {
        "success": True,
        "date": "2024-05-15",
        "data": [
            {"date": "2024-05-15", "material_name": "螺纹钢", "spec": "HRB400E Φ12", "price": 3850},
            {"date": "2024-05-15", "material_name": "螺纹钢", "spec": "HRB400E Φ14", "price": 3870}
        ]
    }
    formatted = format_tool_result("query_price_by_date", mock_result)
    print(f"格式化结果:\n{formatted}")

    print()


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("AI工具调用功能测试")
    print("=" * 50 + "\n")

    # 测试日期解析
    test_date_parser()

    # 测试工具定义
    test_tools_definitions()

    # 测试工具执行
    asyncio.run(test_tool_executor())

    print("=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
