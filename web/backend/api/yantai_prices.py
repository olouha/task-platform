"""
山东烟台钢筋价格抓取 API
精简版 - 只保留抓取功能
数据查询使用 /api/yantai-db 或 /yantai-rebar
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class MaterialPriceResponse(BaseModel):
    material_id: str
    material_name: str
    spec: str
    material_type: str
    brand: str
    price: float
    price_max: float = 0.0
    unit: str = "元/吨"
    price_change: str = ""
    remark: str = ""
    steel_code: str = ""
    region: str = "山东烟台"


class FetchResultResponse(BaseModel):
    success: bool
    source_name: str
    fetched_at: str
    prices: List[MaterialPriceResponse]
    error_message: str = ""
    is_mock: bool = False


def _get_configured_credentials():
    """获取配置的凭据（支持加密存储）"""
    try:
        from services.secure_storage import get_credential
        cred = get_credential('mysteel')
        if cred:
            return cred.get('username'), cred.get('password')
    except ImportError:
        pass

    # 回退：尝试从配置文件读取（不推荐）
    try:
        config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('username'), config.get('password')
    except:
        pass

    return None, None


# ============================================================
# 抓取状态 API
# ============================================================

@router.get("/status")
async def get_fetch_status():
    """
    获取抓取状态

    返回最近一次抓取的时间、结果和数据条数
    """
    logger.info("[get_fetch_status] 获取抓取状态")
    last_fetch_file = Path(__file__).parent.parent / 'services' / 'logs' / 'yantai_last_fetch.json'

    if last_fetch_file.exists():
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                "last_fetch": data.get('last_fetch'),
                "success": data.get('success'),
                "prices_count": data.get('prices_count'),
                "region": data.get('region')
            }

    return {
        "last_fetch": None,
        "success": None,
        "prices_count": 0,
        "region": "山东烟台"
    }


@router.get("/check")
async def check_fetch_status():
    """
    检查今日是否已抓取

    返回布尔值表示今日是否已完成抓取
    """
    logger.info("[check_fetch_status] 检查今日抓取状态")
    from datetime import datetime

    last_fetch_file = Path(__file__).parent.parent / 'services' / 'logs' / 'yantai_last_fetch.json'
    today = datetime.now().date().isoformat()

    if last_fetch_file.exists():
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_fetch_date = data.get('last_fetch', '')[:10]

            if last_fetch_date == today:
                return {
                    "fetched_today": True,
                    "last_fetch": data.get('last_fetch'),
                    "success": data.get('success'),
                    "prices_count": data.get('prices_count', 0),
                    "message": f"今日({today})已抓取，共{data.get('prices_count', 0)}条记录"
                }

    return {
        "fetched_today": False,
        "last_fetch": None,
        "message": "今日尚未抓取，可以执行抓取"
    }


# ============================================================
# 凭据管理 API
# ============================================================

@router.post("/update-credentials")
async def update_credentials(username: str, password: str):
    """
    更新登录凭据（使用加密存储）

    - username: 我的钢铁网用户名
    - password: 我的钢铁网密码

    更新后会自动删除旧Cookie，下次抓取会重新登录
    """
    logger.info(f"[update_credentials] 更新凭据 | username={username[:3]}***")
    try:
        # 优先使用加密存储
        try:
            from services.secure_storage import save_credential
            save_credential('mysteel', username, password)
            logger.info("[update_credentials] 凭据已加密保存")
        except ImportError:
            # 回退：保存到配置文件
            config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
            config_file.parent.mkdir(exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({'username': username, 'password': password}, f, ensure_ascii=False, indent=2)
            logger.warning("[update_credentials] 凭据保存到未加密文件")

        # 删除旧Cookie，强制重新登录
        cookie_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_cookies.json'
        if cookie_file.exists():
            cookie_file.unlink()
            logger.info("[update_credentials] 已删除旧Cookie")

        return {
            "success": True,
            "message": "凭据已更新，请重新抓取以验证"
        }

    except Exception as e:
        logger.error(f"[update_credentials] 更新失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def get_credentials_status():
    """
    获取当前凭据状态（不返回密码）

    返回是否已配置凭据
    """
    logger.info("[get_credentials_status] 获取凭据状态")
    username, _ = _get_configured_credentials()

    return {
        "has_username": bool(username),
        "username": username[:3] + '***' if username else None,
        "has_password": True,  # 无法判断是否有密码，只能通过username推断
        "storage_type": "encrypted"
    }


# ============================================================
# 抓取 API
# ============================================================

@router.post("/fetch", response_model=FetchResultResponse)
async def fetch_prices(force: bool = False):
    """
    抓取山东烟台钢筋价格

    - force: 是否强制抓取（忽略每天一次的限制）

    返回抓取结果，包含价格列表
    """
    logger.info(f"[fetch_prices] 开始抓取 | force={force}")
    try:
        from services.fetch_yantai import run_fetch

        result = await run_fetch()

        if result['success']:
            is_mock = "模拟" in result.get('source_name', '')
            logger.info(f"[fetch_prices] 抓取成功 | count={len(result.get('prices', []))}")

            return FetchResultResponse(
                success=True,
                source_name=result.get('source_name', '我的钢铁网-山东烟台'),
                fetched_at=result.get('fetched_at', ''),
                prices=[
                    MaterialPriceResponse(
                        material_id=f"yt_{p['material_name']}_{p['spec']}_{p['brand']}",
                        material_name=p['material_name'],
                        spec=p['spec'],
                        material_type=p['material_type'],
                        brand=p['brand'],
                        price=p['price'],
                        price_max=0,
                        unit='元/吨',
                        price_change='',
                        remark='',
                        steel_code='',
                        region='山东烟台'
                    )
                    for p in result.get('prices', [])
                ],
                is_mock=is_mock
            )
        else:
            logger.error(f"[fetch_prices] 抓取失败 | error={result.get('error')}")
            return FetchResultResponse(
                success=False,
                source_name='我的钢铁网-山东烟台',
                fetched_at="",
                prices=[],
                error_message=result.get('error', '未知错误')
            )

    except Exception as e:
        logger.error(f"[fetch_prices] 抓取异常 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-historical")
async def fetch_historical_prices_endpoint(days: int = 7):
    """
    抓取历史价格数据（最近N天）

    - days: 抓取最近几天的数据，默认7天

    返回每天的抓取结果和数据统计
    """
    logger.info(f"[fetch_historical_prices] 抓取历史数据 | days={days}")
    try:
        from services.fetch_yantai_api import fetch_historical_prices

        result = await fetch_historical_prices(days=days)

        logger.info(f"[fetch_historical_prices] 完成 | dates={result.get('dates_fetched', 0)}, prices={result.get('total_prices', 0)}")

        return {
            "success": result['success'],
            "dates_fetched": result.get('dates_fetched', 0),
            "total_prices": result.get('total_prices', 0),
            "data": result.get('data', {}),
            "error": result.get('error', '')
        }

    except Exception as e:
        logger.error(f"[fetch_historical_prices] 抓取失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
