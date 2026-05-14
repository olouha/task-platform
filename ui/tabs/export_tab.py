"""
导出管理标签页
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QLabel, QFileDialog, QMessageBox,
                              QGroupBox, QFormLayout, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
import os
import logging


class ExportTab(QWidget):
    """导出管理标签页"""

    def __init__(self, database, export_manager):
        super().__init__()
        self.database = database
        self.export_manager = export_manager
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 快速导出区域
        quick_group = QGroupBox("快速导出")
        quick_layout = QFormLayout()

        # 数据源选择
        self.source_combo = QComboBox()
        self.source_combo.addItems([
            "task_logs",
            "scraper_data_*",
            "browser_table_*",
            "全部任务"
        ])
        quick_layout.addRow("数据源:", self.source_combo)

        # 格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "Excel (xlsx)", "JSON"])
        quick_layout.addRow("导出格式:", self.format_combo)

        # 文件名
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("留空自动生成")
        quick_layout.addRow("文件名:", self.filename_input)

        # 导出按钮
        export_btn = QPushButton("导出数据")
        export_btn.clicked.connect(self._quick_export)
        quick_layout.addRow("", export_btn)

        quick_group.setLayout(quick_layout)
        main_layout.addWidget(quick_group)

        # 历史导出记录
        history_label = QLabel("历史导出文件")
        history_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px 0;")
        main_layout.addWidget(history_label)

        # 文件列表
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["文件名", "大小", "修改时间", "操作"])
        self.file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.file_table)

        # 按钮栏
        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        open_folder_btn = QPushButton("打开导出目录")
        open_folder_btn.clicked.connect(self._open_folder)
        btn_layout.addWidget(open_folder_btn)

        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

    def refresh(self):
        """刷新文件列表"""
        self.file_table.setRowCount(0)

        files = self.export_manager.list_exports()

        for filename in files:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)

            filepath = os.path.join(self.export_manager.output_dir, filename)

            # 文件名
            self.file_table.setItem(row, 0, QTableWidgetItem(filename))

            # 大小
            try:
                size = os.path.getsize(filepath)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / 1024 / 1024:.1f} MB"
                self.file_table.setItem(row, 1, QTableWidgetItem(size_str))
            except:
                self.file_table.setItem(row, 1, QTableWidgetItem("-"))

            # 修改时间
            try:
                mtime = os.path.getmtime(filepath)
                from datetime import datetime
                time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                self.file_table.setItem(row, 2, QTableWidgetItem(time_str))
            except:
                self.file_table.setItem(row, 2, QTableWidgetItem("-"))

            # 操作按钮
            open_btn = QPushButton("打开")
            open_btn.clicked.connect(lambda _, f=filepath: self._open_file(f))
            self.file_table.setCellWidget(row, 3, open_btn)

    def _quick_export(self):
        """快速导出"""
        source = self.source_combo.currentText()
        export_format = self.format_combo.currentText().lower()
        filename = self.filename_input.text().strip()

        # 确定格式
        if 'xlsx' in export_format:
            fmt = 'xlsx'
        elif 'json' in export_format:
            fmt = 'json'
        else:
            fmt = 'csv'

        # 获取数据
        data = []
        if source == 'task_logs':
            cursor = self.database._get_cursor()
            cursor.execute("SELECT * FROM task_logs ORDER BY executed_at DESC")
            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            QMessageBox.information(self, "提示", "请先配置任务数据源")
            return

        if not data:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return

        # 导出
        filepath = self.export_manager.export_now(data, fmt, filename or None)

        if filepath:
            QMessageBox.information(self, "成功", f"导出成功:\n{filepath}")
            self.refresh()
        else:
            QMessageBox.warning(self, "失败", "导出失败")

    def _open_file(self, filepath: str):
        """打开文件"""
        try:
            os.startfile(filepath)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件: {e}")

    def _open_folder(self):
        """打开导出目录"""
        folder = self.export_manager.output_dir
        if os.path.exists(folder):
            os.startfile(folder)
        else:
            os.makedirs(folder, exist_ok=True)
            os.startfile(folder)