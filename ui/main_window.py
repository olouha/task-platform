"""
主窗口模块
"""

import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QTabWidget, QPushButton, QLabel, QStatusBar,
                              QMessageBox, QMenuBar, QMenu)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
import sys
import os

# 导入子模块
from .tabs.dashboard_tab import DashboardTab
from .tabs.tasks_tab import TasksTab
from .tabs.settings_tab import SettingsTab
from .tabs.logs_tab import LogsTab
from .tabs.scraper_tab import ScraperTab
from .tabs.export_tab import ExportTab


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self, scheduler, database, scraper_manager=None, export_manager=None):
        super().__init__()

        self.scheduler = scheduler
        self.database = database
        self.scraper_manager = scraper_manager
        self.export_manager = export_manager
        self.logger = logging.getLogger(__name__)

        self._init_ui()
        self._init_menu()
        self._init_status_bar()

        # 定时刷新任务状态
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_status)
        self.refresh_timer.start(30000)  # 30秒刷新一次

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("TaskPlatform - 任务调度平台")
        self.setMinimumSize(1000, 700)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建标签页
        self.tabs = QTabWidget()

        # 添加标签页
        self.dashboard_tab = DashboardTab(self.scheduler, self.database)
        self.tasks_tab = TasksTab(self.scheduler, self.database)
        self.scraper_tab = ScraperTab(self.scheduler, self.database, self.scraper_manager)
        self.export_tab = ExportTab(self.database, self.export_manager) if self.export_manager else None
        self.logs_tab = LogsTab(self.database)
        self.settings_tab = SettingsTab(self.database)

        self.tabs.addTab(self.dashboard_tab, "仪表盘")
        self.tabs.addTab(self.tasks_tab, "任务管理")
        self.tabs.addTab(self.scraper_tab, "数据抓取")
        if self.export_tab:
            self.tabs.addTab(self.export_tab, "数据导出")
        self.tabs.addTab(self.logs_tab, "执行日志")
        self.tabs.addTab(self.settings_tab, "设置")

        main_layout.addWidget(self.tabs)

        # 连接信号
        self.tasks_tab.task_updated.connect(self._on_task_updated)
        self.scraper_tab.task_updated.connect(self._on_task_updated)

    def _init_menu(self):
        """初始化菜单"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        # 导入任务
        import_action = QAction("导入任务...", self)
        import_action.triggered.connect(self._import_tasks)
        file_menu.addAction(import_action)

        # 导出任务
        export_action = QAction("导出任务...", self)
        export_action.triggered.connect(self._export_tasks)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # 退出
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具")

        # 清空日志
        clear_logs_action = QAction("清空日志", self)
        clear_logs_action.triggered.connect(self._clear_logs)
        tools_menu.addAction(clear_logs_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _init_status_bar(self):
        """初始化状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status_bar()

    def _update_status_bar(self):
        """更新状态栏"""
        tasks = self.scheduler.list_tasks()
        enabled = sum(1 for t in tasks if t.get('enabled', False))
        running = sum(1 for t in tasks if t.get('status') == 'running')

        self.status_bar.showMessage(f"任务总数: {len(tasks)} | 启用: {enabled} | 运行中: {running}")

    def _refresh_status(self):
        """刷新状态"""
        self._update_status_bar()
        self.dashboard_tab.refresh()

    def _on_task_updated(self):
        """任务更新时触发"""
        self._update_status_bar()
        self.dashboard_tab.refresh()

    def _import_tasks(self):
        """导入任务"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入任务", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                for task_data in tasks:
                    self.scheduler.add_task(task_data)
                    self.database.save_task(task_data)
                QMessageBox.information(self, "成功", f"已导入 {len(tasks)} 个任务")
                self.tasks_tab.refresh()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")

    def _export_tasks(self):
        """导出任务"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出任务", "", "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                import json
                tasks = self.scheduler.list_tasks()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, indent=2, ensure_ascii=False)
                QMessageBox.information(self, "成功", f"已导出 {len(tasks)} 个任务")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {e}")

    def _clear_logs(self):
        """清空日志"""
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有日志吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cursor = self.database._get_cursor()
            cursor.execute("DELETE FROM task_logs")
            self.database._connection.commit()
            self.logs_tab.refresh()
            QMessageBox.information(self, "成功", "日志已清空")

    def _show_about(self):
        """显示关于"""
        QMessageBox.about(self, "关于",
            "TaskPlatform v1.0.0\n\n"
            "一个模块化的任务调度平台\n\n"
            "功能:\n"
            "- 定时任务调度\n"
            "- 多数据库支持\n"
            "- 任务执行日志\n"
            "- 可视化界面"
        )

    def closeEvent(self, event):
        """关闭时保存状态"""
        self.scheduler.stop()
        self.database.close()
        event.accept()