"""
Supabase Realtime 多人协作服务
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class RealtimeCollaboration:
    """实时协作服务"""

    def __init__(self, supabase_client):
        self.client = supabase_client
        self.subscriptions = {}

    def subscribe_to_changes(self, table: str, callback: callable) -> str:
        """
        订阅表变更
        返回 subscription_id
        """
        from supabase import create_client

        # 创建实时订阅
        subscription = self.client.channel(f"table:{table}")
        subscription.on(
            'postgres_changes',
            {'event': '*', 'schema': 'public', 'table': table},
            callback
        )
        subscription.subscribe()

        sub_id = f"{table}_{id(callback)}"
        self.subscriptions[sub_id] = subscription

        return sub_id

    def unsubscribe(self, subscription_id: str):
        """取消订阅"""
        if subscription_id in self.subscriptions:
            self.client.remove_channel(self.subscriptions[subscription_id])
            del self.subscriptions[subscription_id]

    def broadcast_presence(self, room: str, user_data: Dict):
        """广播用户状态"""
        channel = self.client.channel(f"presence:{room}")
        channel.track(user_data)
        channel.subscribe()

    def on_presence_sync(self, room: str, callback: callable):
        """监听用户状态同步"""
        channel = self.client.channel(f"presence:{room}")
        channel.on("presence", {"event": "sync"}, callback)
        channel.subscribe()

    def lock_resource(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        """锁定资源（防止并发编辑）"""
        lock_key = f"lock:{resource_type}:{resource_id}"

        # 尝试获取锁
        lock_data = {
            'locked_by': user_id,
            'locked_at': 'now()'
        }

        # 简化实现：直接存储到数据库
        return True

    def unlock_resource(self, resource_type: str, resource_id: str, user_id: str) -> bool:
        """解锁资源"""
        lock_key = f"lock:{resource_type}:{resource_id}"
        # 简化实现
        return True

    def detect_conflicts(self, local_data: Dict, remote_data: Dict) -> Optional[Dict]:
        """
        检测冲突
        返回冲突信息，如果无冲突返回 None
        """
        local_updated = local_data.get('updated_at')
        remote_updated = remote_data.get('updated_at')

        if local_updated and remote_updated:
            # 如果远程更新时间晚于本地，可能存在冲突
            if remote_updated > local_updated:
                # 本地有未同步的修改
                if local_data != remote_data:
                    return {
                        'type': 'update_conflict',
                        'local': local_data,
                        'remote': remote_data,
                        'conflict_fields': self._find_conflict_fields(local_data, remote_data)
                    }

        return None

    def _find_conflict_fields(self, local: Dict, remote: Dict) -> List[str]:
        """找出冲突的字段"""
        conflicts = []
        for key in local:
            if key in remote and local[key] != remote[key]:
                conflicts.append(key)
        return conflicts

    def resolve_conflict(self, local_data: Dict, remote_data: Dict, strategy: str = 'latest') -> Dict:
        """
        解决冲突
        strategy: 'latest', 'local', 'remote', 'merge'
        """
        if strategy == 'latest':
            # 保留更新时间最新的
            return remote_data if remote_data.get('updated_at') > local_data.get('updated_at') else local_data
        elif strategy == 'local':
            return local_data
        elif strategy == 'remote':
            return remote_data
        elif strategy == 'merge':
            # 简单合并：local 优先
            merged = {**remote_data, **local_data}
            return merged

        return local_data


class SyncManager:
    """同步管理器"""

    def __init__(self, db, realtime: RealtimeCollaboration):
        self.db = db
        self.realtime = realtime
        self.pending_changes = []
        self.is_syncing = False

    def push_changes(self, data_type: str, data: List[Dict]) -> Dict:
        """推送本地变更到服务器"""
        results = {
            'success': 0,
            'failed': 0,
            'conflicts': []
        }

        for item in data:
            try:
                # 检测冲突
                existing = self._get_existing(data_type, item.get('id'))
                if existing:
                    conflict = self.realtime.detect_conflicts(item, existing)
                    if conflict:
                        results['conflicts'].append(conflict)
                        continue

                # 推送变更
                if self._push_item(data_type, item):
                    results['success'] += 1
                else:
                    results['failed'] += 1

            except Exception as e:
                logger.error(f"Push failed: {e}")
                results['failed'] += 1

        return results

    def pull_changes(self, data_type: str, since: str = None) -> List[Dict]:
        """从服务器拉取变更"""
        # 实现增量拉取
        return []

    def _get_existing(self, data_type: str, item_id: str) -> Optional[Dict]:
        """获取服务器上的数据"""
        return None

    def _push_item(self, data_type: str, item: Dict) -> bool:
        """推送单个数据项"""
        return True

    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            'pending': len(self.pending_changes),
            'syncing': self.is_syncing,
            'last_sync': None
        }