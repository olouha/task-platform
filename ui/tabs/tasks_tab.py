"""
任务管理标签页
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QDialog, QFormLayout, QLineEdit, QTextEdit,
                              QComboBox, QCheckBox, QMessageBox, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
import uuid
import logging


class TasksTab(QWidget):
    """任务管理标签页"""

    task_updated = pyqtSignal()

    def __init__(self, scheduler, database):
        super().__init__()
        self.scheduler = scheduler
        self.database = database
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 按钮栏
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("添加任务")
        add_btn.clicked.connect(self._add_task)
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton("编辑任务")
        edit_btn.clicked.connect(self._edit_task)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("删除任务")
        delete_btn.clicked.connect(self._delete_task)
        btn_layout.addWidget(delete_btn)

        run_btn = QPushButton("立即执行")
        run_btn.clicked.connect(self._run_task)
        btn_layout.addWidget(run_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # 任务表格
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "任务名称", "类型", "调度规则", "状态", "启用", "上次执行", "下次执行", "描述"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        main_layout.addWidget(self.table)

    def refresh(self):
        """刷新任务列表"""
        self.table.setRowCount(0)

        tasks = self.database.get_all_tasks()

        for task in tasks:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(task.get('id', '')[:12]))

            # 任务名称
            self.table.setItem(row, 1, QTableWidgetItem(task.get('name', '')))

            # 类型
            task_type = task.get('task_type', 'custom')
            type_text = {'cron': 'Cron', 'interval': '间隔', 'custom': '自定义'}.get(task_type, task_type)
            self.table.setItem(row, 2, QTableWidgetItem(type_text))

            # 调度规则
            if task_type == 'cron':
                rule = task.get('cron_expr', '')
            elif task_type == 'interval':
                interval = task.get('interval_seconds', 0)
                if interval >= 3600:
                    rule = f"{interval // 3600}小时"
                elif interval >= 60:
                    rule = f"{interval // 60}分钟"
                else:
                    rule = f"{interval}秒"
            else:
                rule = '-'
            self.table.setItem(row, 3, QTableWidgetItem(rule))

            # 状态
            status = task.get('status', 'pending')
            status_item = QTableWidgetItem(status)
            if status == 'running':
                status_item.setBackground(Qt.GlobalColor.green)
            elif status == 'failed':
                status_item.setBackground(Qt.GlobalColor.red)
            self.table.setItem(row, 4, status_item)

            # 启用
            enabled = task.get('enabled', True)
            self.table.setItem(row, 5, QTableWidgetItem("是" if enabled else "否"))

            # 上次执行
            last_run = task.get('last_run', '')
            if last_run:
                last_run = last_run[:19]
            self.table.setItem(row, 6, QTableWidgetItem(last_run))

            # 下次执行
            next_run = task.get('next_run', '')
            if next_run:
                next_run = next_run[:19]
            self.table.setItem(row, 7, QTableWidgetItem(next_run))

            # 描述
            self.table.setItem(row, 8, QTableWidgetItem(task.get('description', '')[:30]))

    def _add_task(self):
        """添加任务"""
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            task_data['id'] = str(uuid.uuid4())[:8]

            # 保存到数据库
            self.database.save_task(task_data)

            # 添加到调度器
            from core.scheduler import Task
            task = Task(**task_data)
            self.scheduler.add_task(task)

            self.refresh()
            self.task_updated.emit()

    def _edit_task(self):
        """编辑任务"""
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return

        task_id = self.table.item(selected, 0).text()
        task_data = self.database.get_task(task_id)

        if not task_data:
            QMessageBox.warning(self, "错误", "未找到任务")
            return

        dialog = TaskDialog(self, task_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_task_data()
            updated_data['id'] = task_id

            # 更新数据库
            self.database.save_task(updated_data)

            # 更新调度器
            from core.scheduler import Task
            task = Task(**updated_data)
            self.scheduler.add_task(task)

            self.refresh()
            self.task_updated.emit()

    def _delete_task(self):
        """删除任务"""
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return

        task_id = self.table.item(selected, 0).text()

        reply = QMessageBox.question(
            self, "确认", f"确定要删除任务 {task_id} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.scheduler.remove_task(task_id)
            self.database.delete_task(task_id)
            self.refresh()
            self.task_updated.emit()

    def _run_task(self):
        """立即执行任务"""
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "警告", "请先选择一个任务")
            return

        task_id = self.table.item(selected, 0).text()
        self.scheduler.run_task_now(task_id)
        QMessageBox.information(self, "提示", f"任务 {task_id} 已加入执行队列")


class TaskDialog(QDialog):
    """任务编辑对话框"""

    def __init__(self, parent=None, task_data: dict = None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self._init_ui()

        if task_data:
            self._load_data()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("任务编辑")
        self.setMinimumWidth(500)

        layout = QFormLayout(self)

        # 任务名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入任务名称")
        layout.addRow("任务名称:", self.name_input)

        # 描述
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("输入任务描述")
        self.desc_input.setMaximumHeight(80)
        layout.addRow("描述:", self.desc_input)

        # 任务类型
        self.type_combo = QComboBox()
        self.type_combo.addItems(["自定义", "间隔执行", "Cron表达式"])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addRow("任务类型:", self.type_combo)

        # 间隔秒数
        self.interval_layout = QHBoxLayout()
        self.interval_input = QLineEdit()
        self.interval_input.setPlaceholderText("300")
        self.interval_layout.addWidget(self.interval_input)
        self.interval_layout.addWidget(QLabel("秒"))
        self.interval_layout.addStretch()
        layout.addRow("执行间隔:", self.interval_layout)

        # Cron表达式
        self.cron_layout = QHBoxLayout()
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("* * * * * (分 时 日 月 周)")
        self.cron_layout.addWidget(self.cron_input)
        self.cron_layout.addStretch()
        layout.addRow("Cron表达式:", self.cron_layout)

        # 启用
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        layout.addRow("启用:", self.enabled_check)

        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow("", btn_layout)

        self._on_type_changed("自定义")

    def _on_type_changed(self, text: str):
        """任务类型改变"""
        show_interval = text == "间隔执行"
        show_cron = text == "Cron表达式"

        # 找到并显示/隐藏相关行
        for i in range(layout.count()):
            label = layout.itemAt(i).widget()
            if isinstance(label, QLabel):
                text = label.text()
                if "执行间隔" in text:
                    layout.itemAt(i).widget().setVisible(show_interval)
                elif "Cron表达式" in text:
                    layout.itemAt(i).widget().setVisible(show_cron)

    def _load_data(self):
        """加载数据"""
        self.name_input.setText(self.task_data.get('name', ''))
        self.desc_input.setText(self.task_data.get('description', ''))

        task_type = self.task_data.get('task_type', 'custom')
        if task_type == 'interval':
            self.type_combo.setCurrentText("间隔执行")
            self.interval_input.setText(str(self.task_data.get('interval_seconds', 300)))
        elif task_type == 'cron':
            self.type_combo.setCurrentText("Cron表达式")
            self.cron_input.setText(self.task_data.get('cron_expr', ''))
        else:
            self.type_combo.setCurrentText("自定义")

        self.enabled_check.setChecked(self.task_data.get('enabled', True))

    def get_task_data(self) -> dict:
        """获取任务数据"""
        type_text = self.type_combo.currentText()

        if type_text == "间隔执行":
            task_type = 'interval'
            interval_seconds = int(self.interval_input.text() or 300)
        elif type_text == "Cron表达式":
            task_type = 'cron'
            interval_seconds = 0
        else:
            task_type = 'custom'
            interval_seconds = 0

        return {
            'name': self.name_input.text(),
            'description': self.desc_input.toPlainText(),
            'task_type': task_type,
            'cron_expr': self.cron_input.text(),
            'interval_seconds': interval_seconds,
            'enabled': self.enabled_check.isChecked(),
            'status': 'pending',
            'max_retries': 3,
            'config': {}
        }