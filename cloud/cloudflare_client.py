"""
Cloudflare Workers 云端客户端
免费的数据存储服务
"""

import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CloudflareClient:
    """Cloudflare Workers API 客户端"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url.rstrip('/') if api_url else None
        self.timeout = 30

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求"""
        if not self.api_url:
            return None

        url = f"{self.api_url}{endpoint}"

        try:
            response = requests.request(
                method, url, timeout=self.timeout, **kwargs
            )

            if response.status_code in [200, 201]:
                try:
                    return response.json()
                except:
                    return {'data': response.text}

            logger.error(f"Request failed: {response.status_code} - {response.text}")
            return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        result = self._request('GET', '/health')
        return result is not None

    def get_data(self) -> Optional[Dict]:
        """获取所有数据"""
        return self._request('GET', '/data')

    def save_data(self, data: Dict) -> bool:
        """保存所有数据"""
        result = self._request('POST', '/save', json=data)
        return result is not None

    def save_task(self, task: Dict) -> bool:
        """保存任务"""
        task_id = task.get('id')
        if not task_id:
            return False
        result = self._request('PUT', f'/task/{task_id}', json=task)
        return result is not None

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        result = self._request('DELETE', f'/task/{task_id}')
        return result is not None

    def add_log(self, log: Dict) -> bool:
        """添加日志"""
        result = self._request('POST', '/log', json=log)
        return result is not None

    def get_stats(self) -> Optional[Dict]:
        """获取统计"""
        return self._request('GET', '/stats')


class CloudDatabase:
    """基于 Cloudflare Workers 的云端数据库"""

    def __init__(self, api_url: str = None):
        self.client = CloudflareClient(api_url)
        self.api_url = api_url
        self._data = {'tasks': [], 'logs': [], 'data': {}, 'config': {}}
        self._cache_time = 0
        self._cache_ttl = 30  # 缓存30秒
        self._dirty = False  # 是否有未保存的更改

    def _load(self) -> bool:
        """加载数据"""
        if self.api_url:
            data = self.client.get_data()
            if data:
                self._data = data
                self._cache_time = time.time()
                self._dirty = False
                return True
        return False

    def _save(self, force: bool = False) -> bool:
        """保存数据"""
        if not self.api_url:
            return False

        # 如果有未保存的更改，或者强制保存
        if self._dirty or force:
            if self.client.save_data(self._data):
                self._dirty = False
                return True

        return False

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.api_url:
            return True  # 本地模式始终有效
        return time.time() - self._cache_time < self._cache_ttl

    def _mark_dirty(self):
        """标记为已修改"""
        self._dirty = True

    # ========== 数据操作 ==========

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('tasks', [])

    def get_tasks(self) -> List[Dict]:
        """获取所有任务（别名）"""
        return self.get_all_tasks()

    def save_task(self, task: Dict) -> bool:
        """保存任务"""
        tasks = self._data.get('tasks', [])

        # 更新或添加
        found = False
        for i, t in enumerate(tasks):
            if t['id'] == task['id']:
                tasks[i] = task
                found = True
                break

        if not found:
            tasks.append(task)

        self._data['tasks'] = tasks
        self._mark_dirty()

        # 立即保存到云端
        return self._save()

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        self._data['tasks'] = [t for t in self._data.get('tasks', []) if t['id'] != task_id]
        self._mark_dirty()

        if self.api_url:
            self.client.delete_task(task_id)

        return True

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.get('id') == task_id:
                return task
        return None

    def get_logs(self, task_id: str = None) -> List[Dict]:
        """获取日志"""
        if not self._is_cache_valid():
            self._load()

        logs = self._data.get('logs', [])
        if task_id:
            logs = [l for l in logs if l.get('task_id') == task_id]
        return logs

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict]:
        """获取任务日志"""
        logs = self.get_logs(task_id)
        return logs[-limit:] if len(logs) > limit else logs

    def add_log(self, task_id: str, status: str, message: str = '', result: str = '') -> bool:
        """添加日志"""
        from datetime import datetime

        log = {
            'id': str(time.time() * 1000),
            'task_id': task_id,
            'status': status,
            'message': message,
            'result': result,
            'executed_at': datetime.now().isoformat()
        }

        self._data.setdefault('logs', []).append(log)
        self._mark_dirty()

        # 立即保存到云端
        if self.api_url:
            self.client.add_log(log)

        return True

    def get_data(self, key: str) -> Optional[Any]:
        """获取数据"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('data', {}).get(key)

    def save_data(self, key: str, value: Any) -> bool:
        """保存数据"""
        self._data.setdefault('data', {})[key] = value
        self._mark_dirty()
        return self._save()

    def get_config(self, key: str, default=None):
        """获取配置"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('config', {}).get(key, default)

    def save_config(self, key: str, value: Any) -> bool:
        """保存配置"""
        self._data.setdefault('config', {})[key] = value
        self._mark_dirty()
        return self._save()

    def get_stats(self) -> Dict:
        """获取统计"""
        if self.api_url:
            stats = self.client.get_stats()
            if stats:
                return stats

        return {
            'total_tasks': len(self._data.get('tasks', [])),
            'total_logs': len(self._data.get('logs', []))
        }

    def is_connected(self) -> bool:
        """检查连接"""
        if not self.api_url:
            return False
        return self.client.health_check()

    def sync(self) -> bool:
        """手动同步"""
        return self._save(force=True)

    def _get_cursor(self):
        """兼容本地数据库接口"""
        return None

    def _get_connection(self):
        """兼容本地数据库接口"""
        return None

    def close(self):
        """关闭连接（保存数据）"""
        self._save(force=True)