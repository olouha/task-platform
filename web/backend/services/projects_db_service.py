"""
项目管理数据库服务（本地 SQLite）

用于老的「项目管理(Projects)」模块，替代已禁用的 Supabase 存储。
数据字段契约与前端 Projects.tsx 保持一致：
    id / name / description / created_at / status

注意：与「调差项目管理」(adjustment_projects) 是两套独立数据，互不影响。
"""
import sqlite3
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# 数据库文件路径（绝对路径）
# 本文件位于 services/ 下，parent.parent 即 backend/ 目录
DB_FILE = Path(__file__).resolve().parent.parent / 'data' / 'projects.db'


def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接

    Returns:
        sqlite3.Connection: 数据库连接对象，row_factory 设为 sqlite3.Row 以支持列名访问
    """
    logger.debug(f"[get_db_connection] 连接数据库 | db={DB_FILE}")
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    初始化数据库表

    Creates:
        projects 表 - 项目主表（字段契约对齐前端）
    """
    logger.info("[init_db] 开始初始化项目数据库")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at)')

        conn.commit()
        logger.info("[init_db] 项目数据库初始化完成")
    except Exception as e:
        logger.error(f"[init_db] 初始化失败 | error={e}", exc_info=True)
        raise
    finally:
        conn.close()


def list_projects() -> List[Dict[str, Any]]:
    """
    获取所有项目

    Returns:
        List[Dict]: 项目列表，按创建时间倒序
    """
    logger.info("[list_projects] 查询所有项目")

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, name, description, status, created_at
            FROM projects
            ORDER BY created_at DESC
        ''')
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        logger.info(f"[list_projects] 查询完成 | count={len(result)}")
        return result
    except Exception as e:
        logger.error(f"[list_projects] 查询失败 | error={e}", exc_info=True)
        raise
    finally:
        conn.close()


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    获取单个项目详情

    Args:
        project_id: 项目 ID

    Returns:
        Optional[Dict]: 项目字典，不存在返回 None
    """
    logger.info(f"[get_project] 查询项目 | project_id={project_id}")

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, name, description, status, created_at
            FROM projects
            WHERE id = ?
        ''', (project_id,))
        row = cursor.fetchone()
        result = dict(row) if row else None
        logger.info(f"[get_project] 查询完成 | found={result is not None}")
        return result
    except Exception as e:
        logger.error(f"[get_project] 查询失败 | error={e}", exc_info=True)
        raise
    finally:
        conn.close()


def create_project(name: str, description: str = "", status: str = "active") -> Dict[str, Any]:
    """
    创建项目

    Args:
        name: 项目名称
        description: 项目描述
        status: 状态（active / completed）

    Returns:
        Dict: 新建的项目对象（含 id / created_at）
    """
    logger.info(f"[create_project] 创建项目 | name={name} | status={status}")

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    project_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    try:
        cursor.execute('''
            INSERT INTO projects (id, name, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, name, description or "", status or "active", created_at, created_at))
        conn.commit()
        logger.info(f"[create_project] 创建成功 | id={project_id} | affected={cursor.rowcount}")
        return {
            "id": project_id,
            "name": name,
            "description": description or "",
            "status": status or "active",
            "created_at": created_at,
        }
    except Exception as e:
        logger.error(f"[create_project] 创建失败 | error={e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新项目

    Args:
        project_id: 项目 ID
        name: 项目名称（None 则不更新）
        description: 项目描述（None 则不更新）
        status: 状态（None 则不更新）

    Returns:
        Optional[Dict]: 更新后的项目对象，项目不存在返回 None
    """
    logger.info(f"[update_project] 更新项目 | project_id={project_id}")

    init_db()

    existing = get_project(project_id)
    if not existing:
        logger.warning(f"[update_project] 项目不存在 | project_id={project_id}")
        return None

    new_name = name if name is not None else existing["name"]
    new_desc = description if description is not None else existing["description"]
    new_status = status if status is not None else existing["status"]
    updated_at = datetime.now().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE projects
            SET name = ?, description = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (new_name, new_desc, new_status, updated_at, project_id))
        conn.commit()
        logger.info(f"[update_project] 更新完成 | project_id={project_id} | affected={cursor.rowcount}")
        return {
            "id": project_id,
            "name": new_name,
            "description": new_desc,
            "status": new_status,
            "created_at": existing["created_at"],
        }
    except Exception as e:
        logger.error(f"[update_project] 更新失败 | error={e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_project(project_id: str) -> bool:
    """
    删除项目

    Args:
        project_id: 项目 ID

    Returns:
        bool: 是否删除了记录（项目不存在返回 False）
    """
    logger.info(f"[delete_project] 删除项目 | project_id={project_id}")

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        affected = cursor.rowcount
        logger.info(f"[delete_project] 删除完成 | project_id={project_id} | affected={affected}")
        return affected > 0
    except Exception as e:
        logger.error(f"[delete_project] 删除失败 | error={e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()
