"""
材料管理数据库服务（本地 SQLite）
提供材料分类、材料的增删改查功能

参照 services/price/yantai_db_service.py 的连接模式：
- 绝对路径 DB_FILE
- row_factory = sqlite3.Row
- init_db 初始化表并写入种子数据
"""
import sqlite3
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# 数据库文件路径（绝对路径）
DB_FILE = Path(__file__).parent.parent / 'data' / 'materials.db'


def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接

    Returns:
        sqlite3.Connection: 数据库连接对象（row_factory=sqlite3.Row 支持列名访问）
    """
    logger.debug(f"[get_db_connection] 连接数据库 | db={DB_FILE}")
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# 种子数据（首次初始化时写入，避免页面空白）
_SEED_CATEGORIES = [
    {"id": "1", "name": "钢筋类", "icon": "🔩", "color": "#16325C", "sort_order": 1},
    {"id": "2", "name": "混凝土类", "icon": "🧱", "color": "#EF4444", "sort_order": 2},
    {"id": "3", "name": "金属类", "icon": "🔧", "color": "#F59E0B", "sort_order": 3},
    {"id": "4", "name": "有色金属类", "icon": "🪙", "color": "#8B5CF6", "sort_order": 4},
]

_SEED_MATERIALS = [
    {"id": "1", "category_id": "1", "name": "HRB400螺纹钢筋", "spec": "12-25mm", "unit": "吨", "base_price": 4500, "source": "我的钢铁网"},
    {"id": "2", "category_id": "1", "name": "HPB300光圆钢筋", "spec": "8-10mm", "unit": "吨", "base_price": 4600, "source": "我的钢铁网"},
    {"id": "3", "category_id": "1", "name": "钢绞线", "spec": "15.2mm", "unit": "吨", "base_price": 5200, "source": "我的钢铁网"},
    {"id": "4", "category_id": "2", "name": "C30混凝土", "spec": "普通", "unit": "m³", "base_price": 580, "source": "我的钢铁网"},
    {"id": "5", "category_id": "2", "name": "C35混凝土", "spec": "普通", "unit": "m³", "base_price": 610, "source": "我的钢铁网"},
    {"id": "6", "category_id": "4", "name": "铝锭", "spec": "A00", "unit": "吨", "base_price": 18500, "source": "有色金属网"},
    {"id": "7", "category_id": "4", "name": "铜锭", "spec": "1#电解铜", "unit": "吨", "base_price": 68000, "source": "有色金属网"},
]


def init_db() -> None:
    """
    初始化数据库表并写入种子数据

    Creates:
        material_categories 表 - 材料分类
        materials 表 - 材料
    """
    logger.info("[init_db] 开始初始化材料数据库")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS material_categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT,
                color TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY,
                category_id TEXT,
                name TEXT NOT NULL,
                spec TEXT,
                unit TEXT,
                base_price REAL,
                source TEXT,
                source_id TEXT,
                is_adjusted INTEGER DEFAULT 1,
                adjustment_threshold REAL DEFAULT 5.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category_id)')

        # 首次为空时写入种子数据
        cursor.execute('SELECT COUNT(*) FROM material_categories')
        if cursor.fetchone()[0] == 0:
            for c in _SEED_CATEGORIES:
                cursor.execute(
                    'INSERT INTO material_categories (id, name, icon, color, sort_order) VALUES (?, ?, ?, ?, ?)',
                    (c["id"], c["name"], c["icon"], c["color"], c["sort_order"])
                )
            logger.info(f"[init_db] 写入种子分类 | count={len(_SEED_CATEGORIES)}")

        cursor.execute('SELECT COUNT(*) FROM materials')
        if cursor.fetchone()[0] == 0:
            for m in _SEED_MATERIALS:
                cursor.execute(
                    '''INSERT INTO materials
                       (id, category_id, name, spec, unit, base_price, source)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (m["id"], m["category_id"], m["name"], m["spec"], m["unit"], m["base_price"], m["source"])
                )
            logger.info(f"[init_db] 写入种子材料 | count={len(_SEED_MATERIALS)}")

        conn.commit()
        logger.info("[init_db] 材料数据库初始化完成")

    except Exception as e:
        logger.error(f"[init_db] 初始化失败 | error={e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


class MaterialsDBService:
    """材料管理数据库服务类"""

    def __init__(self, db_file: Optional[Path] = None):
        """初始化服务并确保表存在"""
        self.db_file = db_file or DB_FILE
        logger.info(f"[MaterialsDBService] 初始化 | db={self.db_file}")
        init_db()

    # ---------------- 分类 ----------------

    def list_categories(self) -> List[Dict[str, Any]]:
        """查询所有分类，附带每个分类下的材料数量 count"""
        logger.info("[list_categories] 查询所有分类")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT c.id, c.name, c.icon, c.color, c.sort_order,
                       (SELECT COUNT(*) FROM materials m WHERE m.category_id = c.id) AS count
                FROM material_categories c
                ORDER BY c.sort_order, c.name
            ''')
            rows = [dict(r) for r in cursor.fetchall()]
            logger.info(f"[list_categories] 查询完成 | count={len(rows)}")
            return rows
        except Exception as e:
            logger.error(f"[list_categories] 查询失败 | {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """获取单个分类"""
        logger.info(f"[get_category] 查询分类 | category_id={category_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, name, icon, color, sort_order FROM material_categories WHERE id = ?', (category_id,))
            row = cursor.fetchone()
            logger.info(f"[get_category] 查询完成 | found={row is not None}")
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[get_category] 查询失败 | {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def create_category(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建分类"""
        new_id = data.get("id") or str(uuid.uuid4())
        logger.info(f"[create_category] 创建分类 | id={new_id} | name={data.get('name')}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO material_categories (id, name, icon, color, sort_order) VALUES (?, ?, ?, ?, ?)',
                (new_id, data.get("name"), data.get("icon"), data.get("color"), data.get("sort_order", 0))
            )
            conn.commit()
            logger.info(f"[create_category] 创建成功 | id={new_id} | affected={cursor.rowcount}")
            return {**data, "id": new_id, "count": 0}
        except Exception as e:
            logger.error(f"[create_category] 创建失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_category(self, category_id: str, data: Dict[str, Any]) -> bool:
        """更新分类"""
        logger.info(f"[update_category] 更新分类 | category_id={category_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE material_categories SET name=?, icon=?, color=?, sort_order=? WHERE id=?',
                (data.get("name"), data.get("icon"), data.get("color"), data.get("sort_order", 0), category_id)
            )
            conn.commit()
            logger.info(f"[update_category] 更新完成 | affected={cursor.rowcount}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[update_category] 更新失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_category(self, category_id: str) -> bool:
        """删除分类"""
        logger.info(f"[delete_category] 删除分类 | category_id={category_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM material_categories WHERE id=?', (category_id,))
            conn.commit()
            logger.info(f"[delete_category] 删除完成 | affected={cursor.rowcount}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[delete_category] 删除失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------------- 材料 ----------------

    def list_materials(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询材料（可按分类过滤），附带分类名称 category"""
        logger.info(f"[list_materials] 查询材料 | category_id={category_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            sql = '''
                SELECT m.id, m.category_id, c.name AS category, m.name, m.spec, m.unit,
                       m.base_price, m.source, m.source_id, m.is_adjusted, m.adjustment_threshold
                FROM materials m
                LEFT JOIN material_categories c ON m.category_id = c.id
            '''
            params: List[Any] = []
            if category_id:
                sql += ' WHERE m.category_id = ?'
                params.append(category_id)
            sql += ' ORDER BY m.category_id, m.name'
            cursor.execute(sql, params)
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                d["is_adjusted"] = bool(d.get("is_adjusted"))
                rows.append(d)
            logger.info(f"[list_materials] 查询完成 | count={len(rows)}")
            return rows
        except Exception as e:
            logger.error(f"[list_materials] 查询失败 | {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_material(self, material_id: str) -> Optional[Dict[str, Any]]:
        """获取单个材料"""
        logger.info(f"[get_material] 查询材料 | material_id={material_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT m.id, m.category_id, c.name AS category, m.name, m.spec, m.unit,
                       m.base_price, m.source, m.source_id, m.is_adjusted, m.adjustment_threshold
                FROM materials m
                LEFT JOIN material_categories c ON m.category_id = c.id
                WHERE m.id = ?
            ''', (material_id,))
            row = cursor.fetchone()
            logger.info(f"[get_material] 查询完成 | found={row is not None}")
            if not row:
                return None
            d = dict(row)
            d["is_adjusted"] = bool(d.get("is_adjusted"))
            return d
        except Exception as e:
            logger.error(f"[get_material] 查询失败 | {e}", exc_info=True)
            raise
        finally:
            conn.close()

    def create_material(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建材料"""
        new_id = data.get("id") or str(uuid.uuid4())
        logger.info(f"[create_material] 创建材料 | id={new_id} | name={data.get('name')}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO materials
                   (id, category_id, name, spec, unit, base_price, source, source_id, is_adjusted, adjustment_threshold)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    new_id, data.get("category_id"), data.get("name"), data.get("spec"),
                    data.get("unit"), data.get("base_price"), data.get("source"), data.get("source_id"),
                    1 if data.get("is_adjusted", True) else 0, data.get("adjustment_threshold", 5.0)
                )
            )
            conn.commit()
            logger.info(f"[create_material] 创建成功 | id={new_id} | affected={cursor.rowcount}")
            return self.get_material(new_id) or {**data, "id": new_id}
        except Exception as e:
            logger.error(f"[create_material] 创建失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_material(self, material_id: str, data: Dict[str, Any]) -> bool:
        """更新材料"""
        logger.info(f"[update_material] 更新材料 | material_id={material_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''UPDATE materials SET
                   category_id=?, name=?, spec=?, unit=?, base_price=?, source=?, source_id=?,
                   is_adjusted=?, adjustment_threshold=?
                   WHERE id=?''',
                (
                    data.get("category_id"), data.get("name"), data.get("spec"), data.get("unit"),
                    data.get("base_price"), data.get("source"), data.get("source_id"),
                    1 if data.get("is_adjusted", True) else 0, data.get("adjustment_threshold", 5.0),
                    material_id
                )
            )
            conn.commit()
            logger.info(f"[update_material] 更新完成 | affected={cursor.rowcount}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[update_material] 更新失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_material_price(self, material_id: str, base_price: float) -> bool:
        """更新材料基准价"""
        logger.info(f"[update_material_price] 更新价格 | material_id={material_id} | base_price={base_price}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('UPDATE materials SET base_price=? WHERE id=?', (base_price, material_id))
            conn.commit()
            logger.info(f"[update_material_price] 更新完成 | affected={cursor.rowcount}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[update_material_price] 更新失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_material(self, material_id: str) -> bool:
        """删除材料"""
        logger.info(f"[delete_material] 删除材料 | material_id={material_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM materials WHERE id=?', (material_id,))
            conn.commit()
            logger.info(f"[delete_material] 删除完成 | affected={cursor.rowcount}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[delete_material] 删除失败 | {e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()
