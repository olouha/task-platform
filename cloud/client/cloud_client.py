"""
云端客户端SDK
供桌面程序连接云端服务
"""

import requests
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CloudClient:
    """云端客户端"""

    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url.rstrip('/')
        self.timeout = 30

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求"""
        url = f"{self.server_url}{endpoint}"
        try:
            response = requests.request(
                method, url, timeout=self.timeout, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    # ========== 任务操作 ==========

    def get_tasks(self) -> List[Dict]:
        """获取所有任务"""
        result = self._request('GET', '/api/tasks')
        return result.get('data', []) if result else []

    def create_task(self, task_data: Dict) -> Optional[Dict]:
        """创建任务"""
        result = self._request('POST', '/api/tasks', json=task_data)
        return result.get('data') if result else None

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务"""
        result = self._request('GET', f'/api/tasks/{task_id}')
        return result.get('data') if result else None

    def update_task(self, task_id: str, task_data: Dict) -> Optional[Dict]:
        """更新任务"""
        result = self._request('PUT', f'/api/tasks/{task_id}', json=task_data)
        return result.get('data') if result else None

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        result = self._request('DELETE', f'/api/tasks/{task_id}')
        return result.get('success', False) if result else False

    def run_task(self, task_id: str) -> Optional[Dict]:
        """立即执行任务"""
        result = self._request('POST', f'/api/tasks/{task_id}/run')
        return result.get('data') if result else None

    # ========== 日志操作 ==========

    def get_logs(self, task_id: str = None) -> List[Dict]:
        """获取日志"""
        endpoint = '/api/logs'
        if task_id:
            endpoint += f'?task_id={task_id}'
        result = self._request('GET', endpoint)
        return result.get('data', []) if result else []

    # ========== 数据存储 ==========

    def get_data(self, key: str) -> Optional[Any]:
        """获取数据"""
        result = self._request('GET', f'/api/data/{key}')
        return result.get('data') if result else None

    def save_data(self, key: str, data: Any) -> bool:
        """保存数据"""
        result = self._request('POST', f'/api/data/{key}', json=data)
        return result.get('success', False) if result else False

    # ========== 系统操作 ==========

    def health_check(self) -> bool:
        """健康检查"""
        result = self._request('GET', '/api/health')
        return result.get('status') == 'ok' if result else False

    def get_stats(self) -> Optional[Dict]:
        """获取统计"""
        result = self._request('GET', '/api/stats')
        return result.get('data') if result else None

    def is_connected(self) -> bool:
        """检查连接"""
        return self.health_check()


class SyncManager:
    """同步管理器 - 本地数据与云端同步"""

    def __init__(self, local_db, cloud_client: CloudClient):
        self.local_db = local_db
        self.cloud = cloud_client
        self.mode = 'offline'  # offline, online, sync
        self.last_sync = None

    def set_mode(self, mode: str):
        """设置模式"""
        self.mode = mode

    def sync_tasks(self) -> bool:
        """同步任务"""
        try:
            if self.mode == 'offline':
                return False

            # 获取云端任务
            cloud_tasks = self.cloud.get_tasks()

            if self.mode == 'online':
                # 只读云端
                self.local_db._clear_tasks()
                for task in cloud_tasks:
                    self.local_db.save_task(task)

            elif self.mode == 'sync':
                # 双向同步
                local_tasks = self.local_db.get_all_tasks()

                # 上传本地新增的任务
                cloud_ids = {t['id'] for t in cloud_tasks}
                for task in local_tasks:
                    if task['id'] not in cloud_ids:
                        self.cloud.create_task(task)

                # 下载云端任务
                local_ids = {t['id'] for t in local_tasks}
                for task in cloud_tasks:
                    if task['id'] not in local_ids:
                        self.local_db.save_task(task)

            from datetime import datetime
            self.last_sync = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return False

    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            'mode': self.mode,
            'connected': self.cloud.is_connected(),
            'last_sync': self.last_sync.isoformat() if self.last_sync else None
        }