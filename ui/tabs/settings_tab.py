"""
设置标签页
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QLineEdit, QPushButton, QComboBox, QLabel,
                              QGroupBox, QMessageBox, QCheckBox)
from PyQt6.QtCore import Qt
import logging


class SettingsTab(QWidget):
    """设置标签页"""

    def __init__(self, database):
        super().__init__()
        self.database = database
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 数据库设置
        db_group = QGroupBox("数据库设置")
        db_layout = QFormLayout()

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite", "MySQL", "PostgreSQL"])
        self.db_type_combo.currentTextChanged.connect(self._on_db_type_changed)
        db_layout.addRow("数据库类型:", self.db_type_combo)

        # MySQL/PostgreSQL 配置
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost")
        db_layout.addRow("主机:", self.host_input)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("3306")
        db_layout.addRow("端口:", self.port_input)

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root")
        db_layout.addRow("用户名:", self.user_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        db_layout.addRow("密码:", self.password_input)

        self.db_name_input = QLineEdit()
        self.db_name_input.setPlaceholderText("task_platform")
        db_layout.addRow("数据库名:", self.db_name_input)

        # SQLite 配置
        self.sqlite_path = QLineEdit()
        self.sqlite_path.setPlaceholderText("task_platform.db")
        db_layout.addRow("数据库路径:", self.sqlite_path)

        # 测试连接
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        db_layout.addRow("", test_btn)

        db_group.setLayout(db_layout)
        main_layout.addWidget(db_group)

        # 调度器设置
        scheduler_group = QGroupBox("调度器设置")
        scheduler_layout = QFormLayout()

        self.max_concurrent = QLineEdit()
        self.max_concurrent.setText("5")
        scheduler_layout.addRow("最大并发任务:", self.max_concurrent)

        self.default_timeout = QLineEdit()
        self.default_timeout.setText("300")
        scheduler_layout.addRow("默认超时(秒):", self.default_timeout)

        self.retry_check = QCheckBox()
        self.retry_check.setChecked(True)
        scheduler_layout.addRow("失败自动重试:", self.retry_check)

        self.max_retries = QLineEdit()
        self.max_retries.setText("3")
        scheduler_layout.addRow("最大重试次数:", self.max_retries)

        scheduler_group.setLayout(scheduler_layout)
        main_layout.addWidget(scheduler_group)

        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save_settings)
        save_layout.addWidget(save_btn)

        main_layout.addLayout(save_layout)
        main_layout.addStretch()

    def _on_db_type_changed(self, text: str):
        """数据库类型改变"""
        show_mysql = text in ["MySQL", "PostgreSQL"]

        # 显示/隐藏MySQL配置
        self.host_input.setVisible(show_mysql)
        self.port_input.setVisible(show_mysql)
        self.user_input.setVisible(show_mysql)
        self.password_input.setVisible(show_mysql)
        self.db_name_input.setVisible(show_mysql)
        self.sqlite_path.setVisible(not show_mysql)

    def _load_settings(self):
        """加载设置"""
        # 从数据库加载设置
        db_config = self.database.get_config('db_config', {})

        db_type = db_config.get('type', 'sqlite')
        self.db_type_combo.setCurrentText(db_type.title())

        self.host_input.setText(db_config.get('host', 'localhost'))
        self.port_input.setText(str(db_config.get('port', 3306)))
        self.user_input.setText(db_config.get('user', 'root'))
        self.password_input.setText(db_config.get('password', ''))
        self.db_name_input.setText(db_config.get('database', 'task_platform'))
        self.sqlite_path.setText(db_config.get('path', 'task_platform.db'))

        # 调度器设置
        scheduler_config = self.database.get_config('scheduler_config', {})

        self.max_concurrent.setText(str(scheduler_config.get('max_concurrent_tasks', 5)))
        self.default_timeout.setText(str(scheduler_config.get('default_timeout', 300)))
        self.retry_check.setChecked(scheduler_config.get('retry_on_failure', True))
        self.max_retries.setText(str(scheduler_config.get('max_retries', 3)))

    def _save_settings(self):
        """保存设置"""
        db_type = self.db_type_combo.currentText().lower()

        db_config = {
            'type': db_type
        }

        if db_type == 'sqlite':
            db_config['path'] = self.sqlite_path.text()
        else:
            db_config['host'] = self.host_input.text()
            db_config['port'] = int(self.port_input.text() or 3306)
            db_config['user'] = self.user_input.text()
            db_config['password'] = self.password_input.text()
            db_config['database'] = self.db_name_input.text()

        self.database.save_config('db_config', db_config)

        scheduler_config = {
            'max_concurrent_tasks': int(self.max_concurrent.text() or 5),
            'default_timeout': int(self.default_timeout.text() or 300),
            'retry_on_failure': self.retry_check.isChecked(),
            'max_retries': int(self.max_retries.text() or 3)
        }

        self.database.save_config('scheduler_config', scheduler_config)

        QMessageBox.information(self, "成功", "设置已保存")

    def _test_connection(self):
        """测试连接"""
        db_type = self.db_type_combo.currentText().lower()

        try:
            if db_type == 'sqlite':
                import sqlite3
                db_path = self.sqlite_path.text() or 'task_platform.db'
                conn = sqlite3.connect(db_path)
                conn.close()
                QMessageBox.information(self, "成功", f"SQLite 连接成功\n路径: {db_path}")

            elif db_type == 'mysql':
                import pymysql
                conn = pymysql.connect(
                    host=self.host_input.text() or 'localhost',
                    port=int(self.port_input.text() or 3306),
                    user=self.user_input.text() or 'root',
                    password=self.password_input.text(),
                    database=self.db_name_input.text() or 'task_platform'
                )
                conn.close()
                QMessageBox.information(self, "成功", "MySQL 连接成功")

            elif db_type == 'postgresql':
                import psycopg2
                conn = psycopg2.connect(
                    host=self.host_input.text() or 'localhost',
                    port=int(self.port_input.text() or 5432),
                    user=self.user_input.text() or 'postgres',
                    password=self.password_input.text(),
                    database=self.db_name_input.text() or 'task_platform'
                )
                conn.close()
                QMessageBox.information(self, "成功", "PostgreSQL 连接成功")

        except Exception as e:
            QMessageBox.warning(self, "连接失败", str(e))