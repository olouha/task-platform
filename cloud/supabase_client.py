"""
Supabase 云端数据库客户端
"""

import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase REST API 客户端"""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        self.timeout = 30

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求"""
        url = f"{self.url}/rest/v1{endpoint}"

        try:
            response = requests.request(
                method, url, headers=self.headers, timeout=self.timeout, **kwargs
            )

            if response.status_code in [200, 201, 204]:
                if response.text:
                    return response.json()
                return {'success': True}

            logger.error(f"Request failed: {response.status_code} - {response.text}")
            return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_tasks(self) -> List[Dict]:
        """获取所有任务"""
        result = self._request('GET', '/tasks?select=*&order=created_at.desc')
        return result if result else []

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        result = self._request('GET', f'/tasks?id=eq.{task_id}&select=*')
        if result and len(result) > 0:
            return result[0]
        return None

    def create_task(self, task: Dict) -> bool:
        """创建任务"""
        task['id'] = task.get('id', str(time.time() * 1000))
        return self._request('POST', '/tasks', json=task) is not None

    def update_task(self, task_id: str, task: Dict) -> bool:
        """更新任务"""
        return self._request('PATCH', f'/tasks?id=eq.{task_id}', json=task) is not None

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return self._request('DELETE', f'/tasks?id=eq.{task_id}') is not None

    def get_logs(self, task_id: str = None, limit: int = 100) -> List[Dict]:
        """获取日志"""
        endpoint = '/logs?select=*&order=executed_at.desc'
        if task_id:
            endpoint = f'/logs?task_id=eq.{task_id}&select=*&order=executed_at.desc'
        result = self._request('GET', endpoint)
        return result if result else []

    def add_log(self, log: Dict) -> bool:
        """添加日志"""
        log['id'] = log.get('id', str(time.time() * 1000))
        return self._request('POST', '/logs', json=log) is not None

    def health_check(self) -> bool:
        """健康检查"""
        result = self._request('GET', '/tasks?select=id&limit=1')
        return result is not None


class CloudDatabase:
    """基于 Supabase 的云端数据库"""

    def __init__(self, url: str = None, api_key: str = None):
        if not url or not api_key:
            # 从配置文件读取
            import os
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'cloud.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    url = config.get('supabase_url')
                    api_key = config.get('supabase_key')

        self.client = SupabaseClient(url, api_key)
        self.url = url
        self.api_key = api_key

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return self.client.get_tasks()

    def get_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return self.get_all_tasks()

    def save_task(self, task: Dict) -> bool:
        """保存任务"""
        existing = self.client.get_task(task['id'])
        if existing:
            return self.client.update_task(task['id'], task)
        else:
            return self.client.create_task(task)

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return self.client.delete_task(task_id)

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取单个任务"""
        return self.client.get_task(task_id)

    def get_logs(self, task_id: str = None) -> List[Dict]:
        """获取日志"""
        return self.client.get_logs(task_id)

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict]:
        """获取任务日志"""
        return self.client.get_logs(task_id, limit)

    def add_log(self, task_id: str, status: str, message: str = '', result: str = '') -> bool:
        """添加日志"""
        from datetime import datetime
        log = {
            'task_id': task_id,
            'status': status,
            'message': message,
            'result': result,
            'executed_at': datetime.now().isoformat()
        }
        return self.client.add_log(log)

    def get_config(self, key: str, default=None):
        """获取配置（简化版，返回空）"""
        return default

    def save_config(self, key: str, value: Any) -> bool:
        """保存配置（简化版）"""
        return True

    def get_stats(self) -> Dict:
        """获取统计"""
        tasks = self.get_tasks()
        return {
            'total_tasks': len(tasks),
            'total_logs': len(self.get_logs())
        }

    def is_connected(self) -> bool:
        """检查连接"""
        return self.client.health_check()

    def _get_cursor(self):
        """兼容接口"""
        return None

    def _get_connection(self):
        """兼容接口"""
        return None

    def close(self):
        """关闭连接"""
        pass
