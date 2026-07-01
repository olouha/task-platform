"""
指标库本地服务 - 使用SQLite
替代Supabase版本，用于腾讯云Windows部署
"""
import logging
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent / 'data' / 'yantai_rebar.db'


class LocalIndicatorService:
    """本地指标库服务"""

    def __init__(self, db_file: str = None):
        self.db_file = db_file or str(DB_FILE)
        self._init_table()

    def _init_table(self):
        """初始化指标库表"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 创建主表（完整字段 - 扩展版本）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicator_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                location TEXT,
                structure TEXT,
                floor_above INTEGER,
                floor_below INTEGER,
                area_total REAL,
                area_above REAL,
                area_below REAL,
                height REAL,
                complete_date TEXT,
                unit_cost REAL,
                total_cost REAL,
                unit_structure REAL,
                unit_installation REAL,
                unit_decoration REAL,
                unit_measure REAL,
                -- 主要经济指标
                underground_structure REAL,
                above_structure REAL,
                roof REAL,
                exterior_wall REAL,
                interior_wall REAL,
                floor REAL,
                electrical REAL,
                plumbing REAL,
                hvac REAL,
                elevator REAL,
                fire REAL,
                measures REAL,
                -- 材料含量
                steel REAL,
                concrete REAL,
                formwork REAL,
                block REAL,
                cable REAL,
                pipe REAL,
                duct REAL,
                -- ================== 新增字段 ==================
                -- 项目时间信息
                start_date TEXT,
                end_date TEXT,
                entry_date TEXT,
                -- 交付与基础信息
                delivery_type TEXT,
                foundation_type TEXT,
                -- 地上/地下造价分解
                cost_underground_structure REAL,
                cost_underground_installation REAL,
                unit_cost_underground_structure REAL,
                unit_cost_underground_installation REAL,
                cost_above_structure REAL,
                cost_above_installation REAL,
                unit_cost_above_structure REAL,
                unit_cost_above_installation REAL,
                -- 措施费与室外
                cost_measures REAL,
                unit_cost_measures REAL,
                cost_outdoor REAL,
                unit_cost_outdoor REAL,
                -- 专项工程造价（8组）
                cost_pile REAL,
                unit_cost_pile REAL,
                cost_foundation_support REAL,
                unit_cost_foundation_support REAL,
                cost_curtain_wall REAL,
                unit_cost_curtain_wall REAL,
                cost_decoration REAL,
                unit_cost_decoration REAL,
                cost_exterior_insulation REAL,
                unit_cost_exterior_insulation REAL,
                cost_exterior_windows REAL,
                unit_cost_exterior_windows REAL,
                cost_water_drainage REAL,
                unit_cost_water_drainage REAL,
                cost_heating REAL,
                unit_cost_heating REAL,
                cost_electrical REAL,
                unit_cost_electrical REAL,
                cost_hvac REAL,
                unit_cost_hvac REAL,
                -- 地上主体材料
                above_concrete REAL,
                above_concrete_unit REAL,
                above_rebar REAL,
                above_rebar_unit REAL,
                above_formwork REAL,
                above_formwork_unit REAL,
                -- 地下主体材料
                underground_concrete REAL,
                underground_concrete_unit REAL,
                underground_rebar REAL,
                underground_rebar_unit REAL,
                underground_formwork REAL,
                underground_formwork_unit REAL,
                -- 来源信息
                source TEXT,
                source_file TEXT,
                remarks TEXT,
                verified INTEGER DEFAULT 0,
                verified_by TEXT,
                verified_at TEXT,
                -- 时间戳
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # 迁移旧表数据（如果存在且缺少字段）
        self._migrate_old_table(conn)

        conn.commit()
        conn.close()
        logger.info("[LocalIndicatorService] 表初始化完成")

    def _migrate_old_table(self, conn):
        """迁移旧表，添加缺失的字段"""
        cursor = conn.cursor()
        logger.info("[LocalIndicatorService] 开始数据库迁移检查")

        # 需要添加的字段及默认值
        new_columns = {
            # 时间信息
            'start_date': 'TEXT',
            'end_date': 'TEXT',
            'entry_date': 'TEXT',
            # 交付与基础
            'delivery_type': 'TEXT',
            'foundation_type': 'TEXT',
            # 造价分解
            'cost_underground_structure': 'REAL',
            'cost_underground_installation': 'REAL',
            'unit_cost_underground_structure': 'REAL',
            'unit_cost_underground_installation': 'REAL',
            'cost_above_structure': 'REAL',
            'cost_above_installation': 'REAL',
            'unit_cost_above_structure': 'REAL',
            'unit_cost_above_installation': 'REAL',
            # 措施费与室外
            'cost_measures': 'REAL',
            'unit_cost_measures': 'REAL',
            'cost_outdoor': 'REAL',
            'unit_cost_outdoor': 'REAL',
            # 专项工程（16个字段）
            'cost_pile': 'REAL',
            'unit_cost_pile': 'REAL',
            'cost_foundation_support': 'REAL',
            'unit_cost_foundation_support': 'REAL',
            'cost_curtain_wall': 'REAL',
            'unit_cost_curtain_wall': 'REAL',
            'cost_decoration': 'REAL',
            'unit_cost_decoration': 'REAL',
            'cost_exterior_insulation': 'REAL',
            'unit_cost_exterior_insulation': 'REAL',
            'cost_exterior_windows': 'REAL',
            'unit_cost_exterior_windows': 'REAL',
            'cost_water_drainage': 'REAL',
            'unit_cost_water_drainage': 'REAL',
            'cost_heating': 'REAL',
            'unit_cost_heating': 'REAL',
            'cost_electrical': 'REAL',
            'unit_cost_electrical': 'REAL',
            'cost_hvac': 'REAL',
            'unit_cost_hvac': 'REAL',
            # 地上主体材料
            'above_concrete': 'REAL',
            'above_concrete_unit': 'REAL',
            'above_rebar': 'REAL',
            'above_rebar_unit': 'REAL',
            'above_formwork': 'REAL',
            'above_formwork_unit': 'REAL',
            # 地下主体材料
            'underground_concrete': 'REAL',
            'underground_concrete_unit': 'REAL',
            'underground_rebar': 'REAL',
            'underground_rebar_unit': 'REAL',
            'underground_formwork': 'REAL',
            'underground_formwork_unit': 'REAL',
        }

        # 获取当前表的所有列
        cursor.execute("PRAGMA table_info(indicator_projects)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"[LocalIndicatorService] 现有字段数量={len(existing_columns)}")

        # 添加缺失的列
        added_count = 0
        for col, col_type in new_columns.items():
            if col not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE indicator_projects ADD COLUMN {col} {col_type}")
                    logger.info(f"[LocalIndicatorService] 添加字段 {col}:{col_type}")
                    added_count += 1
                except sqlite3.OperationalError as e:
                    logger.warning(f"[LocalIndicatorService] 添加字段失败 {col}: {e}")

        logger.info(f"[LocalIndicatorService] 迁移完成 | 新增字段={added_count}")

    def get_indicator_projects(self, limit: int = 100, category: str = None, location: str = None) -> List[Dict]:
        """获取指标库项目列表"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM indicator_projects WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)
        if location:
            query += ' AND location = ?'
            params.append(location)

        query += ' ORDER BY updated_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        projects = [dict(row) for row in rows]
        conn.close()

        logger.info(f"[get_indicator_projects] 查询完成 | 结果数={len(projects)}")
        return projects

    def get_indicator_project(self, project_id: str) -> Optional[Dict]:
        """获取单个指标库项目"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM indicator_projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()

        conn.close()

        return dict(row) if row else None

    def create_indicator_project(self, project: Dict) -> Optional[Dict]:
        """创建指标库项目"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        project_id = project.get('id') or f"IND-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().isoformat()

        try:
            # 所有字段列表
            all_fields = [
                'id', 'name', 'category', 'location', 'structure',
                'floor_above', 'floor_below', 'area_total', 'area_above', 'area_below',
                'height', 'complete_date', 'unit_cost', 'total_cost',
                'unit_structure', 'unit_installation', 'unit_decoration', 'unit_measure',
                'underground_structure', 'above_structure', 'roof', 'exterior_wall',
                'interior_wall', 'floor', 'electrical', 'plumbing', 'hvac',
                'elevator', 'fire', 'measures',
                'steel', 'concrete', 'formwork', 'block', 'cable', 'pipe', 'duct',
                # 新增字段
                'start_date', 'end_date', 'entry_date',
                'delivery_type', 'foundation_type',
                'cost_underground_structure', 'cost_underground_installation',
                'unit_cost_underground_structure', 'unit_cost_underground_installation',
                'cost_above_structure', 'cost_above_installation',
                'unit_cost_above_structure', 'unit_cost_above_installation',
                'cost_measures', 'unit_cost_measures', 'cost_outdoor', 'unit_cost_outdoor',
                'cost_pile', 'unit_cost_pile',
                'cost_foundation_support', 'unit_cost_foundation_support',
                'cost_curtain_wall', 'unit_cost_curtain_wall',
                'cost_decoration', 'unit_cost_decoration',
                'cost_exterior_insulation', 'unit_cost_exterior_insulation',
                'cost_exterior_windows', 'unit_cost_exterior_windows',
                'cost_water_drainage', 'unit_cost_water_drainage',
                'cost_heating', 'unit_cost_heating',
                'cost_electrical', 'unit_cost_electrical',
                'cost_hvac', 'unit_cost_hvac',
                'above_concrete', 'above_concrete_unit',
                'above_rebar', 'above_rebar_unit',
                'above_formwork', 'above_formwork_unit',
                'underground_concrete', 'underground_concrete_unit',
                'underground_rebar', 'underground_rebar_unit',
                'underground_formwork', 'underground_formwork_unit',
                'source', 'source_file', 'remarks', 'verified', 'verified_by', 'verified_at',
                'created_at', 'updated_at'
            ]

            # 构建INSERT语句
            fields = [f for f in all_fields if f in project or f in ('id', 'created_at', 'updated_at')]
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)

            values = []
            for f in fields:
                if f == 'id':
                    values.append(project_id)
                elif f == 'created_at' or f == 'updated_at':
                    values.append(now)
                else:
                    values.append(project.get(f))

            cursor.execute(f'''
                INSERT INTO indicator_projects ({field_names})
                VALUES ({placeholders})
            ''', values)

            conn.commit()
            logger.info(f"[create_indicator_project] 创建成功 | id={project_id}")

            return self.get_indicator_project(project_id)

        except sqlite3.IntegrityError:
            logger.warning(f"[create_indicator_project] ID已存在 | {project_id}")
            conn.close()
            return None
        except Exception as e:
            logger.error(f"[create_indicator_project] 创建失败 | {e}", exc_info=True)
            conn.close()
            return None

    def update_indicator_project(self, project_id: str, project: Dict) -> bool:
        """更新指标库项目"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # 所有可更新的字段
        all_fields = [
            'name', 'category', 'location', 'structure',
            'floor_above', 'floor_below', 'area_total', 'area_above', 'area_below',
            'height', 'complete_date', 'unit_cost', 'total_cost',
            'unit_structure', 'unit_installation', 'unit_decoration', 'unit_measure',
            'underground_structure', 'above_structure', 'roof', 'exterior_wall',
            'interior_wall', 'floor', 'electrical', 'plumbing', 'hvac',
            'elevator', 'fire', 'measures',
            'steel', 'concrete', 'formwork', 'block', 'cable', 'pipe', 'duct',
            # 新增字段
            'start_date', 'end_date', 'entry_date',
            'delivery_type', 'foundation_type',
            'cost_underground_structure', 'cost_underground_installation',
            'unit_cost_underground_structure', 'unit_cost_underground_installation',
            'cost_above_structure', 'cost_above_installation',
            'unit_cost_above_structure', 'unit_cost_above_installation',
            'cost_measures', 'unit_cost_measures', 'cost_outdoor', 'unit_cost_outdoor',
            'cost_pile', 'unit_cost_pile',
            'cost_foundation_support', 'unit_cost_foundation_support',
            'cost_curtain_wall', 'unit_cost_curtain_wall',
            'cost_decoration', 'unit_cost_decoration',
            'cost_exterior_insulation', 'unit_cost_exterior_insulation',
            'cost_exterior_windows', 'unit_cost_exterior_windows',
            'cost_water_drainage', 'unit_cost_water_drainage',
            'cost_heating', 'unit_cost_heating',
            'cost_electrical', 'unit_cost_electrical',
            'cost_hvac', 'unit_cost_hvac',
            'above_concrete', 'above_concrete_unit',
            'above_rebar', 'above_rebar_unit',
            'above_formwork', 'above_formwork_unit',
            'underground_concrete', 'underground_concrete_unit',
            'underground_rebar', 'underground_rebar_unit',
            'underground_formwork', 'underground_formwork_unit',
            'source', 'source_file', 'remarks', 'verified', 'verified_by', 'verified_at'
        ]

        update_fields = []
        params = []

        for field in all_fields:
            if field in project:
                update_fields.append(f'{field} = ?')
                params.append(project[field])

        if not update_fields:
            conn.close()
            return False

        params.extend([now, project_id])

        query = f"UPDATE indicator_projects SET {', '.join(update_fields)}, updated_at = ? WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()

        if success:
            logger.info(f"[update_indicator_project] 更新成功 | id={project_id}")
        else:
            logger.warning(f"[update_indicator_project] 项目不存在 | id={project_id}")

        return success

    def delete_indicator_project(self, project_id: str) -> bool:
        """删除指标库项目"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM indicator_projects WHERE id = ?', (project_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()

        if success:
            logger.info(f"[delete_indicator_project] 删除成功 | id={project_id}")
        else:
            logger.warning(f"[delete_indicator_project] 项目不存在 | id={project_id}")

        return success

    def import_indicator_projects(self, projects: List[Dict]) -> Dict:
        """批量导入指标库项目"""
        imported = 0
        errors = []

        for project in projects:
            try:
                result = self.create_indicator_project(project)
                if result:
                    imported += 1
                else:
                    errors.append(f"{project.get('name')}: 导入失败")
            except Exception as e:
                errors.append(f"{project.get('name')}: {str(e)}")

        logger.info(f"[import_indicator_projects] 导入完成 | 成功={imported}, 总数={len(projects)}")

        return {
            "imported": imported,
            "total": len(projects),
            "errors": errors
        }

    def get_stats(self) -> Dict:
        """获取指标库统计信息"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM indicator_projects')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT category, COUNT(*) FROM indicator_projects GROUP BY category')
        by_category = dict(cursor.fetchall())

        cursor.execute('SELECT location, COUNT(*) FROM indicator_projects GROUP BY location')
        by_location = dict(cursor.fetchall())

        conn.close()

        return {
            "total": total,
            "by_category": by_category,
            "by_location": by_location
        }


# 全局实例
_indicator_service = None

def get_indicator_service() -> LocalIndicatorService:
    """获取指标库服务实例"""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = LocalIndicatorService()
    return _indicator_service
