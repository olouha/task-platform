"""
数据库管理模块
支持 MySQL/PostgreSQL/SQLite
"""

import json
import logging
import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import sqlite3

# 尝试导入 MySQL 驱动
try:
    import pymysql
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False

try:
    import psycopg2
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config_path: str = None, config: Dict = None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self._connection = None
        self._db_type = None

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

        db_config = self.config.get('database', {})
        self._db_type = db_config.get('type', 'sqlite').lower()
        self._connect(db_config)

    def _connect(self, db_config: Dict):
        """建立数据库连接"""
        try:
            if self._db_type == 'mysql' and HAS_MYSQL:
                self._connection = pymysql.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 3306),
                    user=db_config.get('user', 'root'),
                    password=db_config.get('password', ''),
                    database=db_config.get('database', 'task_platform'),
                    charset=db_config.get('charset', 'utf8mb4')
                )
                self.logger.info("Connected to MySQL database")

            elif self._db_type == 'postgresql' and HAS_POSTGRESQL:
                self._connection = psycopg2.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 5432),
                    user=db_config.get('user', 'postgres'),
                    password=db_config.get('password', ''),
                    database=db_config.get('database', 'task_platform')
                )
                self.logger.info("Connected to PostgreSQL database")

            else:
                # 默认使用 SQLite
                db_path = db_config.get('path', 'task_platform.db')
                self._connection = sqlite3.connect(db_path, check_same_thread=False)
                self._db_type = 'sqlite'
                self.logger.info(f"Connected to SQLite database: {db_path}")

            self._init_tables()

        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            # 回退到 SQLite
            db_path = db_config.get('path', 'task_platform.db')
            self._connection = sqlite3.connect(db_path, check_same_thread=False)
            self._db_type = 'sqlite'
            self.logger.info(f"Fallback to SQLite database: {db_path}")
            self._init_tables()

    def _init_tables(self):
        """初始化数据库表"""
        cursor = self._get_cursor()

        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                task_type TEXT DEFAULT 'custom',
                cron_expr TEXT DEFAULT '',
                interval_seconds INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                last_run TEXT,
                next_run TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                config TEXT DEFAULT '{}',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 执行记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT DEFAULT '',
                result TEXT DEFAULT '',
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)

        # 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._connection.commit()

    def _get_cursor(self):
        """获取游标"""
        return self._connection.cursor()

    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            yield self._connection
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            raise e

    # ========== 任务相关操作 ==========

    def save_task(self, task_data: Dict) -> bool:
        """保存任务"""
        try:
            cursor = self._get_cursor()

            # 序列化 config 为 JSON
            config_json = json.dumps(task_data.get('config', {}), ensure_ascii=False)

            cursor.execute("""
                INSERT OR REPLACE INTO tasks
                (id, name, description, task_type, cron_expr, interval_seconds,
                 enabled, status, last_run, next_run, retry_count, max_retries, config, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                task_data['id'],
                task_data['name'],
                task_data.get('description', ''),
                task_data.get('task_type', 'custom'),
                task_data.get('cron_expr', ''),
                task_data.get('interval_seconds', 0),
                1 if task_data.get('enabled', True) else 0,
                task_data.get('status', 'pending'),
                task_data.get('last_run'),
                task_data.get('next_run'),
                task_data.get('retry_count', 0),
                task_data.get('max_retries', 3),
                config_json
            ))

            self._connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Failed to save task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()

        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))

            # 反序列化 config
            if result.get('config'):
                result['config'] = json.loads(result['config'])

            return result
        return None

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        cursor = self._get_cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")

        results = []
        for row in cursor.fetchall():
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))

            # 反序列化 config
            if result.get('config'):
                result['config'] = json.loads(result['config'])

            results.append(result)

        return results

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        try:
            cursor = self._get_cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self._connection.commit()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete task: {e}")
            return False

    # ========== 日志相关操作 ==========

    def add_log(self, task_id: str, status: str, message: str = '', result: str = ''):
        """添加执行日志"""
        try:
            cursor = self._get_cursor()
            cursor.execute("""
                INSERT INTO task_logs (task_id, status, message, result)
                VALUES (?, ?, ?, ?)
            """, (task_id, status, message, result))
            self._connection.commit()
        except Exception as e:
            self.logger.error(f"Failed to add log: {e}")

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict]:
        """获取任务日志"""
        cursor = self._get_cursor()
        cursor.execute("""
            SELECT * FROM task_logs
            WHERE task_id = ?
            ORDER BY executed_at DESC
            LIMIT ?
        """, (task_id, limit))

        results = []
        for row in cursor.fetchall():
            columns = [desc[0] for desc in cursor.description]
            results.append(dict(zip(columns, row)))

        return results

    # ========== 配置相关操作 ==========

    def save_config(self, key: str, value: Any):
        """保存配置"""
        cursor = self._get_cursor()
        value_json = json.dumps(value, ensure_ascii=False)
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, value_json))
        self._connection.commit()

    def get_config(self, key: str, default=None):
        """获取配置"""
        cursor = self._get_cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return default

    def close(self):
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self.logger.info("Database connection closed")