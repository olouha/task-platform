"""
数据导入导出功能
支持与朋友共享数据
"""

import json
import os
import shutil
from datetime import datetime


class DataSync:
    """数据同步工具"""

    def __init__(self, db):
        self.db = db

    def export_all_data(self, filepath: str = None) -> str:
        """导出所有数据"""
        if not filepath:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"data/export_{timestamp}.json"

        os.makedirs(os.path.dirname(filepath) or 'data', exist_ok=True)

        data = {
            'version': '1.0.0',
            'exported_at': datetime.now().isoformat(),
            'tasks': self.db.get_all_tasks(),
            'logs': self._get_all_logs(),
            'config': self.db.get_config('all_config', {})
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

    def import_all_data(self, filepath: str) -> tuple:
        """导入所有数据，返回 (成功数, 失败数)"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            imported_tasks = 0
            failed_tasks = 0

            # 导入任务
            for task in data.get('tasks', []):
                try:
                    self.db.save_task(task)
                    imported_tasks += 1
                except:
                    failed_tasks += 1

            return imported_tasks, failed_tasks

        except Exception as e:
            return 0, 0

    def _get_all_logs(self):
        """获取所有日志"""
        tasks = self.db.get_all_tasks()
        all_logs = []

        for task in tasks:
            task_id = task.get('id')
            if task_id:
                logs = self.db.get_task_logs(task_id, limit=100)
                all_logs.extend(logs)

        return all_logs

    def merge_data(self, filepath: str) -> dict:
        """合并数据（从朋友那里获取的数据）"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                incoming = json.load(f)

            result = {
                'added_tasks': 0,
                'updated_tasks': 0,
                'skipped_tasks': 0
            }

            existing_tasks = {t['id']: t for t in self.db.get_all_tasks()}

            for task in incoming.get('tasks', []):
                task_id = task.get('id')

                if task_id not in existing_tasks:
                    # 新增
                    self.db.save_task(task)
                    result['added_tasks'] += 1
                else:
                    # 比较更新时间，保留最新的
                    existing = existing_tasks[task_id]
                    existing_time = existing.get('updated_at', '')
                    incoming_time = task.get('updated_at', '')

                    if incoming_time > existing_time:
                        self.db.save_task(task)
                        result['updated_tasks'] += 1
                    else:
                        result['skipped_tasks'] += 1

            return result

        except Exception as e:
            return {'error': str(e)}

    def get_share_package(self) -> str:
        """生成分享包"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"TaskPlatform_Share_{timestamp}.json"
        return self.export_all_data(f"data/{filename}")

    def load_share_package(self, filepath: str, merge: bool = True) -> dict:
        """加载分享包"""
        if merge:
            return self.merge_data(filepath)
        else:
            return self.import_all_data(filepath)
