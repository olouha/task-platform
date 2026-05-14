"""
GitHub Gist 云端存储客户端
使用 GitHub Gist 作为免费的共享数据库
"""

import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GistClient:
    """GitHub Gist 客户端"""

    def __init__(self, token: str = None):
        self.base_url = "https://api.github.com"
        self.token = token

        self.headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

        if token:
            self.headers['Authorization'] = f'Bearer {token}'

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, **kwargs, timeout=30
            )

            if response.status_code in [200, 201]:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Request failed: {response.status_code} - {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def create_gist(self, content: Dict, filename: str = "taskplatform.json", description: str = "TaskPlatform shared data") -> Optional[str]:
        """创建 Gist"""
        data = {
            "description": description,
            "public": True,
            "files": {
                filename: {
                    "content": json.dumps(content, indent=2, ensure_ascii=False)
                }
            }
        }

        result = self._request('POST', '/gists', json=data)

        if result and 'id' in result:
            gist_id = result['id']
            logger.info(f"Created gist: {gist_id}")
            return gist_id

        return None

    def get_gist(self, gist_id: str) -> Optional[Dict]:
        """获取 Gist"""
        result = self._request('GET', f'/gists/{gist_id}')

        if result and 'files' in result:
            for filename, file_data in result['files'].items():
                if 'content' in file_data:
                    try:
                        return json.loads(file_data['content'])
                    except:
                        return None

        return None

    def update_gist(self, gist_id: str, content: Dict, filename: str = "taskplatform.json") -> bool:
        """更新 Gist"""
        data = {
            "files": {
                filename: {
                    "content": json.dumps(content, indent=2, ensure_ascii=False)
                }
            }
        }

        result = self._request('PATCH', f'/gists/{gist_id}', json=data)
        return result is not None

    def delete_gist(self, gist_id: str) -> bool:
        """删除 Gist"""
        result = self._request('DELETE', f'/gists/{gist_id}')
        return result is not None

    def get_public_gist(self, gist_id: str) -> Optional[Dict]:
        """获取公开 Gist（无需 token）"""
        url = f"https://api.github.com/gists/{gist_id}"
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                result = response.json()
                for filename, file_data in result['files'].items():
                    if 'content' in file_data:
                        try:
                            return json.loads(file_data['content'])
                        except:
                            return None
            return None
        except Exception as e:
            logger.error(f"Failed to get public gist: {e}")
            return None

    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/zen", timeout=5)
            return response.status_code == 200
        except:
            return False


class CloudDatabase:
    """基于 GitHub Gist 的云端数据库"""

    def __init__(self, gist_id: str = None, token: str = None):
        self.client = GistClient(token=token)
        self.gist_id = gist_id
        self._data = {'tasks': [], 'logs': [], 'data': {}, 'config': {}}
        self._cache_time = 0
        self._cache_ttl = 30  # 缓存30秒
        self._read_only = token is None  # 无 token 则只读

    def _load(self) -> bool:
        """加载数据"""
        if self.gist_id:
            if self._read_only:
                # 公开 Gist
                data = self.client.get_public_gist(self.gist_id)
            else:
                # 私有 Gist
                data = self.client.get_gist(self.gist_id)

            if data:
                self._data = data
                self._cache_time = time.time()
                return True
        return False

    def _save(self) -> bool:
        """保存数据"""
        if not self.gist_id:
            return False

        if self._read_only:
            logger.warning("Read-only mode, cannot save")
            return False

        return self.client.update_gist(self.gist_id, self._data)

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.gist_id:
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

    def init_gist(self, data: Dict = None) -> Optional[str]:
        """初始化 Gist"""
        if not self._read_only:
            self._data = data or {'tasks': [], 'logs': [], 'data': {}, 'config': {}}
            self.gist_id = self.client.create_gist(self._data)
            return self.gist_id
        return None

    def get_gist_id(self) -> str:
        """获取 Gist ID"""
        return self.gist_id

    def is_read_only(self) -> bool:
        """是否只读"""
        return self._read_only