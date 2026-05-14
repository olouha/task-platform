"""
日志标签页
显示任务执行日志
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QComboBox, QLabel)
from PyQt6.QtCore import Qt


class LogsTab(QWidget):
    """日志标签页"""

    def __init__(self, database):
        super().__init__()
        self.database = database
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 筛选栏
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("任务:"))

        self.task_combo = QComboBox()
        self.task_combo.currentTextChanged.connect(self.refresh)
        filter_layout.addWidget(self.task_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # 日志表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "任务ID", "状态", "时间", "消息"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        main_layout.addWidget(self.table)

    def refresh(self):
        """刷新日志"""
        self.table.setRowCount(0)

        # 更新任务下拉框
        tasks = self.database.get_all_tasks()
        current_task = self.task_combo.currentText()

        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("全部")
        for task in tasks:
            self.task_combo.addItem(task.get('id', '')[:12])
        self.task_combo.blockSignals(False)

        # 设置当前选择
        index = self.task_combo.findText(current_task)
        if index >= 0:
            self.task_combo.setCurrentIndex(index)

        # 获取日志
        if current_task == "全部" or current_task == "":
            # 获取所有任务的日志
            cursor = self.database._get_cursor()
            cursor.execute("""
                SELECT * FROM task_logs
                ORDER BY executed_at DESC
                LIMIT 500
            """)
            rows = cursor.fetchall()
        else:
            # 获取特定任务的日志
            logs = self.database.get_task_logs(current_task, limit=500)
            rows = [(log.get('id'), log.get('task_id'), log.get('status'),
                     log.get('executed_at'), log.get('message'))
                    for log in logs]

        # 显示日志
        for row_data in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)

            for col, value in enumerate(row_data):
                if col == 4:  # 消息列
                    item = QTableWidgetItem(str(value or '')[:50])
                elif col == 3:  # 时间列
                    item = QTableWidgetItem(str(value or '')[:19])
                else:
                    item = QTableWidgetItem(str(value or ''))

                # 状态列着色
                if col == 2:
                    if value == 'success':
                        item.setBackground(Qt.GlobalColor.green)
                        item.setForeground(Qt.GlobalColor.white)
                    elif value == 'failed':
                        item.setBackground(Qt.GlobalColor.red)
                        item.setForeground(Qt.GlobalColor.white)

                self.table.setItem(row, col, item)