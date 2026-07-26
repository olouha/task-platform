"""
用户认证API
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List
import logging

from services.auth_service import user_service, session_manager

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    account: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    session_id: str
    account: str
    position: str
    permissions: str
    is_admin: bool
    online_count: int


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserInfo(BaseModel):
    account: str
    position: str
    permissions: str
    is_admin: bool


class UserWithPassword(BaseModel):
    account: str
    password: str
    position: str
    permissions: str


class AddUserRequest(BaseModel):
    account: str
    password: str
    position: str
    permissions: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    logger.info(f"[login] 登录请求 | account={request.account}")

    # 验证密码
    if not user_service.verify_password(request.account, request.password):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    # 获取用户信息
    user = user_service.get_user(request.account)
    if not user:
        raise HTTPException(status_code=401, detail="账号不存在")

    # 创建会话（支持同一账号多人同时在线）
    session_id = session_manager.create_session(request.account)
    online_count = session_manager.get_online_count(request.account)

    logger.info(f"[login] 登录成功 | account={request.account}, online_count={online_count}")

    return LoginResponse(
        success=True,
        session_id=session_id,
        account=user['account'],
        position=user['position'],
        permissions=user['permissions'],
        is_admin=user['is_admin'],
        online_count=online_count
    )


@router.post("/logout")
async def logout(x_session_id: str = Header(..., alias="X-Session-ID")):
    """用户登出"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    session_manager.remove_session(x_session_id)
    logger.info(f"[logout] 登出成功 | account={account}")

    return {"success": True, "message": "登出成功"}


@router.get("/user-info")
async def get_user_info(x_session_id: str = Header(..., alias="X-Session-ID")):
    """获取当前用户信息"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    user = user_service.get_user(account)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        **user,
        "online_count": session_manager.get_online_count(account),
        "total_online": session_manager.get_all_online_count()
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    """修改密码"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    if len(request.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少4位")

    if user_service.update_password(account, request.old_password, request.new_password):
        logger.info(f"[change_password] 密码修改成功 | account={account}")
        return {"success": True, "message": "密码修改成功"}
    else:
        raise HTTPException(status_code=400, detail="原密码错误")


@router.get("/users", response_model=list[UserInfo])
async def get_all_users(x_session_id: str = Header(..., alias="X-Session-ID")):
    """获取所有用户列表（需要管理员权限）"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    user = user_service.get_user(account)
    if not user or not user['is_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user_service.get_all_users()


@router.get("/users-with-password", response_model=List[dict])
async def get_all_users_with_password(x_session_id: str = Header(..., alias="X-Session-ID")):
    """获取所有用户列表（含密码，仅管理员）"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    user = user_service.get_user(account)
    if not user or not user['is_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user_service.get_all_users_with_password()


@router.post("/users")
async def add_user(
    request: AddUserRequest,
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    """新增用户（仅管理员）"""
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    user = user_service.get_user(account)
    if not user or not user['is_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4位")

    result = user_service.add_user(request.account, request.password, request.position, request.permissions)
    if not result:
        raise HTTPException(status_code=400, detail="账号已存在")

    logger.info(f"[add_user] 新增用户 | admin={account}, new_account={request.account}")
    return {"success": True, "message": "用户添加成功"}


@router.put("/users/{target_account}/password")
async def admin_change_password(
    target_account: str,
    new_password: str,
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    """管理员修改任意用户密码"""
    admin_account = session_manager.verify_session(x_session_id)
    if not admin_account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    admin = user_service.get_user(admin_account)
    if not admin or not admin['is_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    if len(new_password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4位")

    result = user_service.admin_update_password(target_account, new_password)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")

    logger.info(f"[admin_change_password] 管理员修改密码 | admin={admin_account}, target={target_account}")
    return {"success": True, "message": f"已修改 {target_account} 的密码"}


@router.delete("/users/{target_account}")
async def delete_user(
    target_account: str,
    x_session_id: str = Header(..., alias="X-Session-ID")
):
    """删除用户（仅管理员）"""
    admin_account = session_manager.verify_session(x_session_id)
    if not admin_account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")

    admin = user_service.get_user(admin_account)
    if not admin or not admin['is_admin']:
        raise HTTPException(status_code=403, detail="需要管理员权限")

    result = user_service.delete_user(target_account)
    if not result:
        raise HTTPException(status_code=404, detail="用户不存在")

    logger.info(f"[delete_user] 删除用户 | admin={admin_account}, deleted={target_account}")
    return {"success": True, "message": f"已删除用户 {target_account}"}


@router.get("/online-stat")
async def get_online_stat(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """获取在线统计"""
    return {
        "total_online": session_manager.get_all_online_count(),
        "sessions": len(session_manager.sessions)
    }
