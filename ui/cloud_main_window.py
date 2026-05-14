"""
云端主窗口
在主窗口基础上增加云端同步功能
"""

import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QStatusBar, QMessageBox, QGroupBox,
                              QFormLayout, QLineEdit, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor


class CloudStatusWidget(QWidget):
    """云端状态显示"""

    def __init__(self, cloud_client, sync_manager):
        super().__init__()
        self.cloud = cloud_client
        self.sync = sync_manager
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 连接状态
        self.status_label = QLabel("●")
        self.status_label.setStyleSheet("color: red; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.status_text = QLabel("离线")
        layout.addWidget(self.status_text)

        # 同步模式
        layout.addSpacing(20)
        layout.addWidget(QLabel("同步模式:"))

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["离线", "云端只读", "双向同步"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        # 同步按钮
        self.sync_btn = QPushButton("同步")
        self.sync_btn.clicked.connect(self._do_sync)
        layout.addWidget(self.sync_btn)

    def update_status(self):
        """更新状态"""
        connected = self.cloud.is_connected()

        if connected:
            self.status_label.setStyleSheet("color: green; font-size: 12px;")
            self.status_text.setText("已连接")
        else:
            self.status_label.setStyleSheet("color: red; font-size: 12px;")
            self.status_text.setText("离线")

        status = self.sync.get_sync_status()
        if status['mode'] == 'offline':
            self.mode_combo.setCurrentText("离线")
        elif status['mode'] == 'online':
            self.mode_combo.setCurrentText("云端只读")
        else:
            self.mode_combo.setCurrentText("双向同步")

    def _on_mode_changed(self, text: str):
        """模式改变"""
        mode_map = {
            "离线": "offline",
            "云端只读": "online",
            "双向同步": "sync"
        }
        self.sync.set_mode(mode_map[text])
        self.update_status()

    def _do_sync(self):
        """执行同步"""
        if not self.cloud.is_connected():
            QMessageBox.warning(self, "警告", "云端未连接")
            return

        if self.sync.sync_tasks():
            QMessageBox.information(self, "成功", "同步完成")
        else:
            QMessageBox.warning(self, "失败", "同步失败")

        self.update_status()


class CloudSettingsDialog(QWidget):
    """云端设置对话框内容"""

    def __init__(self, cloud_client, db):
        super().__init__()
        self.cloud = cloud_client
        self.db = db
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)

        # 服务器设置
        group = QGroupBox("云端服务器设置")
        form = QFormLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:5000")
        form.addRow("服务器地址:", self.url_input)

        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        form.addRow("", self.test_btn)

        group.setLayout(form)
        layout.addWidget(group)

        # 当前连接状态
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("padding: 10px; background: #f0f0f0;")
        layout.addWidget(self.status_label)

        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

        # 加载当前设置
        self._load_settings()

    def _load_settings(self):
        """加载设置"""
        cloud_url = self.db.get_config('cloud_url', 'http://localhost:5000')
        self.url_input.setText(cloud_url)
        self._test_connection()

    def _test_connection(self):
        """测试连接"""
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("请输入服务器地址")
            return

        # 临时设置
        self.cloud.server_url = url

        if self.cloud.is_connected():
            self.status_label.setText("✓ 连接成功")
            self.status_label.setStyleSheet("padding: 10px; background: #d4edda; color: green;")
        else:
            self.status_label.setText("✗ 连接失败")
            self.status_label.setStyleSheet("padding: 10px; background: #f8d7da; color: red;")

    def _save_settings(self):
        """保存设置"""
        url = self.url_input.text().strip()
        self.db.save_config('cloud_url', url)
        self.cloud.server_url = url
        QMessageBox.information(self, "成功", "设置已保存")


# 继承主窗口，添加云端功能
from ui.main_window import MainWindow


class CloudMainWindow(MainWindow):
    """云端版主窗口"""

    def __init__(self, scheduler, database, cloud_client, sync_manager, export_manager=None):
        super().__init__(scheduler, database, None, export_manager)

        self.cloud = cloud_client
        self.sync = sync_manager

        self.setWindowTitle("TaskPlatform - 云端版")

        # 添加云端状态栏
        self._add_cloud_status()

        # 添加云端设置标签页
        from ui.tabs.settings_tab import SettingsTab

        # 替换设置标签页为带云端设置的版本
        self.settings_tab = CloudSettingsTab(self.database, self.cloud)
        self.tabs.removeTab(4)  # 移除旧的设置标签
        self.tabs.addTab(self.settings_tab, "云端设置")

    def _add_cloud_status(self):
        """添加云端状态栏"""
        # 在现有状态栏添加云端状态
        self.cloud_status = CloudStatusWidget(self.cloud, self.sync)

        # 创建定时器更新状态
        self.cloud_timer = QTimer()
        self.cloud_timer.timeout.connect(self.cloud_status.update_status)
        self.cloud_timer.start(10000)  # 每10秒更新

        # 添加到状态栏
        self.status_bar.addPermanentWidget(self.cloud_status)

    def _show_about(self):
        """显示关于"""
        QMessageBox.about(self, "关于",
            "TaskPlatform 云端版 v1.0.0\n\n"
            "一个支持云端同步的任务调度平台\n\n"
            "功能:\n"
            "- 定时任务调度\n"
            "- 多数据库支持\n"
            "- 云端数据同步\n"
            "- 离线/在线模式切换"
        )


class CloudSettingsTab(QWidget):
    """云端设置标签页"""

    def __init__(self, database, cloud_client):
        super().__init__()
        self.database = database
        self.cloud = cloud_client
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 服务器设置
        server_group = QGroupBox("云端服务器设置")
        server_layout = QFormLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://localhost:5000")
        server_layout.addRow("服务器地址:", self.url_input)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        server_layout.addRow("", test_btn)

        self.connection_status = QLabel("未测试")
        self.connection_status.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        server_layout.addRow("连接状态:", self.connection_status)

        server_group.setLayout(server_layout)
        main_layout.addWidget(server_group)

        # 同步设置
        sync_group = QGroupBox("同步设置")
        sync_layout = QFormLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["离线模式", "云端只读", "双向同步"])
        sync_layout.addRow("同步模式:", self.mode_combo)

        self.auto_sync_check = QCheckBox()
        self.auto_sync_check.setChecked(True)
        sync_layout.addRow("自动同步:", self.auto_sync_check)

        self.sync_interval = QLineEdit()
        self.sync_interval.setText("60")
        sync_layout.addRow("同步间隔(秒):", self.sync_interval)

        sync_group.setLayout(sync_layout)
        main_layout.addWidget(sync_group)

        # 统计信息
        stats_group = QGroupBox("云端统计")
        stats_layout = QFormLayout()

        self.stats_label = QLabel("点击刷新获取统计")
        stats_layout.addRow("云端状态:", self.stats_label)

        refresh_stats_btn = QPushButton("刷新统计")
        refresh_stats_btn.clicked.connect(self._refresh_stats)
        stats_layout.addRow("", refresh_stats_btn)

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # 保存按钮
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save_settings)
        save_layout.addWidget(save_btn)

        main_layout.addLayout(save_layout)
        main_layout.addStretch()

    def _load_settings(self):
        """加载设置"""
        cloud_config = self.database.get_config('cloud_config', {})

        self.url_input.setText(cloud_config.get('url', 'http://localhost:5000'))

        mode = cloud_config.get('mode', 'offline')
        mode_map = {'offline': '离线模式', 'online': '云端只读', 'sync': '双向同步'}
        self.mode_combo.setCurrentText(mode_map.get(mode, '离线模式'))

        self.auto_sync_check.setChecked(cloud_config.get('auto_sync', True))
        self.sync_interval.setText(str(cloud_config.get('sync_interval', 60)))

    def _test_connection(self):
        """测试连接"""
        url = self.url_input.text().strip()
        if not url:
            self.connection_status.setText("请输入服务器地址")
            return

        self.cloud.server_url = url

        if self.cloud.is_connected():
            self.connection_status.setText("✓ 连接成功")
            self.connection_status.setStyleSheet("padding: 10px; background: #d4edda; color: green; border-radius: 5px;")
        else:
            self.connection_status.setText("✗ 连接失败")
            self.connection_status.setStyleSheet("padding: 10px; background: #f8d7da; color: red; border-radius: 5px;")

    def _refresh_stats(self):
        """刷新统计"""
        stats = self.cloud.get_stats()
        if stats:
            self.stats_label.setText(
                f"任务总数: {stats.get('total_tasks', 0)}\n"
                f"启用任务: {stats.get('enabled_tasks', 0)}\n"
                f"日志记录: {stats.get('total_logs', 0)}"
            )
        else:
            self.stats_label.setText("获取失败")

    def _save_settings(self):
        """保存设置"""
        mode_map = {'离线模式': 'offline', '云端只读': 'online', '双向同步': 'sync'}

        cloud_config = {
            'url': self.url_input.text().strip(),
            'mode': mode_map.get(self.mode_combo.currentText(), 'offline'),
            'auto_sync': self.auto_sync_check.isChecked(),
            'sync_interval': int(self.sync_interval.text() or 60)
        }

        self.database.save_config('cloud_config', cloud_config)
        self.cloud.server_url = cloud_config['url']

        QMessageBox.information(self, "成功", "设置已保存")