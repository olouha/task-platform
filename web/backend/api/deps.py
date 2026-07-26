"""通用 FastAPI 依赖：获取当前登录账号，用于上传/导入留痕"""

import logging
from fastapi import Header, HTTPException

from services.auth_service import session_manager, user_service

logger = logging.getLogger(__name__)


def get_current_account(x_session_id: str = Header(..., alias="X-Session-ID")) -> str:
    """解析 X-Session-ID 返回当前登录账号

    用于上传/导入接口留痕（uploaded_by）。会话无效或未登录时抛 401。

    Returns:
        当前登录账号字符串

    Raises:
        HTTPException: 401 会话无效或已过期
    """
    logger.debug(f"[get_current_account] 解析会话 | session_id={x_session_id[:8] if x_session_id else 'N/A'}...")
    account = session_manager.verify_session(x_session_id)
    if not account:
        logger.warning("[get_current_account] 会话无效或已过期")
        raise HTTPException(status_code=401, detail="会话无效或已过期")
    return account


# 全权限职位（可执行删除/修改等敏感写操作）
FULL_ACCESS_POSITIONS = ['管理层', '开发人员', '办公室团队']


def get_current_user_can_delete(x_session_id: str = Header(..., alias="X-Session-ID")) -> str:
    """校验管理员权限（is_admin 或全权限职位），用于删除/修改等敏感写操作。

    登录态校验 + 权限等级校验。与前端 canDelete 逻辑一致，
    提取为公共依赖供所有模块的 DELETE/PUT 端点复用，避免前端隐藏可被绕过。
    """
    account = session_manager.verify_session(x_session_id)
    if not account:
        raise HTTPException(status_code=401, detail="会话无效或已过期")
    user = user_service.get_user(account)
    if not user:
        raise HTTPException(status_code=403, detail="用户不存在")
    position = (user.get('position') or '').strip()
    if user.get('is_admin') or position in FULL_ACCESS_POSITIONS:
        return account
    raise HTTPException(status_code=403, detail="需要管理员或管理/开发/办公室职位权限")
