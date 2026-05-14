"""
仪表盘标签页
显示系统概览和统计信息
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QFrame, QGridLayout, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import datetime


class DashboardTab(QWidget):
    """仪表盘标签页"""

    def __init__(self, scheduler, database):
        super().__init__()
        self.scheduler = scheduler
        self.database = database
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)

        # 标题
        title = QLabel("系统概览")
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px;")
        main_layout.addWidget(title)

        # 统计卡片区域
        stats_layout = QGridLayout()
        stats_layout.setSpacing(20)

        # 总任务数
        self.total_card = self._create_stat_card("总任务数", "0", "#3498db")
        stats_layout.addWidget(self.total_card, 0, 0)

        # 运行中
        self.running_card = self._create_stat_card("运行中", "0", "#2ecc71")
        stats_layout.addWidget(self.running_card, 0, 1)

        # 成功
        self.success_card = self._create_stat_card("执行成功", "0", "#27ae60")
        stats_layout.addWidget(self.success_card, 0, 2)

        # 失败
        self.failed_card = self._create_stat_card("执行失败", "0", "#e74c3c")
        stats_layout.addWidget(self.failed_card, 0, 3)

        main_layout.addLayout(stats_layout)

        # 最近任务区域
        recent_label = QLabel("最近执行记录")
        recent_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px 10px 5px 10px;")
        main_layout.addWidget(recent_label)

        # 最近日志
        self.recent_logs = QLabel("暂无执行记录")
        self.recent_logs.setStyleSheet("padding: 10px; background: #f5f5f5; border-radius: 5px;")
        self.recent_logs.setMinimumHeight(200)
        main_layout.addWidget(self.recent_logs)

        # 快速操作
        quick_actions = QHBoxLayout()

        start_btn = QPushButton("启动调度器")
        start_btn.clicked.connect(self._start_scheduler)
        quick_actions.addWidget(start_btn)

        stop_btn = QPushButton("停止调度器")
        stop_btn.clicked.connect(self._stop_scheduler)
        quick_actions.addWidget(stop_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        quick_actions.addWidget(refresh_btn)

        quick_actions.addStretch()

        main_layout.addLayout(quick_actions)
        main_layout.addStretch()

    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 10px;
                border-left: 4px solid {color};
                padding: 15px;
            }}
        """)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 14px;")

        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return card

    def refresh(self):
        """刷新数据"""
        tasks = self.scheduler.list_tasks()

        total = len(tasks)
        running = sum(1 for t in tasks if t.get('status') == 'running')
        enabled = sum(1 for t in tasks if t.get('enabled', False))

        # 更新卡片
        self._update_card(self.total_card, total)
        self._update_card(self.running_card, running)

        # 计算成功/失败
        success_count = 0
        failed_count = 0
        for task_id in [t.get('id') for t in tasks]:
            logs = self.database.get_task_logs(task_id, limit=50)
            success_count += sum(1 for log in logs if log.get('status') == 'success')
            failed_count += sum(1 for log in logs if log.get('status') == 'failed')

        self._update_card(self.success_card, success_count)
        self._update_card(self.failed_card, failed_count)

        # 更新最近日志
        all_logs = []
        for task_id in [t.get('id') for t in tasks][:5]:
            logs = self.database.get_task_logs(task_id, limit=3)
            all_logs.extend(logs)

        all_logs.sort(key=lambda x: x.get('executed_at', ''), reverse=True)
        all_logs = all_logs[:10]

        if all_logs:
            log_text = "<table width='100%' cellspacing='5'>"
            log_text += "<tr style='background:#ddd'><th>时间</th><th>任务</th><th>状态</th><th>消息</th></tr>"

            for log in all_logs:
                status_color = "#2ecc71" if log.get('status') == 'success' else "#e74c3c"
                status_icon = "✓" if log.get('status') == 'success' else "✗"

                executed_at = log.get('executed_at', '')[:19] if log.get('executed_at') else '-'
                task_id = log.get('task_id', '-')[:15]
                message = log.get('message', '-')[:40]

                log_text += f"""
                    <tr>
                        <td>{executed_at}</td>
                        <td>{task_id}</td>
                        <td><span style='color:{status_color}'>{status_icon} {log.get('status', '-')}</span></td>
                        <td>{message}</td>
                    </tr>
                """

            log_text += "</table>"
            self.recent_logs.setText(log_text)
        else:
            self.recent_logs.setText("暂无执行记录")

    def _update_card(self, card: QFrame, value: int):
        """更新卡片值"""
        value_label = card.findChildren(QLabel)[1]
        value_label.setText(str(value))

    def _start_scheduler(self):
        """启动调度器"""
        self.scheduler.start()

    def _stop_scheduler(self):
        """停止调度器"""
        self.scheduler.stop()