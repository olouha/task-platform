"""
烟台钢筋数据库服务
提供价格数据的插入、查询、统计等功能
"""
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_FILE = Path(__file__).parent.parent.parent / 'data' / 'yantai_rebar.db'


def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接

    Returns:
        sqlite3.Connection: 数据库连接对象

    Notes:
        设置 row_factory 以支持列名访问
    """
    logger.debug(f"[get_db_connection] 连接数据库 | db={DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    初始化数据库表

    Creates:
        rebar_prices 表 - 钢筋价格主表
        索引 - date, material_name 索引以提高查询性能
    """
    logger.info("[init_db] 开始初始化数据库")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 创建价格主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rebar_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                material_name TEXT NOT NULL,
                spec TEXT,
                material_type TEXT,
                brand TEXT,
                price INTEGER NOT NULL,
                region TEXT DEFAULT '山东烟台',
                fetch_time TEXT,
                uploaded_by TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, material_name, spec, brand, price)
            )
        ''')

        # 检查并添加 fetch_time 字段（如果不存在）
        cursor.execute("PRAGMA table_info(rebar_prices)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'fetch_time' not in columns:
            cursor.execute('ALTER TABLE rebar_prices ADD COLUMN fetch_time TEXT')
            logger.info("[init_db] 已添加 fetch_time 字段")

        # 检查并添加 uploaded_by 字段（如果不存在）
        if 'uploaded_by' not in columns:
            cursor.execute('ALTER TABLE rebar_prices ADD COLUMN uploaded_by TEXT')
            logger.info("[init_db] 已添加 uploaded_by 字段")

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rebar_date ON rebar_prices(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rebar_material ON rebar_prices(material_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rebar_spec ON rebar_prices(spec)')

        conn.commit()
        logger.info("[init_db] 数据库初始化完成")

    except Exception as e:
        logger.error(f"[init_db] 初始化失败 | error={e}", exc_info=True)
        raise
    finally:
        conn.close()


class YantaiDBService:
    """
    烟台钢筋数据库服务类

    提供价格数据的批量插入、查询、统计等功能
    """

    def __init__(self, db_file: Optional[Path] = None):
        """
        初始化数据库服务

        Args:
            db_file: 数据库文件路径，默认为 services/data/yantai_rebar.db
        """
        self.db_file = db_file or DB_FILE
        logger.info(f"[YantaiDBService] 初始化 | db={self.db_file}")

    def insert_prices(self, prices: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量插入价格数据

        Args:
            prices: 价格数据列表，每个元素包含:
                - date: 日期 (YYYY-MM-DD)
                - material_name: 品名
                - spec: 规格
                - material_type: 材质
                - brand: 品牌/钢厂
                - price: 价格 (整数)
                - region: 地区 (可选，默认 '山东烟台')
                - fetch_time: 抓取时间 (可选，格式 HH:MM:SS)

        Returns:
            Dict[str, int]: 包含 inserted 和 skipped 的统计信息
        """
        logger.info(f"[insert_prices] 开始插入 | count={len(prices)}")

        if not prices:
            logger.warning("[insert_prices] 数据为空")
            return {"inserted": 0, "skipped": 0}

        conn = get_db_connection()
        cursor = conn.cursor()

        inserted = 0
        skipped = 0

        try:
            for price in prices:
                try:
                    cursor.execute('''
                        INSERT INTO rebar_prices
                        (date, material_name, spec, material_type, brand, price, region, fetch_time, uploaded_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        price.get('date', ''),
                        price.get('material_name', ''),
                        price.get('spec', ''),
                        price.get('material_type', ''),
                        price.get('brand', ''),
                        price.get('price', 0),
                        price.get('region', '山东烟台'),
                        price.get('fetch_time', ''),
                        price.get('uploaded_by', ''),
                    ))
                    inserted += 1
                except sqlite3.IntegrityError:
                    # 重复数据跳过
                    skipped += 1
                except Exception as e:
                    logger.warning(f"[insert_prices] 插入失败 | data={price} | error={e}")
                    skipped += 1

            conn.commit()
            logger.info(f"[insert_prices] 插入完成 | inserted={inserted} | skipped={skipped}")

        except Exception as e:
            logger.error(f"[insert_prices] 批量插入失败 | error={e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

        return {"inserted": inserted, "skipped": skipped}

    def get_latest(self, date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """
        获取最新价格数据

        Args:
            date: 指定日期 (YYYY-MM-DD)，None 则获取最新日期
            limit: 返回记录数

        Returns:
            Dict: 包含 success, count, prices 的字典
        """
        logger.info(f"[get_latest] 查询最新价格 | date={date} | limit={limit}")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if date:
                cursor.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = ?
                    ORDER BY CASE WHEN fetch_time LIKE '09%' THEN 1 ELSE 2 END, material_name, spec
                    LIMIT ?
                ''', (date, limit))
            else:
                cursor.execute('''
                    SELECT date, fetch_time, material_name, spec, material_type, brand, price, region
                    FROM rebar_prices
                    WHERE date = (SELECT MAX(date) FROM rebar_prices)
                    ORDER BY CASE WHEN fetch_time LIKE '09%' THEN 1 ELSE 2 END, material_name, spec
                    LIMIT ?
                ''', (limit,))

            rows = cursor.fetchall()
            conn.close()

            result = {
                'success': True,
                'count': len(rows),
                'prices': [dict(row) for row in rows]
            }
            logger.info(f"[get_latest] 查询完成 | count={len(rows)}")

            return result

        except Exception as e:
            logger.error(f"[get_latest] 查询失败 | error={e}", exc_info=True)
            if conn:
                conn.close()
            raise

    def get_by_range(
        self,
        start_date: str,
        end_date: str,
        material: Optional[str] = None,
        spec: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取日期范围内的价格数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            material: 品名筛选 (可选)
            spec: 规格筛选 (可选)

        Returns:
            Dict: 包含 success, start_date, end_date, total_count, dates_count, data 的字典
        """
        logger.info(f"[get_by_range] 查询日期范围 | start={start_date} | end={end_date} | material={material} | spec={spec}")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            sql = '''
                SELECT date, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date BETWEEN ? AND ?
            '''
            params: List[Any] = [start_date, end_date]

            if material:
                sql += ' AND material_name LIKE ?'
                params.append(f'%{material}%')

            if spec:
                sql += ' AND spec LIKE ?'
                params.append(f'%{spec}%')

            sql += ' ORDER BY date, material_name, spec'

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

            # 按日期分组
            dates_data: Dict[str, List[Dict]] = {}
            for row in rows:
                d = dict(row)
                date_str = d['date']
                if date_str not in dates_data:
                    dates_data[date_str] = []
                dates_data[date_str].append(d)

            result = {
                'success': True,
                'start_date': start_date,
                'end_date': end_date,
                'total_count': len(rows),
                'dates_count': len(dates_data),
                'data': dates_data
            }
            logger.info(f"[get_by_range] 查询完成 | total={len(rows)} | dates={len(dates_data)}")

            return result

        except Exception as e:
            logger.error(f"[get_by_range] 查询失败 | error={e}", exc_info=True)
            if conn:
                conn.close()
            raise

    def get_trend(
        self,
        material: Optional[str] = None,
        spec: Optional[str] = None,
        days: int = 365,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取价格趋势数据

        Args:
            material: 品名筛选 (可选)
            spec: 规格筛选 (可选)
            days: 天数 (默认365天)
            start_date: 开始日期 (YYYY-MM-DD) (可选)
            end_date: 结束日期 (YYYY-MM-DD) (可选)

        Returns:
            Dict: 包含 success, count, data 的字典
        """
        logger.info(f"[get_trend] 查询趋势 | material={material} | spec={spec} | days={days}")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            sql = '''
                SELECT date, AVG(price) as avg_price, MIN(price) as min_price,
                       MAX(price) as max_price, COUNT(*) as cnt
                FROM rebar_prices
                WHERE 1=1
            '''
            params: List[Any] = []

            if material:
                sql += ' AND material_name LIKE ?'
                params.append(f'%{material}%')

            if spec:
                sql += ' AND spec LIKE ?'
                params.append(f'%{spec}%')

            if start_date:
                sql += ' AND date >= ?'
                params.append(start_date)
            elif end_date:
                cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                sql += ' AND date >= ?'
                params.append(cutoff)

            if end_date:
                sql += ' AND date <= ?'
                params.append(end_date)

            sql += ' GROUP BY date ORDER BY date'

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

            result = {
                'success': True,
                'count': len(rows),
                'data': [dict(row) for row in rows]
            }
            logger.info(f"[get_trend] 查询完成 | count={len(rows)}")

            return result

        except Exception as e:
            logger.error(f"[get_trend] 查询失败 | error={e}", exc_info=True)
            if conn:
                conn.close()
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            Dict: 包含 total_count, dates_count, date_range, materials, specs 的字典
        """
        logger.info("[get_stats] 查询统计信息")

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # 总记录数
            cursor.execute('SELECT COUNT(*) FROM rebar_prices')
            total = cursor.fetchone()[0]

            # 日期数
            cursor.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
            dates = cursor.fetchone()[0]

            # 日期范围
            cursor.execute('SELECT MIN(date), MAX(date) FROM rebar_prices')
            range_row = cursor.fetchone()

            # 材料统计
            cursor.execute('SELECT material_name, COUNT(*) as cnt FROM rebar_prices GROUP BY material_name ORDER BY cnt DESC')
            materials = {row[0]: row[1] for row in cursor.fetchall()}

            # 规格统计
            cursor.execute('SELECT spec, COUNT(*) as cnt FROM rebar_prices GROUP BY spec ORDER BY cnt DESC LIMIT 20')
            specs = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            result = {
                'total_count': total,
                'dates_count': dates,
                'date_range': {'start': range_row[0], 'end': range_row[1]},
                'materials': materials,
                'specs': specs
            }
            logger.info(f"[get_stats] 查询完成 | total={total} | dates={dates}")

            return result

        except Exception as e:
            logger.error(f"[get_stats] 查询失败 | error={e}", exc_info=True)
            if conn:
                conn.close()
            raise


# 便捷函数 - 兼容旧接口
def insert_prices(prices: List[Dict[str, Any]]) -> Dict[str, int]:
    """批量插入价格数据（便捷函数）"""
    service = YantaiDBService()
    return service.insert_prices(prices)


def get_latest(date: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """获取最新价格（便捷函数）"""
    service = YantaiDBService()
    return service.get_latest(date, limit)


def get_by_range(
    start_date: str,
    end_date: str,
    material: Optional[str] = None,
    spec: Optional[str] = None
) -> Dict[str, Any]:
    """获取日期范围数据（便捷函数）"""
    service = YantaiDBService()
    return service.get_by_range(start_date, end_date, material, spec)


def get_trend(
    material: Optional[str] = None,
    spec: Optional[str] = None,
    days: int = 365,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """获取价格趋势（便捷函数）"""
    service = YantaiDBService()
    return service.get_trend(material, spec, days, start_date, end_date)


def get_stats() -> Dict[str, Any]:
    """获取统计信息（便捷函数）"""
    service = YantaiDBService()
    return service.get_stats()