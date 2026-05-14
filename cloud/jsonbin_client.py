"""
JSONBin.io 云端存储客户端
免费的 JSON 数据存储服务
"""

import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class JSONBinClient:
    """JSONBin.io 客户端"""

    def __init__(self, api_key: str = None, collection_id: str = None):
        # JSONBin.io API 地址
        self.base_url = "https://jsonbin.io/api/v1"

        # API Key（可选，用于私有bin）
        self.api_key = api_key or "free-tier"

        # Collection ID（可选，用于组织多个bin）
        self.collection_id = collection_id

        # 默认 headers
        self.headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': self.api_key,
            'X-Access-Key': self.api_key
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()

        # 如果有自定义 key
        if 'key' in kwargs:
            headers['X-Access-Key'] = kwargs.pop('key')

        try:
            response = requests.request(
                method, url, headers=headers, **kwargs, timeout=30
            )

            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error(f"Request failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    # ========== Collection 操作 ==========

    def create_collection(self, name: str = "TaskPlatform") -> Optional[str]:
        """创建 Collection"""
        data = {
            "name": name,
            "description": "TaskPlatform shared database"
        }

        result = self._request('POST', '/collection', json=data)
        if result and 'id' in result:
            return result['id']
        return None

    def get_collection(self, collection_id: str) -> Optional[Dict]:
        """获取 Collection"""
        return self._request('GET', f'/collection/{collection_id}')

    # ========== Bin 操作 ==========

    def create_bin(self, data: Any, collection_id: str = None) -> Optional[str]:
        """创建 Bin，返回 bin ID"""
        payload = json.dumps(data) if not isinstance(data, str) else data

        endpoint = '/b'
        if collection_id:
            endpoint = f'/collection/{collection_id}/bin'

        result = self._request('POST', endpoint, data=payload)

        if result and 'metadata' in result:
            bin_id = result['metadata']['id']
            logger.info(f"Created bin: {bin_id}")
            return bin_id

        return None

    def read_bin(self, bin_id: str) -> Optional[Dict]:
        """读取 Bin"""
        return self._request('GET', f'/b/{bin_id}')

    def update_bin(self, bin_id: str, data: Any) -> bool:
        """更新 Bin"""
        payload = json.dumps(data) if not isinstance(data, str) else data

        result = self._request('PUT', f'/b/{bin_id}', data=payload)
        return result is not None

    def patch_bin(self, bin_id: str, data: Dict) -> bool:
        """部分更新 Bin"""
        result = self._request('PATCH', f'/b/{bin_id}', json=data)
        return result is not None

    def delete_bin(self, bin_id: str) -> bool:
        """删除 Bin"""
        result = self._request('DELETE', f'/b/{bin_id}')
        return result is not None

    # ========== 健康检查 ==========

    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(
                "https://jsonbin.io/api/v1/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


class CloudDatabase:
    """基于 JSONBin.io 的云端数据库"""

    def __init__(self, master_key: str = None, bin_id: str = None):
        self.client = JSONBinClient(api_key=master_key)
        self.bin_id = bin_id
        self._data = {'tasks': [], 'logs': [], 'data': {}, 'config': {}}
        self._cache_time = 0
        self._cache_ttl = 60  # 缓存60秒

    def _load(self) -> bool:
        """加载数据"""
        if self.bin_id:
            result = self.client.read_bin(self.bin_id)
            if result and 'record' in result:
                self._data = result['record']
                self._cache_time = time.time()
                return True
        return False

    def _save(self) -> bool:
        """保存数据"""
        if self.bin_id:
            return self.client.update_bin(self.bin_id, self._data)
        else:
            # 创建新 bin
            self.bin_id = self.client.create_bin(self._data)
            return self.bin_id is not None

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.bin_id:
            return False
        return time.time() - self._cache_time < self._cache_ttl

    # ========== 数据操作 ==========

    def get_tasks(self) -> List[Dict]:
        """获取所有任务"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('tasks', [])

    def save_task(self, task: Dict) -> bool:
        """保存任务"""
        tasks = self.get_tasks()

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
        return self._save()

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        tasks = self.get_tasks()
        self._data['tasks'] = [t for t in tasks if t['id'] != task_id]
        return self._save()

    def get_logs(self, task_id: str = None) -> List[Dict]:
        """获取日志"""
        if not self._is_cache_valid():
            self._load()

        logs = self._data.get('logs', [])
        if task_id:
            logs = [l for l in logs if l.get('task_id') == task_id]
        return logs

    def add_log(self, task_id: str, status: str, message: str = '') -> bool:
        """添加日志"""
        from datetime import datetime

        if not self._is_cache_valid():
            self._load()

        log = {
            'id': str(time.time() * 1000),
            'task_id': task_id,
            'status': status,
            'message': message,
            'executed_at': datetime.now().isoformat()
        }

        self._data.setdefault('logs', []).append(log)

        # 只保留最近1000条日志
        if len(self._data['logs']) > 1000:
            self._data['logs'] = self._data['logs'][-1000:]

        return self._save()

    def get_data(self, key: str) -> Optional[Any]:
        """获取数据"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('data', {}).get(key)

    def save_data(self, key: str, value: Any) -> bool:
        """保存数据"""
        if not self._is_cache_valid():
            self._load()

        self._data.setdefault('data', {})[key] = value
        return self._save()

    def get_config(self, key: str, default=None):
        """获取配置"""
        if not self._is_cache_valid():
            self._load()
        return self._data.get('config', {}).get(key, default)

    def save_config(self, key: str, value: Any) -> bool:
        """保存配置"""
        if not self._is_cache_valid():
            self._load()

        self._data.setdefault('config', {})[key] = value
        return self._save()

    def get_stats(self) -> Dict:
        """获取统计"""
        if not self._is_cache_valid():
            self._load()

        return {
            'total_tasks': len(self._data.get('tasks', [])),
            'enabled_tasks': sum(1 for t in self._data.get('tasks', []) if t.get('enabled')),
            'total_logs': len(self._data.get('logs', [])),
            'stored_data_keys': len(self._data.get('data', {}))
        }

    def is_connected(self) -> bool:
        """检查连接"""
        return self.client.health_check()

    def init_bin(self, data: Dict = None) -> str:
        """初始化 bin"""
        self._data = data or {'tasks': [], 'logs': [], 'data': {}, 'config': {}}
        self.bin_id = self.client.create_bin(self._data)
        return self.bin_id

    def get_bin_id(self) -> str:
        """获取 bin ID"""
        return self.bin_id