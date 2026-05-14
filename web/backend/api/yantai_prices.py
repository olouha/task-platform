"""
山东烟台钢筋价格抓取 API v7.0 - 支持品牌维度
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class MaterialPriceResponse(BaseModel):
    material_id: str
    material_name: str  # 品名：高线、螺纹钢、盘螺、圆钢
    spec: str           # 规格：如 Φ6、Φ8、Φ10
    material_type: str  # 材质：如 HPB300、HRB400E、HRB500E
    brand: str          # 钢厂/产地
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


class PriceRecord(BaseModel):
    date: str
    fetched_at: str
    source: str
    prices: List[MaterialPriceResponse]


class PriceSummary(BaseModel):
    """价格汇总"""
    total_count: int
    brands: List[str]
    material_types: dict  # {品名: 数量}
    brands_detail: dict   # {品名: [品牌列表]}


@router.get("/status")
async def get_fetch_status():
    """获取抓取状态"""
    from pathlib import Path
    import os

    last_fetch_file = Path(os.path.join(os.path.dirname(__file__), '..', 'services', 'logs', 'yantai_last_fetch.json'))
    if last_fetch_file.exists():
        import json
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


@router.post("/fetch", response_model=FetchResultResponse)
async def fetch_prices(force: bool = False):
    """
    抓取山东烟台钢筋价格（品牌维度）

    - force: 是否强制抓取（忽略每天一次的限制）
    """
    try:
        from services.fetch_yantai import run_fetch

        result = await run_fetch()

        if result['success']:
            # 判断是否是模拟数据
            is_mock = "模拟" in result.get('source_name', '')

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
            return FetchResultResponse(
                success=False,
                source_name='我的钢铁网-山东烟台',
                fetched_at="",
                prices=[],
                error_message=result.get('error', '未知错误')
            )

    except Exception as e:
        logger.error(f"抓取失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-credentials")
async def update_credentials(username: str, password: str):
    """
    更新登录凭据

    - username: 我的钢铁网用户名
    - password: 我的钢铁网密码
    """
    try:
        import json
        from pathlib import Path

        config_file = Path(__file__).parent.parent / 'services' / 'data' / 'mysteel_config.json'
        config_file.parent.mkdir(exist_ok=True)

        config = {
            'username': username,
            'password': password
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 删除旧Cookie，强制重新登录
        cookie_file = config_file.parent / 'mysteel_cookies.json'
        if cookie_file.exists():
            cookie_file.unlink()

        return {
            "success": True,
            "message": "凭据已更新，请重新抓取以验证"
        }

    except Exception as e:
        logger.error(f"更新凭据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def get_credentials_status():
    """
    获取当前凭据状态（不返回密码）
    """
    from services.yantai_rebar_scraper import YantaiRebarScraper
    import os

    scraper = YantaiRebarScraper()
    config_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', 'mysteel_config.json')

    if os.path.exists(config_file):
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return {
                "has_username": bool(config.get('username')),
                "username": config.get('username', '')[:3] + '***' if config.get('username') else None,
                "has_password": bool(config.get('password'))
            }

    return {
        "has_username": False,
        "username": None,
        "has_password": False
    }


@router.get("/summary", response_model=PriceSummary)
async def get_price_summary():
    """获取价格汇总（按品名、品牌统计）"""
    try:
        from services.yantai_rebar_scraper import read_from_excel
        import os

        # 修正Excel路径：从api目录相对于services目录
        excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

        all_data = read_from_excel(excel_file)
        if not all_data:
            return PriceSummary(
                total_count=0,
                brands=[],
                material_types={},
                brands_detail={}
            )

        # 获取最新一天的数据
        latest_sheet = sorted(all_data.keys())[-1] if all_data else None
        if not latest_sheet:
            return PriceSummary(
                total_count=0,
                brands=[],
                material_types={},
                brands_detail={}
            )

        prices = all_data[latest_sheet].get('prices', [])

        # 统计
        brands = set()
        material_types = {}
        brands_detail = {}

        for p in prices:
            brand = p.get('brand', '')
            material_name = p.get('material_name', '')

            if brand:
                brands.add(brand)

            if material_name:
                material_types[material_name] = material_types.get(material_name, 0) + 1

                if material_name not in brands_detail:
                    brands_detail[material_name] = []
                if brand and brand not in brands_detail[material_name]:
                    brands_detail[material_name].append(brand)

        return PriceSummary(
            total_count=len(prices),
            brands=sorted(list(brands)),
            material_types=material_types,
            brands_detail=brands_detail
        )

    except Exception as e:
        logger.error(f"获取汇总失败: {e}")
        return PriceSummary(
            total_count=0,
            brands=[],
            material_types={},
            brands_detail={}
        )


@router.get("/history", response_model=List[PriceRecord])
async def get_price_history(days: int = 30):
    """
    获取价格历史

    - days: 返回最近几天的数据，默认30天
    """
    from pathlib import Path

    data_file = Path("data/yantai_rebar_prices.json")
    if not data_file.exists():
        return []

    import json
    with open(data_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    # 返回最近指定天数的记录
    return all_data[-days:]


@router.get("/latest")
async def get_latest_price(date: str = None):
    """获取最新价格 - 支持指定日期"""
    from services.yantai_rebar_scraper import read_from_excel

    # 修正Excel路径 - 使用相对路径
    excel_file = "services/data/山东烟台钢筋价格.xlsx"

    all_data = read_from_excel(excel_file)
    if not all_data:
        return {"success": False, "prices": []}

    # 如果指定了日期，使用该日期；否则使用最新
    if date and date in all_data:
        target_sheet = date
    else:
        target_sheet = sorted(all_data.keys())[-1] if all_data else None

    if not target_sheet:
        return {"success": False, "prices": [], "sheet": None}

    prices = all_data[target_sheet].get('prices', [])
    if not prices:
        return {"success": False, "prices": [], "sheet": target_sheet}

    return {
        "success": True,
        "sheet": target_sheet,
        "prices": [
            {
                "date": target_sheet,  # 添加日期
                "time": p.get('time', ''),
                "material_id": f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
                "material_name": p.get('material_name', ''),
                "spec": p.get('spec', ''),
                "material_type": p.get('material_type', ''),
                "brand": p.get('brand', ''),
                "price": p.get('price', 0),
                "price_max": p.get('price_max', 0),
                "unit": p.get('unit', '元/吨'),
                "price_change": p.get('price_change', ''),
                "remark": p.get('remark', ''),
                "steel_code": p.get('steel_code', ''),
                "region": p.get('region', '山东烟台')
            }
            for p in prices
        ]
    }


@router.get("/check")
async def check_fetch_status():
    """检查今日是否已抓取"""
    from pathlib import Path
    import os

    last_fetch_file = Path(os.path.join(os.path.dirname(__file__), '..', 'services', 'logs', 'yantai_last_fetch.json'))
    today = datetime.now().date().isoformat()

    if last_fetch_file.exists():
        import json
        with open(last_fetch_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_fetch_date = data.get('last_fetch', '')[:10]

            if last_fetch_date == today:
                return {
                    "fetched_today": True,
                    "last_fetch": data.get('last_fetch'),
                    "success": data.get('success'),
                    "prices_count": data.get('prices_count'),
                    "message": f"今日({today})已抓取，共{data.get('prices_count', 0)}条记录"
                }

    return {
        "fetched_today": False,
        "last_fetch": None,
        "message": "今日尚未抓取，可以执行抓取"
    }


@router.get("/by-brand/{brand}")
async def get_prices_by_brand(brand: str):
    """按品牌筛选价格"""
    from services.yantai_rebar_scraper import read_from_excel
    import os

    excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

    all_data = read_from_excel(excel_file)
    if not all_data:
        return []

    latest_sheet = sorted(all_data.keys())[-1] if all_data else None
    if not latest_sheet:
        return []

    prices = all_data[latest_sheet].get('prices', [])

    # 筛选指定品牌
    filtered = [p for p in prices if brand in p.get('brand', '')]

    return [
        MaterialPriceResponse(
            material_id=f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
            material_name=p.get('material_name', ''),
            spec=p.get('spec', ''),
            material_type=p.get('material_type', ''),
            brand=p.get('brand', ''),
            price=p.get('price', 0),
            unit=p.get('unit', '元/吨'),
            region=p.get('region', '山东烟台')
        )
        for p in filtered
    ]


@router.get("/by-type/{material_type}")
async def get_prices_by_type(material_type: str):
    """按品名筛选价格（高线、螺纹钢、盘螺、圆钢）"""
    from services.yantai_rebar_scraper import read_from_excel
    import os

    excel_file = os.path.join(os.path.dirname(__file__), '..', 'services', 'data', '山东烟台钢筋价格.xlsx')

    all_data = read_from_excel(excel_file)
    if not all_data:
        return []

    latest_sheet = sorted(all_data.keys())[-1] if all_data else None
    if not latest_sheet:
        return []

    prices = all_data[latest_sheet].get('prices', [])

    # 筛选指定品名
    filtered = [p for p in prices if material_type in p.get('material_name', '')]

    return [
        MaterialPriceResponse(
            material_id=f"yt_{p.get('material_name', '')}_{p.get('spec', '')}_{p.get('brand', '')}",
            material_name=p.get('material_name', ''),
            spec=p.get('spec', ''),
            material_type=p.get('material_type', ''),
            brand=p.get('brand', ''),
            price=p.get('price', 0),
            unit=p.get('unit', '元/吨'),
            region=p.get('region', '山东烟台')
        )
        for p in filtered
    ]