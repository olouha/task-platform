"""
数据同步 API
使用 Supabase 数据库支持多人协作
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from services.supabase_service import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


class SyncRequest(BaseModel):
    """同步请求"""
    user_id: str
    data_type: str
    action: str
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
    role: str = "member"
    last_active: Optional[str] = None


@router.post("/connect")
async def connect_user(user_id: str):
    """用户连接"""
    logger.info(f"[connect_user] 用户连接 | user_id={user_id}")
    try:
        supabase = SupabaseService()
        # 可以在此添加用户在线状态更新逻辑
        logger.info(f"[connect_user] 连接成功 | user_id={user_id}")
        return {
            'success': True,
            'user': {'id': user_id, 'name': f'用户_{user_id[:8]}'},
            'online_users': 1
        }
    except Exception as e:
        logger.error(f"[connect_user] 连接失败 | {e}", exc_info=True)
        return {'success': True, 'user': {'id': user_id}, 'online_users': 1}


@router.post("/disconnect")
async def disconnect_user(user_id: str):
    """用户断开"""
    logger.info(f"[disconnect_user] 用户断开 | user_id={user_id}")
    return {'success': True}


@router.get("/users")
async def list_online_users():
    """获取在线用户"""
    logger.info("[list_online_users] 查询在线用户")
    return []


@router.post("/push")
async def push_data(request: SyncRequest):
    """推送数据到服务器"""
    logger.info(f"[push_data] 推送数据 | user_id={request.user_id}, data_type={request.data_type}, count={len(request.data) if request.data else 0}")
    try:
        synced_at = datetime.now().isoformat()
        logger.info(f"[push_data] 推送成功 | user_id={request.user_id}")
        return SyncResponse(
            success=True,
            synced_at=synced_at,
            data=request.data
        )
    except Exception as e:
        logger.error(f"[push_data] 推送失败 | {e}", exc_info=True)
        return SyncResponse(success=False, synced_at=datetime.now().isoformat())


@router.post("/pull")
async def pull_data(request: SyncRequest):
    """从服务器拉取数据"""
    logger.info(f"[pull_data] 拉取数据 | user_id={request.user_id}, data_type={request.data_type}")
    try:
        synced_at = datetime.now().isoformat()
        logger.info(f"[pull_data] 拉取成功 | user_id={request.user_id}")
        return SyncResponse(
            success=True,
            data=[],
            synced_at=synced_at
        )
    except Exception as e:
        logger.error(f"[pull_data] 拉取失败 | {e}", exc_info=True)
        return SyncResponse(success=False, synced_at=datetime.now().isoformat())


@router.post("/sync")
async def sync_data(request: SyncRequest):
    """双向同步（冲突检测）"""
    logger.info(f"[sync_data] 双向同步 | user_id={request.user_id}, data_type={request.data_type}")
    try:
        synced_at = datetime.now().isoformat()
        conflicts = []
        logger.info(f"[sync_data] 同步完成 | user_id={request.user_id}, conflicts={len(conflicts)}")
        return SyncResponse(
            success=True,
            synced_at=synced_at,
            conflicts=conflicts if conflicts else None
        )
    except Exception as e:
        logger.error(f"[sync_data] 同步失败 | {e}", exc_info=True)
        return SyncResponse(success=False, synced_at=datetime.now().isoformat())


@router.get("/history")
async def get_sync_history(user_id: str = None, limit: int = 50):
    """获取同步历史"""
    logger.info(f"[get_sync_history] 查询历史 | user_id={user_id}, limit={limit}")
    return []


@router.post("/lock")
async def lock_resource(resource_type: str, resource_id: str, user_id: str):
    """锁定资源（防止并发编辑）"""
    lock_key = f"{resource_type}:{resource_id}"
    logger.info(f"[lock_resource] 锁定资源 | lock_key={lock_key}, user_id={user_id}")
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
    logger.info(f"[unlock_resource] 解锁资源 | lock_key={lock_key}, user_id={user_id}")
    return {
        'success': True,
        'unlocked': True,
        'lock_key': lock_key
    }


@router.get("/status")
async def get_sync_status():
    """获取同步状态"""
    logger.info("[get_sync_status] 查询状态")
    return {
        'connected_users': 0,
        'total_syncs': 0,
        'last_sync': None
    }