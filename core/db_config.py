"""
数据库连接配置模块
"""

import json
import os


class DBConfig:
    """数据库配置类"""

    # 支持的数据库类型
    DB_TYPES = ['mysql', 'postgresql', 'sqlite']

    def __init__(self, config_path: str = None):
        self.config_path = config_path or 'config/settings.json'
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self) -> dict:
        """默认配置"""
        return {
            "database": {
                "type": "sqlite",
                "path": "task_platform.db"
            }
        }

    def get_db_config(self) -> dict:
        """获取数据库配置"""
        return self._config.get('database', {})

    def get_db_type(self) -> str:
        """获取数据库类型"""
        return self.get_db_config().get('type', 'sqlite')

    def is_mysql(self) -> bool:
        """是否为 MySQL"""
        return self.get_db_type() == 'mysql'

    def is_postgresql(self) -> bool:
        """是否为 PostgreSQL"""
        return self.get_db_type() == 'postgresql'

    def is_sqlite(self) -> bool:
        """是否为 SQLite"""
        return self.get_db_type() == 'sqlite'

    def update_config(self, db_type: str, **kwargs):
        """更新配置"""
        self._config['database'] = {
            'type': db_type,
            **kwargs
        }
        self._save_config()

    def _save_config(self):
        """保存配置"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=4, ensure_ascii=False)

    def test_connection(self) -> tuple:
        """测试数据库连接

        Returns:
            tuple: (success: bool, message: str)
        """
        db_config = self.get_db_config()
        db_type = db_config.get('type', 'sqlite')

        if db_type == 'mysql':
            try:
                import pymysql
                conn = pymysql.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 3306),
                    user=db_config.get('user', 'root'),
                    password=db_config.get('password', ''),
                    database=db_config.get('database', 'task_platform'),
                    charset=db_config.get('charset', 'utf8mb4')
                )
                conn.close()
                return True, "MySQL 连接成功"
            except Exception as e:
                return False, f"MySQL 连接失败: {e}"

        elif db_type == 'postgresql':
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=db_config.get('host', 'localhost'),
                    port=db_config.get('port', 5432),
                    user=db_config.get('user', 'postgres'),
                    password=db_config.get('password', ''),
                    database=db_config.get('database', 'task_platform')
                )
                conn.close()
                return True, "PostgreSQL 连接成功"
            except Exception as e:
                return False, f"PostgreSQL 连接失败: {e}"

        else:  # sqlite
            db_path = db_config.get('path', 'task_platform.db')
            try:
                if os.path.exists(db_path) or os.access(os.path.dirname(db_path) or '.', os.W_OK):
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    conn.close()
                    return True, f"SQLite 连接成功 ({db_path})"
                else:
                    return False, "SQLite 路径不可写"
            except Exception as e:
                return False, f"SQLite 连接失败: {e}"