"""
指标库本地服务 - 使用SQLite
替代Supabase版本，用于腾讯云Windows部署
支持版本管理和历史追溯
"""
import logging
import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE = Path(__file__).parent / 'data' / 'yantai_rebar.db'

# 快照保留数量
MAX_SNAPSHOTS = 10


class LocalIndicatorService:
    """本地指标库服务 - 支持版本管理和历史追溯"""

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
                -- ================== 项目时间信息 ==================
                start_date TEXT,
                end_date TEXT,
                entry_date TEXT,
                -- ================== 交付与基础信息 ==================
                delivery_type TEXT,
                foundation_type TEXT,
                -- ================== 地上/地下造价分解 ==================
                cost_underground_structure REAL,
                cost_underground_installation REAL,
                unit_cost_underground_structure REAL,
                unit_cost_underground_installation REAL,
                cost_above_structure REAL,
                cost_above_installation REAL,
                unit_cost_above_structure REAL,
                unit_cost_above_installation REAL,
                -- ================== 措施费与室外 ==================
                cost_measures REAL,
                unit_cost_measures REAL,
                cost_outdoor REAL,
                unit_cost_outdoor REAL,
                -- ================== 专项工程造价（8组）====================
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
                -- ================== 地上主体材料 ==================
                above_concrete REAL,
                above_concrete_unit REAL,
                above_rebar REAL,
                above_rebar_unit REAL,
                above_formwork REAL,
                above_formwork_unit REAL,
                -- ================== 地下主体材料 ==================
                underground_concrete REAL,
                underground_concrete_unit REAL,
                underground_rebar REAL,
                underground_rebar_unit REAL,
                underground_formwork REAL,
                underground_formwork_unit REAL,
                -- ================== 来源信息 ==================
                source TEXT,
                source_file TEXT,
                remarks TEXT,
                verified INTEGER DEFAULT 0,
                verified_by TEXT,
                verified_at TEXT,
                -- ================== 版本管理字段 ==================
                version INTEGER DEFAULT 1,
                is_latest INTEGER DEFAULT 1,
                snapshot_id TEXT,
                -- ================== 时间戳 ==================
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        # 创建快照历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicator_snapshots (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                project_name TEXT NOT NULL,
                version INTEGER NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                filename TEXT,
                imported_by TEXT,
                UNIQUE(project_id, version)
            )
        ''')

        # 创建导入历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS import_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                total_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
                details TEXT
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
            # 版本管理字段
            'version': 'INTEGER DEFAULT 1',
            'is_latest': 'INTEGER DEFAULT 1',
            'snapshot_id': 'TEXT',
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

        # 获取版本信息
        cursor.execute('SELECT MAX(version) FROM indicator_projects WHERE is_latest = 1')
        max_version = cursor.fetchone()[0] or 1

        # 获取快照数量
        cursor.execute('SELECT COUNT(*) FROM indicator_snapshots')
        snapshot_count = cursor.fetchone()[0]

        conn.close()

        return {
            "total": total,
            "by_category": by_category,
            "by_location": by_location,
            "max_version": max_version,
            "snapshot_count": snapshot_count
        }

    # ==================== 版本管理 ====================

    def _save_snapshot(self, project_id: str, data: Dict, filename: str = None) -> str:
        """保存项目快照（入库前调用）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 获取当前版本号
        cursor.execute(
            'SELECT version FROM indicator_projects WHERE id = ?',
            (project_id,)
        )
        row = cursor.fetchone()
        current_version = row[0] if row else 0

        # 生成快照ID
        snapshot_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # 保存快照
        cursor.execute('''
            INSERT INTO indicator_snapshots (id, project_id, project_name, version, data, created_at, filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_id,
            project_id,
            data.get('name', ''),
            current_version,
            json.dumps(data, ensure_ascii=False),
            now,
            filename
        ))

        # 清理旧快照（只保留最近 MAX_SNAPSHOTS 个）
        cursor.execute('''
            DELETE FROM indicator_snapshots
            WHERE project_id = ? AND id NOT IN (
                SELECT id FROM indicator_snapshots
                WHERE project_id = ?
                ORDER BY version DESC
                LIMIT ?
            )
        ''', (project_id, project_id, MAX_SNAPSHOTS))

        conn.commit()
        conn.close()

        logger.info(f"[_save_snapshot] 保存快照 | project_id={project_id}, version={current_version}")
        return snapshot_id

    def get_version_history(self, project_id: str) -> List[Dict]:
        """获取项目版本历史"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, project_id, project_name, version, created_at, filename
            FROM indicator_snapshots
            WHERE project_id = ?
            ORDER BY version DESC
        ''', (project_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_snapshot_detail(self, snapshot_id: str) -> Optional[Dict]:
        """获取快照详情"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('SELECT data FROM indicator_snapshots WHERE id = ?', (snapshot_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """回滚到指定快照"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        try:
            # 获取快照数据
            cursor.execute('SELECT project_id, version, data FROM indicator_snapshots WHERE id = ?', (snapshot_id,))
            row = cursor.fetchone()

            if not row:
                conn.close()
                logger.warning(f"[rollback_to_snapshot] 快照不存在 | snapshot_id={snapshot_id}")
                return False

            project_id, snapshot_version, data_str = row
            data = json.loads(data_str)

            # 获取当前数据作为新快照
            cursor.execute('SELECT * FROM indicator_projects WHERE id = ?', (project_id,))
            current_row = cursor.fetchone()
            if current_row:
                current_data = {description[0]: current_row[i] for i, description in enumerate(cursor.description)}
                self._save_snapshot(project_id, current_data, f"rollback_backup_v{snapshot_version}")

            # 更新主表（使用快照数据，但生成新版本）
            cursor.execute('SELECT MAX(version) FROM indicator_projects WHERE id = ?', (project_id,))
            max_version = cursor.fetchone()[0] or 0
            new_version = max_version + 1

            now = datetime.now().isoformat()

            # 删除旧版本
            cursor.execute('DELETE FROM indicator_projects WHERE id = ?', (project_id,))

            # 插入快照数据（带新版本号）
            data['version'] = new_version
            data['is_latest'] = 1
            data['updated_at'] = now

            # 构建INSERT语句
            fields = list(data.keys())
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)
            values = [data.get(f) for f in fields]

            cursor.execute(f'''
                INSERT INTO indicator_projects ({field_names})
                VALUES ({placeholders})
            ''', values)

            conn.commit()
            conn.close()

            logger.info(f"[rollback_to_snapshot] 回滚成功 | project_id={project_id}, snapshot_version={snapshot_version}, new_version={new_version}")
            return True

        except Exception as e:
            conn.close()
            logger.error(f"[rollback_to_snapshot] 回滚失败 | {e}", exc_info=True)
            return False

    # ==================== 导入历史 ====================

    def record_import_history(
        self,
        filename: str,
        total_count: int,
        success_count: int,
        fail_count: int,
        details: List[Dict] = None
    ) -> int:
        """记录导入历史"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO import_history (filename, total_count, success_count, fail_count, details)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            filename,
            total_count,
            success_count,
            fail_count,
            json.dumps(details or [], ensure_ascii=False)
        ))

        import_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"[record_import_history] 记录导入 | filename={filename}, success={success_count}, fail={fail_count}")
        return import_id

    def get_import_history(self, limit: int = 50) -> List[Dict]:
        """获取导入历史列表"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, filename, total_count, success_count, fail_count, imported_at
            FROM import_history
            ORDER BY imported_at DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_import_detail(self, import_id: int) -> Optional[Dict]:
        """获取导入详情"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM import_history WHERE id = ?',
            (import_id,)
        )
        row = cursor.fetchone()

        conn.close()

        if row:
            return {
                'id': row[0],
                'filename': row[1],
                'total_count': row[2],
                'success_count': row[3],
                'fail_count': row[4],
                'imported_at': row[5],
                'details': json.loads(row[6]) if row[6] else []
            }
        return None

    # ==================== 数据一致性校验 ====================

    def sync_check(self) -> Dict[str, Any]:
        """前后端数据一致性校验"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 获取主表统计
        cursor.execute('SELECT COUNT(*) FROM indicator_projects')
        project_count = cursor.fetchone()[0]

        # 获取快照数量
        cursor.execute('SELECT COUNT(*) FROM indicator_snapshots')
        snapshot_count = cursor.fetchone()[0]

        # 获取最后更新时间
        cursor.execute('SELECT MAX(updated_at) FROM indicator_projects')
        last_update = cursor.fetchone()[0]

        # 获取导入历史数量
        cursor.execute('SELECT COUNT(*) FROM import_history')
        import_count = cursor.fetchone()[0]

        # 获取最后导入时间
        cursor.execute('SELECT MAX(imported_at) FROM import_history')
        last_import = cursor.fetchone()[0]

        # 获取最新版本号
        cursor.execute('SELECT MAX(version) FROM indicator_projects WHERE is_latest = 1')
        max_version = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'sqlite': {
                'project_count': project_count,
                'snapshot_count': snapshot_count,
                'import_count': import_count,
                'max_version': max_version
            },
            'last_update': last_update,
            'last_import': last_import,
            'in_sync': True  # SQLite 单机，无同步问题
        }

    # ==================== 自动导入（先校验后入库） ====================

    def auto_import_project(self, data: Dict, source_filename: str = None) -> Dict[str, Any]:
        """自动导入项目（校验通过直接入库，已存在则更新版本）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        try:
            project_name = data.get('name')
            if not project_name:
                return {'success': False, 'error': '项目名称不能为空'}

            # 检查是否已存在
            cursor.execute('SELECT id, version FROM indicator_projects WHERE name = ?', (project_name,))
            existing = cursor.fetchone()

            if existing:
                existing_id, current_version = existing

                # 保存当前版本快照
                cursor.execute('SELECT * FROM indicator_projects WHERE id = ?', (existing_id,))
                current_row = cursor.fetchone()
                if current_row:
                    current_data = {desc[0]: current_row[i] for i, desc in enumerate(cursor.description)}
                    self._save_snapshot(existing_id, current_data, source_filename)

                # 更新主表
                data['id'] = existing_id
                data['version'] = current_version + 1
                data['is_latest'] = 1
                data['updated_at'] = now
                # 自动审核
                data['verified'] = 1
                data['verified_by'] = '系统'
                data['verified_at'] = now

                # 删除旧记录
                cursor.execute('DELETE FROM indicator_projects WHERE id = ?', (existing_id,))

                logger.info(f"[auto_import_project] 更新项目 | name={project_name}, new_version={data['version']}")
            else:
                # 新增项目
                data['id'] = data.get('id') or f"IND-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
                data['version'] = 1
                data['is_latest'] = 1
                data['created_at'] = now
                data['updated_at'] = now
                data['entry_date'] = datetime.now().strftime('%Y-%m-%d')
                # 自动审核
                data['verified'] = 1
                data['verified_by'] = '系统'
                data['verified_at'] = now

                logger.info(f"[auto_import_project] 新增项目 | name={project_name}")

            # 获取表的实际列名（过滤掉 Excel 解析来的不存在于表的字段如 index）
            cursor.execute("PRAGMA table_info(indicator_projects)")
            table_cols = {row[1] for row in cursor.fetchall()}

            # 插入数据（字段名加双引号避免保留字冲突；跳过表中不存在的字段）
            fields = [f for f in data.keys() if f in table_cols]
            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(f'"{f}"' for f in fields)
            values = [data.get(f) for f in fields]

            cursor.execute(f'''
                INSERT INTO indicator_projects ({field_names})
                VALUES ({placeholders})
            ''', values)

            conn.commit()
            conn.close()

            return {
                'success': True,
                'id': data['id'],
                'version': data['version'],
                'is_update': existing is not None
            }

        except Exception as e:
            conn.close()
            logger.error(f"[auto_import_project] 导入失败 | {e}", exc_info=True)
            return {'success': False, 'error': str(e)}


# 全局实例
_indicator_service = None

def get_indicator_service() -> LocalIndicatorService:
    """获取指标库服务实例"""
    global _indicator_service
    if _indicator_service is None:
        _indicator_service = LocalIndicatorService()
    return _indicator_service
