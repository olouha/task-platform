"""
AI 工具执行引擎
执行 AI 助手调用的工具函数
"""

import logging
import sqlite3
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from services.ai_tools import DateParser, format_tool_result

logger = logging.getLogger(__name__)

# 数据库路径
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "yantai_rebar.db"
COST_REF_DB_PATH = BASE_DIR / "services" / "data" / "cost_reference.db"


class ToolExecutor:
    """工具执行器"""

    def __init__(self):
        self.db_path = str(DB_PATH)
        self.cost_ref_db_path = str(COST_REF_DB_PATH)
        logger.info(f"[ToolExecutor] 初始化 | yantai_db={self.db_path}")
        logger.info(f"[ToolExecutor] 初始化 | cost_ref_db={self.cost_ref_db_path}")

    async def execute(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            执行结果
        """
        logger.info(f"[ToolExecutor] 执行工具 | name={tool_name}, params={parameters}")

        try:
            # 根据工具名称调用对应方法
            method = getattr(self, f"_tool_{tool_name}", None)
            if method is None:
                logger.warning(f"[ToolExecutor] 未找到工具 | name={tool_name}")
                return {"error": f"未知工具: {tool_name}"}

            # 执行工具
            result = await method(**parameters)
            logger.info(f"[ToolExecutor] 工具执行完成 | name={tool_name}")
            return result

        except Exception as e:
            logger.error(f"[ToolExecutor] 工具执行失败 | name={tool_name}, error={e}", exc_info=True)
            return {"error": str(e)}

    # ==================== 工具实现 ====================

    async def _tool_query_price_by_date(
        self,
        date: str,
        material: Optional[str] = None,
        spec: Optional[str] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询指定日期的价格

        Args:
            date: 日期字符串
            material: 材料名称
            spec: 规格
            region: 地区

        Returns:
            查询结果
        """
        logger.info(f"[query_price_by_date] 开始 | date={date}, material={material}, spec={spec}")

        # 解析日期
        parsed_date = DateParser.parse(date)
        if not parsed_date:
            return {"error": f"无法解析日期: {date}"}

        logger.info(f"[query_price_by_date] 日期解析 | original={date} -> parsed={parsed_date}")

        # 查询数据库
        results = self._query_yantai_db(
            date=parsed_date,
            material=material,
            spec=spec
        )

        if not results:
            return {
                "success": True,
                "date": parsed_date,
                "message": f"未找到 {parsed_date} 的价格数据",
                "data": []
            }

        return {
            "success": True,
            "date": parsed_date,
            "count": len(results),
            "data": results
        }

    async def _tool_query_price_range(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        material: Optional[str] = None,
        spec: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询日期范围内的价格

        Args:
            start_date: 开始日期
            end_date: 结束日期
            material: 材料名称
            spec: 规格

        Returns:
            查询结果
        """
        logger.info(f"[query_price_range] 开始 | start={start_date}, end={end_date}")

        # 解析日期
        parsed_start = DateParser.parse(start_date)
        if not parsed_start:
            return {"error": f"无法解析开始日期: {start_date}"}

        # 如果没有指定结束日期，使用今天
        if end_date:
            parsed_end = DateParser.parse(end_date)
            if not parsed_end:
                return {"error": f"无法解析结束日期: {end_date}"}
        else:
            parsed_end = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"[query_price_range] 日期范围 | {parsed_start} ~ {parsed_end}")

        # 查询数据库
        results = self._query_yantai_range(
            start_date=parsed_start,
            end_date=parsed_end,
            material=material,
            spec=spec
        )

        # 按日期分组
        grouped = {}
        for row in results:
            date_val = row.get('date')
            if date_val not in grouped:
                grouped[date_val] = []
            grouped[date_val].append(row)

        return {
            "success": True,
            "start_date": parsed_start,
            "end_date": parsed_end,
            "total_count": len(results),
            "dates_count": len(grouped),
            "data": grouped
        }

    async def _tool_query_price_trend(
        self,
        material: Optional[str] = None,
        spec: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        查询价格趋势

        Args:
            material: 材料名称
            spec: 规格
            days: 统计天数

        Returns:
            趋势分析结果
        """
        logger.info(f"[query_price_trend] 开始 | material={material}, days={days}")

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 查询数据
        results = self._query_yantai_range(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            material=material,
            spec=spec
        )

        if not results:
            return {
                "success": True,
                "message": f"最近 {days} 天没有找到相关数据",
                "data": []
            }

        # 按日期分组并计算统计
        daily_stats = {}
        for row in results:
            date_val = row.get('date')
            price = row.get('price')

            if date_val not in daily_stats:
                daily_stats[date_val] = {
                    'date': date_val,
                    'prices': [],
                    'count': 0
                }

            if price:
                daily_stats[date_val]['prices'].append(price)
                daily_stats[date_val]['count'] += 1

        # 计算每日均价
        trend_data = []
        for date_val in sorted(daily_stats.keys()):
            stats = daily_stats[date_val]
            prices = stats['prices']

            if prices:
                trend_data.append({
                    'date': date_val,
                    'avg_price': round(sum(prices) / len(prices), 2),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'count': len(prices)
                })

        # 计算总体趋势
        if len(trend_data) >= 2:
            first_avg = trend_data[0]['avg_price']
            last_avg = trend_data[-1]['avg_price']
            change = last_avg - first_avg
            change_pct = (change / first_avg * 100) if first_avg > 0 else 0

            trend_summary = {
                'start_date': trend_data[0]['date'],
                'end_date': trend_data[-1]['date'],
                'start_price': first_avg,
                'end_price': last_avg,
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'direction': '上涨' if change > 0 else ('下跌' if change < 0 else '持平')
            }
        else:
            trend_summary = None

        return {
            "success": True,
            "days": days,
            "data_points": len(trend_data),
            "summary": trend_summary,
            "data": trend_data
        }

    async def _tool_search_materials(
        self,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        搜索材料信息

        Args:
            keyword: 搜索关键词

        Returns:
            材料列表
        """
        logger.info(f"[search_materials] 开始 | keyword={keyword}")

        materials = self._get_materials(keyword)

        return {
            "success": True,
            "count": len(materials),
            "data": materials
        }

    async def _tool_get_latest_prices(
        self,
        material: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取最新价格

        Args:
            material: 材料名称
            limit: 返回数量

        Returns:
            最新价格数据
        """
        logger.info(f"[get_latest_prices] 开始 | material={material}, limit={limit}")

        # 查询最新日期
        latest_date = self._get_latest_date()
        if not latest_date:
            return {"error": "数据库中没有价格数据"}

        logger.info(f"[get_latest_prices] 最新日期 | date={latest_date}")

        # 查询该日期的数据
        results = self._query_yantai_db(
            date=latest_date,
            material=material,
            limit=limit
        )

        return {
            "success": True,
            "date": latest_date,
            "count": len(results),
            "data": results
        }

    async def _tool_compare_prices(
        self,
        date1: str,
        date2: str,
        material: Optional[str] = None,
        spec: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        对比两个日期的价格

        Args:
            date1: 第一个日期
            date2: 第二个日期
            material: 材料名称
            spec: 规格

        Returns:
            价格对比结果
        """
        logger.info(f"[compare_prices] 开始 | date1={date1}, date2={date2}")

        # 解析日期
        parsed_date1 = DateParser.parse(date1)
        parsed_date2 = DateParser.parse(date2)

        if not parsed_date1 or not parsed_date2:
            return {"error": "无法解析日期"}

        # 查询两个日期的数据
        data1 = self._query_yantai_db(date=parsed_date1, material=material, spec=spec)
        data2 = self._query_yantai_db(date=parsed_date2, material=material, spec=spec)

        # 构建对比结果
        comparison = []

        # 按材料+规格分组对比
        def get_key(row):
            return f"{row.get('material_name', '')}|{row.get('spec', '')}"

        map1 = {get_key(row): row for row in data1}
        map2 = {get_key(row): row for row in data2}

        all_keys = set(map1.keys()) | set(map2.keys())

        for key in all_keys:
            row1 = map1.get(key)
            row2 = map2.get(key)

            if row1 and row2:
                price1 = row1.get('price', 0)
                price2 = row2.get('price', 0)
                change = price2 - price1
                change_pct = (change / price1 * 100) if price1 > 0 else 0

                comparison.append({
                    'material': row1.get('material_name'),
                    'spec': row1.get('spec'),
                    'date1': parsed_date1,
                    'price1': price1,
                    'date2': parsed_date2,
                    'price2': price2,
                    'change': round(change, 2),
                    'change_pct': round(change_pct, 2),
                    'direction': '上涨' if change > 0 else ('下跌' if change < 0 else '持平')
                })
            elif row1:
                comparison.append({
                    'material': row1.get('material_name'),
                    'spec': row1.get('spec'),
                    'date1': parsed_date1,
                    'price1': row1.get('price'),
                    'date2': parsed_date2,
                    'price2': None,
                    'change': None,
                    'change_pct': None,
                    'direction': '无数据'
                })
            elif row2:
                comparison.append({
                    'material': row2.get('material_name'),
                    'spec': row2.get('spec'),
                    'date1': parsed_date1,
                    'price1': None,
                    'date2': parsed_date2,
                    'price2': row2.get('price'),
                    'change': None,
                    'change_pct': None,
                    'direction': '新增'
                })

        return {
            "success": True,
            "date1": parsed_date1,
            "date2": parsed_date2,
            "count": len(comparison),
            "data": comparison
        }

    # ==================== 数据库辅助方法 ====================

    def _get_db_connection(self, db_path: str = None):
        """获取数据库连接"""
        path = db_path or self.db_path
        if not os.path.exists(path):
            logger.warning(f"[_get_db_connection] 数据库不存在 | path={path}")
            return None
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _query_yantai_db(
        self,
        date: str,
        material: Optional[str] = None,
        spec: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """查询烟台价格数据库"""
        conn = self._get_db_connection()
        if not conn:
            return []

        try:
            c = conn.cursor()

            sql = '''
                SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = ?
            '''
            params = [date]

            if material:
                sql += ' AND material_name LIKE ?'
                params.append(f'%{material}%')

            if spec:
                sql += ' AND spec LIKE ?'
                params.append(f'%{spec}%')

            sql += ' ORDER BY CASE WHEN fetch_time LIKE \'09%\' THEN 1 ELSE 2 END, material_name, spec LIMIT ?'
            params.append(limit)

            c.execute(sql, params)
            rows = c.fetchall()
            conn.close()

            # 格式化结果
            results = []
            for row in rows:
                d = dict(row)
                # 添加时段字段
                fetch_time = d.get('fetch_time', '')
                if fetch_time and (fetch_time.startswith('09') or fetch_time.startswith('12')):
                    d['time'] = '上午'
                elif fetch_time:
                    d['time'] = '下午'
                else:
                    d['time'] = '全天'
                results.append(d)

            logger.info(f"[_query_yantai_db] 查询完成 | date={date}, count={len(results)}")
            return results

        except Exception as e:
            logger.error(f"[_query_yantai_db] 查询失败 | error={e}", exc_info=True)
            conn.close()
            return []

    def _query_yantai_range(
        self,
        start_date: str,
        end_date: str,
        material: Optional[str] = None,
        spec: Optional[str] = None
    ) -> List[Dict]:
        """查询日期范围内的数据"""
        conn = self._get_db_connection()
        if not conn:
            return []

        try:
            c = conn.cursor()

            sql = '''
                SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date BETWEEN ? AND ?
            '''
            params = [start_date, end_date]

            if material:
                sql += ' AND material_name LIKE ?'
                params.append(f'%{material}%')

            if spec:
                sql += ' AND spec LIKE ?'
                params.append(f'%{spec}%')

            sql += ' ORDER BY date, CASE WHEN fetch_time LIKE \'09%\' THEN 1 ELSE 2 END, material_name, spec'

            c.execute(sql, params)
            rows = c.fetchall()
            conn.close()

            results = []
            for row in rows:
                d = dict(row)
                fetch_time = d.get('fetch_time', '')
                if fetch_time and (fetch_time.startswith('09') or fetch_time.startswith('12')):
                    d['time'] = '上午'
                elif fetch_time:
                    d['time'] = '下午'
                else:
                    d['time'] = '全天'
                results.append(d)

            logger.info(f"[_query_yantai_range] 查询完成 | range={start_date}~{end_date}, count={len(results)}")
            return results

        except Exception as e:
            logger.error(f"[_query_yantai_range] 查询失败 | error={e}", exc_info=True)
            conn.close()
            return []

    def _get_latest_date(self) -> Optional[str]:
        """获取数据库中最新的日期"""
        conn = self._get_db_connection()
        if not conn:
            return None

        try:
            c = conn.cursor()
            c.execute('SELECT MAX(date) FROM rebar_prices')
            result = c.fetchone()
            conn.close()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.error(f"[_get_latest_date] 查询失败 | error={e}", exc_info=True)
            conn.close()
            return None

    def _get_materials(self, keyword: Optional[str] = None) -> List[Dict]:
        """获取材料列表"""
        conn = self._get_db_connection()
        if not conn:
            return []

        try:
            c = conn.cursor()

            if keyword:
                c.execute('''
                    SELECT DISTINCT material_name, COUNT(*) as cnt
                    FROM rebar_prices
                    WHERE material_name LIKE ?
                    GROUP BY material_name
                    ORDER BY cnt DESC
                ''', (f'%{keyword}%',))
            else:
                c.execute('''
                    SELECT DISTINCT material_name, COUNT(*) as cnt
                    FROM rebar_prices
                    GROUP BY material_name
                    ORDER BY cnt DESC
                ''')

            rows = c.fetchall()
            conn.close()

            return [{'name': row[0], 'count': row[1]} for row in rows]

        except Exception as e:
            logger.error(f"[_get_materials] 查询失败 | error={e}", exc_info=True)
            conn.close()
            return []


# 全局实例
tool_executor = ToolExecutor()


async def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工具（便捷函数）

    Args:
        tool_name: 工具名称
        parameters: 工具参数

    Returns:
        执行结果
    """
    return await tool_executor.execute(tool_name, parameters)
