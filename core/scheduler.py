"""
核心调度器模块
负责管理定时任务的创建、调度、执行
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import time
import os

# 尝试导入 APScheduler，如果不存在则使用简单实现
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    description: str = ""
    task_type: str = "custom"  # cron, interval, custom
    cron_expr: str = ""  # 分 时 日 月 周
    interval_seconds: int = 0
    enabled: bool = True
    status: TaskStatus = TaskStatus.PENDING
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class Scheduler:
    """任务调度器"""

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.tasks: Dict[str, Task] = {}
        self.task_handlers: Dict[str, Callable] = {}

        # 加载配置
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'scheduler': {
                    'max_concurrent_tasks': 5,
                    'default_timeout': 300,
                    'retry_on_failure': True,
                    'max_retries': 3
                }
            }

        # 初始化调度器
        if HAS_APSCHEDULER:
            self.scheduler = BackgroundScheduler(
                job_defaults={
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 60
                }
            )
            self._use_apscheduler = True
        else:
            self._use_apscheduler = False
            self._simple_scheduler_running = False
            self._simple_thread = None

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.task_handlers[task_type] = handler
        self.logger.info(f"Registered handler for task type: {task_type}")

    def add_task(self, task: Task) -> bool:
        """添加任务"""
        try:
            if task.id in self.tasks:
                self.logger.warning(f"Task {task.id} already exists, updating...")
                self.remove_task(task.id)

            self.tasks[task.id] = task

            if self._use_apscheduler:
                self._add_task_apscheduler(task)
            else:
                self._schedule_simple_task(task)

            self.logger.info(f"Task added: {task.name} ({task.id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add task {task.id}: {e}")
            return False

    def _add_task_apscheduler(self, task: Task):
        """使用 APScheduler 添加任务"""
        trigger = None

        if task.task_type == 'cron' and task.cron_expr:
            parts = task.cron_expr.split()
            if len(parts) >= 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
        elif task.task_type == 'interval' and task.interval_seconds > 0:
            trigger = IntervalTrigger(seconds=task.interval_seconds)

        if trigger:
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                id=task.id,
                args=[task.id],
                replace_existing=True
            )

    def _schedule_simple_task(self, task: Task):
        """简单调度器实现"""
        pass  # 简单模式下由外部驱动

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        try:
            if task_id in self.tasks:
                if self._use_apscheduler:
                    self.scheduler.remove_job(task_id)
                del self.tasks[task_id]
                self.logger.info(f"Task removed: {task_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to remove task {task_id}: {e}")
            return False

    def start(self):
        """启动调度器"""
        if self._use_apscheduler:
            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("Scheduler started (APScheduler)")
        else:
            self._simple_scheduler_running = True
            self._simple_thread = threading.Thread(target=self._simple_scheduler_loop, daemon=True)
            self._simple_thread.start()
            self.logger.info("Scheduler started (Simple)")

    def stop(self):
        """停止调度器"""
        if self._use_apscheduler:
            self.scheduler.shutdown()
        else:
            self._simple_scheduler_running = False
        self.logger.info("Scheduler stopped")

    def _simple_scheduler_loop(self):
        """简单调度器主循环"""
        while self._simple_scheduler_running:
            now = datetime.now()
            for task_id, task in list(self.tasks.items()):
                if not task.enabled:
                    continue

                if task.next_run:
                    try:
                        # 处理 ISO 格式带 Z 后缀的情况
                        next_run_str = task.next_run.replace('Z', '+00:00')
                        next_run_time = datetime.fromisoformat(next_run_str)
                        if now >= next_run_time:
                            self._execute_task(task_id)
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"解析下次运行时间失败: {task.next_run}, {e}")
                        continue

            time.sleep(10)

    def _execute_task(self, task_id: str):
        """执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            return

        task.status = TaskStatus.RUNNING
        task.last_run = datetime.now().isoformat()

        try:
            handler = self.task_handlers.get(task.task_type)
            if handler:
                result = handler(task)
                task.status = TaskStatus.SUCCESS if result else TaskStatus.FAILED
            else:
                self.logger.warning(f"No handler for task type: {task.task_type}")
                task.status = TaskStatus.FAILED

            # 计算下次执行时间
            self._update_next_run(task)

        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.retry_count += 1

            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING

    def _update_next_run(self, task: Task):
        """更新任务下次执行时间"""
        now = datetime.now()
        if task.task_type == 'interval' and task.interval_seconds > 0:
            task.next_run = (now + timedelta(seconds=task.interval_seconds)).isoformat()
        elif task.task_type == 'cron' and task.cron_expr:
            # 解析 cron 表达式计算下次执行时间
            try:
                parts = task.cron_expr.split()
                if len(parts) >= 5:
                    minute, hour, day, month, day_of_week = parts[:5]
                    # 使用 APScheduler 计算下次执行时间
                    if HAS_APSCHEDULER:
                        trigger = CronTrigger(
                            minute=minute, hour=hour, day=day,
                            month=month, day_of_week=day_of_week
                        )
                        # APScheduler 没有直接计算下次时间的方法，使用简单估算
                        # 根据 cron 表达式推算下一个匹配的时间点
                        next_time = self._calculate_cron_next_run(
                            minute, hour, day, month, day_of_week
                        )
                        if next_time:
                            task.next_run = next_time.isoformat()
                        else:
                            # 回退：设置5分钟后
                            task.next_run = (now + timedelta(minutes=5)).isoformat()
                    else:
                        task.next_run = (now + timedelta(minutes=5)).isoformat()
                else:
                    task.next_run = (now + timedelta(minutes=5)).isoformat()
            except Exception as e:
                self.logger.warning(f"计算cron下次时间失败: {e}, 回退到5分钟后")
                task.next_run = (now + timedelta(minutes=5)).isoformat()
        else:
            # 无效任务类型或无cron表达式，默认5分钟
            task.next_run = (now + timedelta(minutes=5)).isoformat()

    def _calculate_cron_next_run(self, minute: str, hour: str, day: str, month: str, day_of_week: str):
        """根据cron表达式计算下次执行时间"""
        from dateutil.parser import parse as cron_parser
        import croniter

        try:
            # 构建 cron 表达式
            cron_expr = f"{minute} {hour} {day} {month} {day_of_week}"
            now = datetime.now()
            cron = croniter.croniter(cron_expr, now)
            return cron.get_next(datetime)
        except Exception:
            return None

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if task:
            return asdict(task)
        return None

    def list_tasks(self) -> list:
        """列出所有任务"""
        return [asdict(t) for t in self.tasks.values()]

    def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            if self._use_apscheduler:
                self.scheduler.pause_job(task_id)
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            if self._use_apscheduler:
                self.scheduler.resume_job(task_id)
            return True
        return False

    def run_task_now(self, task_id: str):
        """立即执行任务"""
        if task_id in self.tasks:
            threading.Thread(target=self._execute_task, args=[task_id]).start()