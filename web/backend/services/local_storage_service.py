"""
本地 SQLite 存储服务
当 Supabase 不可用时使用本地数据库
"""

import os
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# 获取后端目录
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
DB_FILE = os.path.join(DATA_DIR, 'local_storage.db')


def get_db_connection():
    """获取数据库连接"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_local_db():
    """初始化本地数据库表"""
    conn = get_db_connection()
    c = conn.cursor()

    # 项目表
    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT,
            area REAL,
            structure_type TEXT,
            total_amount REAL,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # 项目材料表
    c.execute('''
        CREATE TABLE IF NOT EXISTS project_materials (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            quantity REAL,
            unit_price REAL,
            created_at TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    # 指标库表
    c.execute('''
        CREATE TABLE IF NOT EXISTS indicators (
            id TEXT PRIMARY KEY,
            code TEXT,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            specification TEXT,
            base_price REAL,
            price_source TEXT,
            region TEXT,
            effective_date TEXT,
            remarks TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    # 调差规则表
    c.execute('''
        CREATE TABLE IF NOT EXISTS adjustment_rules (
            id TEXT PRIMARY KEY,
            project_name TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            formula TEXT,
            base_price_source TEXT,
            config TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("[init_local_db] 本地数据库初始化完成")


class LocalStorageService:
    """本地存储服务"""

    def __init__(self):
        init_local_db()
        logger.info("[LocalStorageService] 初始化完成")

    def health_check(self) -> bool:
        """健康检查"""
        try:
            conn = get_db_connection()
            conn.execute('SELECT 1')
            conn.close()
            return True
        except:
            return False

    # ========== 项目管理 ==========

    def get_projects(self) -> List[Dict]:
        """获取所有项目"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM projects ORDER BY created_at DESC')
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取单个项目"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_project(self, data: Dict) -> Dict:
        """创建项目"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        # 生成 ID
        import uuid
        project_id = data.get('id') or str(uuid.uuid4())

        c.execute('''
            INSERT INTO projects (id, name, description, location, area, structure_type, total_amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            data.get('name', ''),
            data.get('description'),
            data.get('location'),
            data.get('area'),
            data.get('structure_type'),
            data.get('total_amount'),
            now,
            now
        ))
        conn.commit()
        conn.close()

        return {'id': project_id, 'success': True}

    def update_project(self, project_id: str, data: Dict) -> bool:
        """更新项目"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        c.execute('''
            UPDATE projects SET name=?, description=?, location=?, area=?, structure_type=?, total_amount=?, updated_at=?
            WHERE id=?
        ''', (
            data.get('name'),
            data.get('description'),
            data.get('location'),
            data.get('area'),
            data.get('structure_type'),
            data.get('total_amount'),
            now,
            project_id
        ))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM project_materials WHERE project_id = ?', (project_id,))
        c.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    # ========== 项目材料 ==========

    def get_project_materials(self, project_id: str) -> List[Dict]:
        """获取项目材料"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM project_materials WHERE project_id = ?', (project_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_project_material(self, project_id: str, data: Dict) -> Dict:
        """创建项目材料"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        import uuid
        material_id = data.get('id') or str(uuid.uuid4())

        c.execute('''
            INSERT INTO project_materials (id, project_id, name, category, unit, quantity, unit_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            material_id,
            project_id,
            data.get('name', ''),
            data.get('category'),
            data.get('unit'),
            data.get('quantity'),
            data.get('unit_price'),
            now
        ))
        conn.commit()
        conn.close()

        return {'id': material_id, 'success': True}

    def update_project_material(self, material_id: str, data: Dict) -> bool:
        """更新项目材料"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE project_materials SET name=?, category=?, unit=?, quantity=?, unit_price=?
            WHERE id=?
        ''', (
            data.get('name'),
            data.get('category'),
            data.get('unit'),
            data.get('quantity'),
            data.get('unit_price'),
            material_id
        ))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    def delete_project_material(self, material_id: str) -> bool:
        """删除项目材料"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM project_materials WHERE id = ?', (material_id,))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    # ========== 指标库 ==========

    def get_indicators(self, category: str = None) -> List[Dict]:
        """获取指标库"""
        conn = get_db_connection()
        c = conn.cursor()
        if category:
            c.execute('SELECT * FROM indicators WHERE category = ? ORDER BY code', (category,))
        else:
            c.execute('SELECT * FROM indicators ORDER BY category, code')
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def create_indicator(self, data: Dict) -> Dict:
        """创建指标"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        import uuid
        indicator_id = data.get('id') or str(uuid.uuid4())

        c.execute('''
            INSERT INTO indicators (id, code, name, category, unit, specification, base_price, price_source, region, effective_date, remarks, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            indicator_id,
            data.get('code'),
            data.get('name', ''),
            data.get('category'),
            data.get('unit'),
            data.get('specification'),
            data.get('base_price'),
            data.get('price_source'),
            data.get('region'),
            data.get('effective_date'),
            data.get('remarks'),
            now,
            now
        ))
        conn.commit()
        conn.close()

        return {'id': indicator_id, 'success': True}

    def update_indicator(self, indicator_id: str, data: Dict) -> bool:
        """更新指标"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        c.execute('''
            UPDATE indicators SET code=?, name=?, category=?, unit=?, specification=?, base_price=?, price_source=?, region=?, effective_date=?, remarks=?, updated_at=?
            WHERE id=?
        ''', (
            data.get('code'),
            data.get('name'),
            data.get('category'),
            data.get('unit'),
            data.get('specification'),
            data.get('base_price'),
            data.get('price_source'),
            data.get('region'),
            data.get('effective_date'),
            data.get('remarks'),
            now,
            indicator_id
        ))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    def delete_indicator(self, indicator_id: str) -> bool:
        """删除指标"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM indicators WHERE id = ?', (indicator_id,))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    # ========== 调差规则 ==========

    def get_adjustment_rules(self) -> List[Dict]:
        """获取调差规则"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM adjustment_rules ORDER BY created_at DESC')
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('config'):
                try:
                    d['config'] = json.loads(d['config'])
                except:
                    pass
            result.append(d)
        return result

    def create_adjustment_rule(self, data: Dict) -> Dict:
        """创建调差规则"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()

        import uuid
        rule_id = data.get('id') or str(uuid.uuid4())
        config = data.get('config')
        if config:
            config = json.dumps(config, ensure_ascii=False)

        c.execute('''
            INSERT INTO adjustment_rules (id, project_name, rule_name, formula, base_price_source, config, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule_id,
            data.get('project_name', ''),
            data.get('rule_name', ''),
            data.get('formula'),
            data.get('base_price_source'),
            config,
            now,
            now
        ))
        conn.commit()
        conn.close()

        return {'id': rule_id, 'success': True}

    def update_adjustment_rule(self, rule_id: str, data: Dict) -> bool:
        """更新调差规则"""
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        config = data.get('config')
        if config:
            config = json.dumps(config, ensure_ascii=False)

        c.execute('''
            UPDATE adjustment_rules SET project_name=?, rule_name=?, formula=?, base_price_source=?, config=?, updated_at=?
            WHERE id=?
        ''', (
            data.get('project_name'),
            data.get('rule_name'),
            data.get('formula'),
            data.get('base_price_source'),
            config,
            now,
            rule_id
        ))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0

    def delete_adjustment_rule(self, rule_id: str) -> bool:
        """删除调差规则"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM adjustment_rules WHERE id = ?', (rule_id,))
        conn.commit()
        affected = c.rowcount
        conn.close()
        return affected > 0