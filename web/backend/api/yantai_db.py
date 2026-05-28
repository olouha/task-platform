"""
山东烟台钢筋价格数据库API
使用SQLite数据库提供价格查询接口
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sqlite3
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

DB_FILE = 'services/data/yantai_rebar.db'


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


class PriceRecord(BaseModel):
    date: str
    material_name: str
    spec: str
    material_type: str
    brand: str
    price: int
    region: str = '山东烟台'


class PriceSummary(BaseModel):
    total_count: int
    dates_count: int
    date_range: dict
    materials: dict
    specs: dict


@router.get("/stats", response_model=PriceSummary)
async def get_stats():
    """获取数据库统计信息"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 总记录数
        c.execute('SELECT COUNT(*) FROM rebar_prices')
        total = c.fetchone()[0]

        # 日期数
        c.execute('SELECT COUNT(DISTINCT date) FROM rebar_prices')
        dates = c.fetchone()[0]

        # 日期范围
        c.execute('SELECT MIN(date), MAX(date) FROM rebar_prices')
        range_row = c.fetchone()

        # 材料统计
        c.execute('SELECT material_name, COUNT(*) as cnt FROM rebar_prices GROUP BY material_name ORDER BY cnt DESC')
        materials = {row[0]: row[1] for row in c.fetchall()}

        # 规格统计
        c.execute('SELECT spec, COUNT(*) as cnt FROM rebar_prices GROUP BY spec ORDER BY cnt DESC LIMIT 20')
        specs = {row[0]: row[1] for row in c.fetchall()}

        conn.close()

        return PriceSummary(
            total_count=total,
            dates_count=dates,
            date_range={'start': range_row[0], 'end': range_row[1]},
            materials=materials,
            specs=specs
        )
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    date: str = Query(None, description="指定日期 (YYYY-MM-DD)"),
    limit: int = Query(50, description="返回记录数")
):
    """获取最新价格数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if date:
            c.execute('''
                SELECT date, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = ?
                ORDER BY material_name, spec
                LIMIT ?
            ''', (date, limit))
        else:
            c.execute('''
                SELECT date, material_name, spec, material_type, brand, price, region
                FROM rebar_prices
                WHERE date = (SELECT MAX(date) FROM rebar_prices)
                ORDER BY material_name, spec
                LIMIT ?
            ''', (limit,))

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'count': len(rows),
            'prices': [dict(row) for row in rows]
        }
    except Exception as e:
        logger.error(f"获取最新价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/range")
async def get_by_range(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    material: str = Query(None, description="品名筛选"),
    spec: str = Query(None, description="规格筛选")
):
    """获取日期范围内的价格数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, material_name, spec, material_type, brand, price, region
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

        sql += ' ORDER BY date, material_name, spec'

        c.execute(sql, params)
        rows = c.fetchall()

        # 按日期分组
        dates_data = {}
        for row in rows:
            d = dict(row)
            date_str = d['date']
            if date_str not in dates_data:
                dates_data[date_str] = []
            dates_data[date_str].append(d)

        conn.close()

        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'total_count': len(rows),
            'dates_count': len(dates_data),
            'data': dates_data
        }
    except Exception as e:
        logger.error(f"获取日期范围数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_trend(
    material: str = Query(None, description="品名"),
    spec: str = Query(None, description="规格"),
    days: int = Query(365, description="天数"),
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """获取价格趋势数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 构建查询条件
        sql = '''
            SELECT date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price, COUNT(*) as cnt
            FROM rebar_prices
            WHERE 1=1
        '''
        params = []

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

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'count': len(rows),
            'data': [dict(row) for row in rows]
        }
    except Exception as e:
        logger.error(f"获取趋势数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/materials")
async def get_materials():
    """获取所有品名类型"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('''
            SELECT DISTINCT material_name, COUNT(*) as cnt
            FROM rebar_prices
            GROUP BY material_name
            ORDER BY cnt DESC
        ''')

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'materials': [{'name': row[0], 'count': row[1]} for row in rows]
        }
    except Exception as e:
        logger.error(f"获取品名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/specs")
async def get_specs(material: str = Query(None, description="品名筛选")):
    """获取所有规格"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if material:
            c.execute('''
                SELECT DISTINCT spec, COUNT(*) as cnt
                FROM rebar_prices
                WHERE material_name LIKE ?
                GROUP BY spec
                ORDER BY cnt DESC
            ''', (f'%{material}%',))
        else:
            c.execute('''
                SELECT DISTINCT spec, COUNT(*) as cnt
                FROM rebar_prices
                GROUP BY spec
                ORDER BY cnt DESC
            ''')

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'specs': [{'spec': row[0], 'count': row[1]} for row in rows]
        }
    except Exception as e:
        logger.error(f"获取规格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dates")
async def get_available_dates(
    start_date: str = Query(None, description="开始日期"),
    end_date: str = Query(None, description="结束日期")
):
    """获取所有可用日期"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        if start_date and end_date:
            c.execute('''
                SELECT DISTINCT date FROM rebar_prices
                WHERE date BETWEEN ? AND ?
                ORDER BY date
            ''', (start_date, end_date))
        elif start_date:
            c.execute('''
                SELECT DISTINCT date FROM rebar_prices
                WHERE date >= ?
                ORDER BY date
            ''', (start_date,))
        elif end_date:
            c.execute('''
                SELECT DISTINCT date FROM rebar_prices
                WHERE date <= ?
                ORDER BY date
            ''', (end_date,))
        else:
            c.execute('SELECT DISTINCT date FROM rebar_prices ORDER BY date')

        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'count': len(rows),
            'dates': [row[0] for row in rows]
        }
    except Exception as e:
        logger.error(f"获取日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_prices(
    keyword: str = Query(..., description="搜索关键词"),
    date: str = Query(None, description="指定日期"),
    limit: int = Query(100, description="返回数量")
):
    """搜索价格数据"""
    try:
        conn = get_db_connection()
        c = conn.cursor()

        sql = '''
            SELECT date, material_name, spec, material_type, brand, price, region
            FROM rebar_prices
            WHERE (material_name LIKE ? OR spec LIKE ? OR brand LIKE ? OR material_type LIKE ?)
        '''
        params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']

        if date:
            sql += ' AND date = ?'
            params.append(date)

        sql += ' ORDER BY date DESC, material_name, spec LIMIT ?'
        params.append(limit)

        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        return {
            'success': True,
            'count': len(rows),
            'keyword': keyword,
            'prices': [dict(row) for row in rows]
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))