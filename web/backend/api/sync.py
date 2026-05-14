"""
数据同步 API
支持多人协作
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class SyncRequest(BaseModel):
    """同步请求"""
    user_id: str
    data_type: str  # projects, materials, price_history, etc.
    action: str  # push, pull
    data: Optional[List[dict]] = None
    last_sync: Optional[str] = None


class SyncResponse(BaseModel):
    """同步响应"""
    success: bool
    data: Optional[List[dict]] = None
    conflicts: Optional[List[dict]] = None
    synced_at: str


class User(BaseModel):
    """用户"""
    id: str
    name: str
    email: str
    role: str = "member"  # admin, member, viewer
    last_active: Optional[str] = None


# 模拟数据
_users_db = {}
_sync_history_db = []


@router.post("/connect")
async def connect_user(user_id: str):
    """用户连接"""
    if user_id not in _users_db:
        _users_db[user_id] = {
            'id': user_id,
            'name': f'用户_{user_id[:8]}',
            'connected_at': datetime.now().isoformat()
        }

    _users_db[user_id]['last_active'] = datetime.now().isoformat()

    return {
        'success': True,
        'user': _users_db[user_id],
        'online_users': len(_users_db)
    }


@router.post("/disconnect")
async def disconnect_user(user_id: str):
    """用户断开"""
    if user_id in _users_db:
        del _users_db[user_id]

    return {'success': True}


@router.get("/users")
async def list_online_users():
    """获取在线用户"""
    return list(_users_db.values())


@router.post("/push")
async def push_data(request: SyncRequest):
    """推送数据到服务器"""
    synced_at = datetime.now().isoformat()

    # 记录同步历史
    _sync_history_db.append({
        'user_id': request.user_id,
        'action': 'push',
        'data_type': request.data_type,
        'count': len(request.data) if request.data else 0,
        'synced_at': synced_at
    })

    return SyncResponse(
        success=True,
        synced_at=synced_at,
        data=request.data
    )


@router.post("/pull")
async def pull_data(request: SyncRequest):
    """从服务器拉取数据"""
    synced_at = datetime.now().isoformat()

    # 模拟返回数据
    # 实际应从数据库查询
    data = []

    # 记录同步历史
    _sync_history_db.append({
        'user_id': request.user_id,
        'action': 'pull',
        'data_type': request.data_type,
        'synced_at': synced_at
    })

    return SyncResponse(
        success=True,
        data=data,
        synced_at=synced_at
    )


@router.post("/sync")
async def sync_data(request: SyncRequest):
    """双向同步（冲突检测）"""
    synced_at = datetime.now().isoformat()

    # 检查冲突
    conflicts = []

    # 模拟冲突检测
    if request.data:
        for item in request.data:
            # 简单示例：检查是否有其他用户的更新
            pass

    return SyncResponse(
        success=True,
        synced_at=synced_at,
        conflicts=conflicts if conflicts else None
    )


@router.get("/history")
async def get_sync_history(user_id: str = None, limit: int = 50):
    """获取同步历史"""
    history = _sync_history_db

    if user_id:
        history = [h for h in history if h.get('user_id') == user_id]

    return history[-limit:]


@router.post("/lock")
async def lock_resource(resource_type: str, resource_id: str, user_id: str):
    """锁定资源（防止并发编辑）"""
    lock_key = f"{resource_type}:{resource_id}"

    # 简化实现：返回锁定状态
    return {
        'success': True,
        'locked': True,
        'lock_key': lock_key,
        'locked_by': user_id,
        'locked_at': datetime.now().isoformat()
    }


@router.post("/unlock")
async def unlock_resource(resource_type: str, resource_id: str, user_id: str):
    """解锁资源"""
    lock_key = f"{resource_type}:{resource_id}"

    return {
        'success': True,
        'unlocked': True,
        'lock_key': lock_key
    }


@router.get("/status")
async def get_sync_status():
    """获取同步状态"""
    return {
        'connected_users': len(_users_db),
        'total_syncs': len(_sync_history_db),
        'last_sync': _sync_history_db[-1] if _sync_history_db else None
    }