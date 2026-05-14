"""
价格来源认证信息 API
支持配置网站登录账号、API密钥等认证信息
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()


class PriceSourceAuth(BaseModel):
    """价格来源认证信息"""
    source_id: str
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None  # 不返回实际密码
    auth_type: str = "form"
    auth_extra: Optional[dict] = None


class PriceSourceAuthUpdate(BaseModel):
    """更新认证信息"""
    source_id: str
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    auth_type: Optional[str] = None
    auth_extra: Optional[dict] = None


class PriceSourceAuthResponse(BaseModel):
    """认证信息响应（密码为空）"""
    source_id: str
    source_name: str
    has_credentials: bool
    auth_type: str
    last_verified: Optional[str] = None


# 模拟数据库
_auth_store: dict = {}
_last_verified: dict = {}


@router.get("/", response_model=List[PriceSourceAuthResponse])
async def list_source_auths():
    """获取所有价格来源的认证状态"""
    from models.schemas import PriceSource

    results = []
    for source_id in list(_auth_store.keys()):
        auth = _auth_store[source_id]
        results.append(PriceSourceAuthResponse(
            source_id=source_id,
            source_name=auth.get('source_name', ''),
            has_credentials=bool(auth.get('auth_username')),
            auth_type=auth.get('auth_type', 'form'),
            last_verified=_last_verified.get(source_id)
        ))

    return results


@router.get("/{source_id}", response_model=PriceSourceAuthResponse)
async def get_source_auth(source_id: str):
    """获取特定价格来源的认证信息"""
    auth = _auth_store.get(source_id)
    if not auth:
        raise HTTPException(status_code=404, detail="未找到认证信息")

    return PriceSourceAuthResponse(
        source_id=source_id,
        source_name=auth.get('source_name', ''),
        has_credentials=bool(auth.get('auth_username')),
        auth_type=auth.get('auth_type', 'form'),
        last_verified=_last_verified.get(source_id)
    )


@router.post("/", response_model=PriceSourceAuthResponse)
async def set_source_auth(auth_data: PriceSourceAuthUpdate):
    """设置价格来源的认证信息"""
    source_id = auth_data.source_id

    # 简单加密密码（生产环境应使用更安全的方式）
    encrypted_password = None
    if auth_data.auth_password:
        import base64
        encrypted_password = base64.b64encode(
            auth_data.auth_password.encode()
        ).decode('utf-8')

    auth_info = {
        'source_id': source_id,
        'auth_username': auth_data.auth_username,
        'auth_password_encrypted': encrypted_password,
        'auth_type': auth_data.auth_type,
        'auth_extra': auth_data.auth_extra,
        'updated_at': datetime.now().isoformat()
    }

    _auth_store[source_id] = auth_info

    return PriceSourceAuthResponse(
        source_id=source_id,
        source_name=auth_info.get('source_name', ''),
        has_credentials=bool(auth_data.auth_username),
        auth_type=auth_data.auth_type or 'form',
        last_verified=_last_verified.get(source_id)
    )


@router.delete("/{source_id}")
async def delete_source_auth(source_id: str):
    """删除价格来源的认证信息"""
    if source_id in _auth_store:
        del _auth_store[source_id]
        if source_id in _last_verified:
            del _last_verified[source_id]
        return {"success": True, "message": "认证信息已删除"}

    raise HTTPException(status_code=404, detail="未找到认证信息")


@router.post("/{source_id}/verify")
async def verify_credentials(source_id: str):
    """验证认证信息是否有效"""
    auth = _auth_store.get(source_id)
    if not auth or not auth.get('auth_username'):
        raise HTTPException(status_code=400, detail="未配置认证信息")

    # 这里可以调用实际的爬虫来验证登录
    # 暂时模拟验证
    from services.authenticated_scraper import ScraperFactory, SiteCredentials

    # 解密密码
    import base64
    encrypted_password = auth.get('auth_password_encrypted', '')
    if encrypted_password:
        try:
            password = base64.b64decode(encrypted_password).decode('utf-8')
        except:
            password = None
    else:
        password = None

    credentials = SiteCredentials(
        source_id=source_id,
        source_name=auth.get('source_name', ''),
        username=auth.get('auth_username', ''),
        password=password or ''
    )

    # 获取爬虫类型
    scraper_type_map = {
        'eeee1111-1111-1111-1111-111111111111': 'mysteel_rebar',
        'eeee2222-2222-2222-2222-222222222222': 'mysteel_concrete',
        'eeee3333-3333-3333-3333-333333333333': 'mysteel_concrete',
        'eeee4444-4444-4444-4444-444444444444': 'ccmn_aluminum',
        'eeee5555-5555-5555-5555-555555555555': 'ccmn_copper',
        'eeee6666-6666-6666-6666-666666666666': 'ccmn_zinc',
    }

    scraper_type = scraper_type_map.get(source_id, 'mysteel_rebar')
    scraper = ScraperFactory.get_scraper(scraper_type, credentials)

    if scraper:
        result = scraper.login()
        if result:
            _last_verified[source_id] = datetime.now().isoformat()
            return {
                "success": True,
                "message": "认证信息有效",
                "verified_at": _last_verified[source_id]
            }

    return {
        "success": False,
        "message": "认证信息验证失败，请检查用户名和密码"
    }


@router.post("/{source_id}/test-fetch")
async def test_fetch_with_auth(source_id: str):
    """使用认证信息测试抓取"""
    auth = _auth_store.get(source_id)
    if not auth or not auth.get('auth_username'):
        raise HTTPException(status_code=400, detail="未配置认证信息")

    # 解密密码
    import base64
    encrypted_password = auth.get('auth_password_encrypted', '')
    if encrypted_password:
        try:
            password = base64.b64decode(encrypted_password).decode('utf-8')
        except:
            password = ''
    else:
        password = ''

    from services.authenticated_scraper import ScraperFactory, SiteCredentials

    credentials = SiteCredentials(
        source_id=source_id,
        source_name=auth.get('source_name', ''),
        username=auth.get('auth_username', ''),
        password=password
    )

    # 获取爬虫类型
    scraper_type_map = {
        'eeee1111-1111-1111-1111-111111111111': 'mysteel_rebar',
        'eeee2222-2222-2222-2222-222222222222': 'mysteel_concrete',
        'eeee3333-3333-3333-3333-333333333333': 'mysteel_concrete',
        'eeee4444-4444-4444-4444-444444444444': 'ccmn_aluminum',
        'eeee5555-5555-5555-5555-555555555555': 'ccmn_copper',
        'eeee6666-6666-6666-6666-666666666666': 'ccmn_zinc',
    }

    scraper_type = scraper_type_map.get(source_id, 'mysteel_rebar')
    scraper = ScraperFactory.get_scraper(scraper_type, credentials)

    if scraper:
        result = scraper.fetch(force=True)
        return {
            "success": result.success,
            "price": result.price,
            "material_name": result.material_name,
            "unit": result.unit,
            "fetched_at": result.fetched_at,
            "error_message": result.error_message
        }

    return {
        "success": False,
        "error_message": "未找到对应的爬虫"
    }


@router.get("/{source_id}/fetch-status")
async def get_fetch_status(source_id: str):
    """获取抓取状态"""
    auth = _auth_store.get(source_id)

    return {
        "source_id": source_id,
        "last_verified": _last_verified.get(source_id),
        "has_credentials": bool(auth.get('auth_username')) if auth else False
    }