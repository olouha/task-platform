"""
抓取任务标签页
用于配置网页抓取和浏览器自动化任务
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QDialog, QFormLayout, QLineEdit, QTextEdit,
                              QComboBox, QCheckBox, QMessageBox, QLabel,
                              QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal
import uuid
import logging
import json


class ScraperConfigTab(QWidget):
    """抓取配置标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # URL配置
        url_group = QGroupBox("抓取目标")
        url_layout = QFormLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addRow("目标URL:", self.url_input)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST"])
        url_layout.addRow("请求方法:", self.method_combo)

        url_group.setLayout(url_layout)
        main_layout.addWidget(url_group)

        # 选择器配置
        selector_group = QGroupBox("数据选择器")
        selector_layout = QFormLayout()

        self.items_selector = QLineEdit()
        self.items_selector.setPlaceholderText("tr.item, div.news-list li")
        selector_layout.addRow("列表项选择器:", self.items_selector)

        self.table_selector = QLineEdit()
        self.table_selector.setPlaceholderText("table.data-table")
        selector_layout.addRow("表格选择器:", self.table_selector)

        self.custom_selector = QLineEdit()
        self.custom_selector.setPlaceholderText(".price, #total")
        selector_layout.addRow("自定义选择器:", self.custom_selector)

        selector_group.setLayout(selector_layout)
        main_layout.addWidget(selector_group)

        # 高级配置
        advanced_group = QGroupBox("高级配置")
        advanced_layout = QFormLayout()

        self.timeout_input = QLineEdit()
        self.timeout_input.setText("30")
        advanced_layout.addRow("超时时间(秒):", self.timeout_input)

        self.headers_input = QTextEdit()
        self.headers_input.setMaximumHeight(80)
        self.headers_input.setPlaceholderText('{"Authorization": "Bearer xxx"}')
        advanced_layout.addRow("自定义请求头:", self.headers_input)

        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)

        main_layout.addStretch()

    def get_config(self) -> dict:
        """获取配置"""
        try:
            headers = json.loads(self.headers_input.toPlainText()) if self.headers_input.toPlainText() else {}
        except:
            headers = {}

        return {
            'url': self.url_input.text(),
            'method': self.method_combo.currentText().lower(),
            'selectors': {
                'items': self.items_selector.text(),
                'table': self.table_selector.text(),
                'custom': self.custom_selector.text()
            },
            'timeout': int(self.timeout_input.text() or 30),
            'headers': headers
        }


class BrowserConfigTab(QWidget):
    """浏览器自动化配置标签页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 浏览器配置
        browser_group = QGroupBox("浏览器设置")
        browser_layout = QFormLayout()

        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["Chromium", "Firefox", "Webkit"])
        browser_layout.addRow("浏览器类型:", self.browser_combo)

        self.headless_check = QCheckBox()
        self.headless_check.setChecked(True)
        browser_layout.addRow("无头模式:", self.headless_check)

        browser_group.setLayout(browser_layout)
        main_layout.addWidget(browser_group)

        # 步骤配置
        steps_group = QGroupBox("操作步骤")
        steps_layout = QVBoxLayout()

        self.steps_text = QTextEdit()
        self.steps_text.setPlaceholderText(
            '[\n'
            '  {"action": "goto", "url": "https://example.com"},\n'
            '  {"action": "wait", "selector": "#login-form", "timeout": 5000},\n'
            '  {"action": "fill", "selector": "#username", "value": "admin"},\n'
            '  {"action": "fill", "selector": "#password", "value": "pass"},\n'
            '  {"action": "click", "selector": "button[type=submit]"},\n'
            '  {"action": "wait", "selector": ".dashboard"},\n'
            '  {"action": "extract", "selector": "table", "type": "table"}\n'
            ']'
        )
        self.steps_text.setMinimumHeight(200)
        steps_layout.addWidget(self.steps_text)

        steps_group.setLayout(steps_layout)
        main_layout.addWidget(steps_group)

        # 选项
        options_group = QGroupBox("保存选项")
        options_layout = QFormLayout()

        self.save_html_check = QCheckBox()
        self.save_html_check.setChecked(True)
        options_layout.addRow("保存HTML:", self.save_html_check)

        self.screenshot_check = QCheckBox()
        options_layout.addRow("截图:", self.screenshot_check)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

    def get_config(self) -> dict:
        """获取配置"""
        steps = []
        try:
            steps = json.loads(self.steps_text.toPlainText())
        except:
            pass

        return {
            'browser': self.browser_combo.currentText().lower(),
            'headless': self.headless_check.isChecked(),
            'steps': steps,
            'save_html': self.save_html_check.isChecked(),
            'screenshot': self.screenshot_check.isChecked()
        }


class ScraperTab(QWidget):
    """抓取任务标签页"""

    task_updated = pyqtSignal()

    def __init__(self, scheduler, database, scraper_manager):
        super().__init__()
        self.scheduler = scheduler
        self.database = database
        self.scraper_manager = scraper_manager
        self.logger = logging.getLogger(__name__)
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 按钮栏
        btn_layout = QHBoxLayout()

        add_scraper_btn = QPushButton("添加网页抓取")
        add_scraper_btn.clicked.connect(lambda: self._add_task('scraper'))
        btn_layout.addWidget(add_scraper_btn)

        add_browser_btn = QPushButton("添加浏览器自动化")
        add_browser_btn.clicked.connect(lambda: self._add_task('browser'))
        btn_layout.addWidget(add_browser_btn)

        delete_btn = QPushButton("删除")
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "类型", "目标/URL", "调度规则", "状态"
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
            task_type = task.get('task_type', '')
            if task_type not in ['scraper', 'browser']:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(task.get('id', '')[:12]))

            # 名称
            self.table.setItem(row, 1, QTableWidgetItem(task.get('name', '')))

            # 类型
            type_text = {'scraper': '网页抓取', 'browser': '浏览器自动化'}.get(task_type, task_type)
            self.table.setItem(row, 2, QTableWidgetItem(type_text))

            # 目标/URL
            config = task.get('config', {})
            if task_type == 'scraper':
                target = config.get('url', '-')
            else:
                steps = config.get('steps', [])
                first_step = steps[0] if steps else {}
                target = first_step.get('url', '-')
            self.table.setItem(row, 3, QTableWidgetItem(target[:40]))

            # 调度规则
            if task.get('task_type') == 'interval':
                interval = task.get('interval_seconds', 0)
                rule = f"每 {interval} 秒"
            elif task.get('task_type') == 'cron':
                rule = task.get('cron_expr', '-')
            else:
                rule = '-'
            self.table.setItem(row, 4, QTableWidgetItem(rule))

            # 状态
            status = task.get('status', 'pending')
            self.table.setItem(row, 5, QTableWidgetItem(status))

    def _add_task(self, task_type: str):
        """添加任务"""
        if task_type == 'scraper':
            dialog = ScraperDialog(self)
        else:
            dialog = BrowserDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            task_data['id'] = str(uuid.uuid4())[:8]
            task_data['task_type'] = task_type

            # 保存到数据库
            self.database.save_task(task_data)

            # 添加到调度器
            from core.scheduler import Task
            task = Task(**task_data)
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


class ScraperDialog(QDialog):
    """网页抓取对话框"""

    def __init__(self, parent=None, task_data: dict = None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self._init_ui()

        if task_data:
            self._load_data()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("添加网页抓取任务")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # 任务基本信息
        info_group = QGroupBox("任务信息")
        info_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("任务名称")
        info_layout.addRow("任务名称:", self.name_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setPlaceholderText("任务描述")
        info_layout.addRow("描述:", self.desc_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 抓取配置
        self.scraper_config = ScraperConfigTab()
        layout.addWidget(self.scraper_config)

        # 调度配置
        schedule_group = QGroupBox("调度设置")
        schedule_layout = QFormLayout()

        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["手动触发", "间隔执行", "Cron表达式"])
        self.schedule_type_combo.currentTextChanged.connect(self._on_schedule_type_changed)
        schedule_layout.addRow("调度类型:", self.schedule_type_combo)

        self.interval_input = QLineEdit()
        self.interval_input.setText("300")
        schedule_layout.addRow("执行间隔(秒):", self.interval_input)

        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("* * * * * (分 时 日 月 周)")
        schedule_layout.addRow("Cron表达式:", self.cron_input)

        schedule_group.setLayout(schedule_layout)
        layout.addWidget(schedule_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._on_schedule_type_changed("手动触发")

    def _on_schedule_type_changed(self, text: str):
        """调度类型改变"""
        show_interval = text == "间隔执行"
        show_cron = text == "Cron表达式"

        self.interval_input.setVisible(show_interval)
        self.cron_input.setVisible(show_cron)

    def _load_data(self):
        """加载数据"""
        self.name_input.setText(self.task_data.get('name', ''))
        self.desc_input.setText(self.task_data.get('description', ''))

    def get_task_data(self) -> dict:
        """获取任务数据"""
        schedule_type = self.schedule_type_combo.currentText()

        task_type = 'custom'
        interval_seconds = 0
        cron_expr = ''

        if schedule_type == "间隔执行":
            task_type = 'interval'
            interval_seconds = int(self.interval_input.text() or 300)
        elif schedule_type == "Cron表达式":
            task_type = 'cron'
            cron_expr = self.cron_input.text()

        config = self.scraper_config.get_config()

        return {
            'name': self.name_input.text(),
            'description': self.desc_input.toPlainText(),
            'task_type': task_type,
            'cron_expr': cron_expr,
            'interval_seconds': interval_seconds,
            'enabled': True,
            'status': 'pending',
            'max_retries': 3,
            'config': config
        }


class BrowserDialog(QDialog):
    """浏览器自动化对话框"""

    def __init__(self, parent=None, task_data: dict = None):
        super().__init__(parent)
        self.task_data = task_data or {}
        self._init_ui()

        if task_data:
            self._load_data()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("添加浏览器自动化任务")
        self.setMinimumSize(600, 600)

        layout = QVBoxLayout(self)

        # 任务基本信息
        info_group = QGroupBox("任务信息")
        info_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("任务名称")
        info_layout.addRow("任务名称:", self.name_input)

        self.desc_input = QTextEdit()
        self.desc_input.setMaximumHeight(60)
        self.desc_input.setPlaceholderText("任务描述")
        info_layout.addRow("描述:", self.desc_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 浏览器配置
        self.browser_config = BrowserConfigTab()
        layout.addWidget(self.browser_config)

        # 调度配置
        schedule_group = QGroupBox("调度设置")
        schedule_layout = QFormLayout()

        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["手动触发", "间隔执行", "Cron表达式"])
        self.schedule_type_combo.currentTextChanged.connect(self._on_schedule_type_changed)
        schedule_layout.addRow("调度类型:", self.schedule_type_combo)

        self.interval_input = QLineEdit()
        self.interval_input.setText("3600")
        schedule_layout.addRow("执行间隔(秒):", self.interval_input)

        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("* * * * *")
        schedule_layout.addRow("Cron表达式:", self.cron_input)

        schedule_group.setLayout(schedule_layout)
        layout.addWidget(schedule_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        self._on_schedule_type_changed("手动触发")

    def _on_schedule_type_changed(self, text: str):
        """调度类型改变"""
        show_interval = text == "间隔执行"
        show_cron = text == "Cron表达式"

        self.interval_input.setVisible(show_interval)
        self.cron_input.setVisible(show_cron)

    def _load_data(self):
        """加载数据"""
        self.name_input.setText(self.task_data.get('name', ''))
        self.desc_input.setText(self.task_data.get('description', ''))

    def get_task_data(self) -> dict:
        """获取任务数据"""
        schedule_type = self.schedule_type_combo.currentText()

        task_type = 'custom'
        interval_seconds = 0
        cron_expr = ''

        if schedule_type == "间隔执行":
            task_type = 'interval'
            interval_seconds = int(self.interval_input.text() or 3600)
        elif schedule_type == "Cron表达式":
            task_type = 'cron'
            cron_expr = self.cron_input.text()

        config = self.browser_config.get_config()

        return {
            'name': self.name_input.text(),
            'description': self.desc_input.toPlainText(),
            'task_type': task_type,
            'cron_expr': cron_expr,
            'interval_seconds': interval_seconds,
            'enabled': True,
            'status': 'pending',
            'max_retries': 3,
            'config': config
        }