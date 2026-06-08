"""
批量价格接口 API
用于获取多个材料的基准价、施工期均价、数据完整率
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import logging
from pathlib import Path

from api.adjustment_prices import load_yantai_prices, get_material_prices, STEEL_BRANDS_PRIORITY

router = APIRouter(prefix="/adjustments/prices", tags=["调差价格批量获取"])
logger = logging.getLogger(__name__)


# ============================================================
# 请求/响应模型
# ============================================================

class BatchPriceRequest(BaseModel):
    """批量价格查询请求"""
    materials: List[str] = Field(..., min_length=1, description="材料名称列表")
    start_date: str = Field(..., description="施工期开始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="施工期结束日期 YYYY-MM-DD")
    base_date: str = Field(default="", description="基准日期 YYYY-MM-DD（可选）")
    brands: Optional[List[str]] = Field(default=None, description="品牌偏好列表")


class MaterialPriceData(BaseModel):
    """单个材料的价格数据"""
    material: str
    base_price: float = 0
    period_avg_price: float = 0
    data_points: int = 0
    data_completeness: float = 0  # 数据完整率（百分比）
    change_rate: float = 0  # 涨跌幅度百分比
    price_list: List[Dict] = Field(default_factory=list)  # 价格明细
    warnings: List[str] = Field(default_factory=list)  # 警告信息


class BatchPriceResponse(BaseModel):
    """批量价格响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================
# 数据完整率计算
# ============================================================

def calculate_data_completeness(
    material_name: str,
    start_date: str,
    end_date: str,
    all_prices: List[Dict]
) -> Dict[str, Any]:
    """
    计算指定材料在时间范围内的数据完整率

    Args:
        material_name: 材料名称
        start_date: 开始日期
        end_date: 结束日期
        all_prices: 所有价格数据

    Returns:
        {
            "total_days": 总天数,
            "valid_days": 有效数据天数,
            "completeness": 完整率百分比,
            "missing_dates": 缺失日期列表
        }
    """
    # 计算总天数
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days + 1
    except Exception:
        return {
            "total_days": 0,
            "valid_days": 0,
            "completeness": 0,
            "missing_dates": []
        }

    # 收集有效日期
    valid_dates = set()
    for p in all_prices:
        if start_date <= p.get('date', '') <= end_date:
            # 模糊匹配材料名称
            pname = p.get('material_name', '')
            if (material_name in pname or pname in material_name or
                '钢筋' in material_name and '钢筋' in pname):
                if p.get('price', 0) > 0:
                    valid_dates.add(p['date'])

    valid_days = len(valid_dates)

    # 计算完整率
    completeness = (valid_days / total_days * 100) if total_days > 0 else 0

    # 找出缺失日期
    all_dates = set()
    current = start
    while current <= end:
        all_dates.add(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    missing = sorted(list(all_dates - valid_dates))

    return {
        "total_days": total_days,
        "valid_days": valid_days,
        "completeness": round(completeness, 2),
        "missing_dates": missing[:10]  # 最多返回10个缺失日期
    }


def get_material_price_data(
    material_name: str,
    start_date: str,
    end_date: str,
    base_date: str,
    all_prices: List[Dict],
    brands: Optional[List[str]] = None
) -> MaterialPriceData:
    """
    获取单个材料的完整价格数据

    Args:
        material_name: 材料名称
        start_date: 施工期开始日期
        end_date: 施工期结束日期
        base_date: 基准日期
        all_prices: 所有价格数据
        brands: 品牌偏好

    Returns:
        MaterialPriceData
    """
    result = MaterialPriceData(material=material_name)

    # 获取基准价
    if base_date:
        base_result = get_material_prices(material_name, base_date, base_date, all_prices)
        result.base_price = base_result.get('avg_price', 0)
    else:
        # 无基准日期，使用默认值（钢筋默认4500）
        if '钢筋' in material_name or '螺纹' in material_name:
            result.base_price = 4500

    # 获取施工期价格
    period_result = get_material_prices(
        material_name, start_date, end_date, all_prices,
        brands=brands if brands else STEEL_BRANDS_PRIORITY
    )
    result.period_avg_price = period_result.get('avg_price', 0)
    result.data_points = period_result.get('count', 0)

    # 计算涨跌幅度
    if result.base_price > 0:
        result.change_rate = round(
            (result.period_avg_price - result.base_price) / result.base_price * 100, 2
        )

    # 计算数据完整率
    completeness_data = calculate_data_completeness(
        material_name, start_date, end_date, all_prices
    )
    result.data_completeness = completeness_data['completeness']

    # 价格明细（最多50条）
    result.price_list = [
        {
            'date': p['date'],
            'price': p['price'],
            'brand': p.get('brand', ''),
            'spec': p.get('spec', '')
        }
        for p in period_result.get('prices', [])[:50]
    ]

    # 添加警告
    if result.data_completeness < 50:
        result.warnings.append(f"数据完整率过低：{result.data_completeness}%")
    elif result.data_completeness < 80:
        result.warnings.append(f"数据完整率偏低：{result.data_completeness}%")

    if result.base_price == 0:
        result.warnings.append("未找到基准价，使用默认值")

    return result


# ============================================================
# API 端点
# ============================================================

@router.post("/batch-get", response_model=BatchPriceResponse)
async def batch_get_prices(request: BatchPriceRequest):
    """
    批量获取多个材料的价格数据

    请求参数:
    - materials: 材料名称列表
    - start_date: 施工期开始日期
    - end_date: 施工期结束日期
    - base_date: 基准日期（可选）
    - brands: 品牌偏好（可选）

    返回:
    - 各材料的基准价、施工期均价、数据完整率
    """
    logger.info(
        f"[batch_get_prices] 批量获取价格 | materials={len(request.materials)}, "
        f"period={request.start_date} to {request.end_date}"
    )

    try:
        # 加载价格数据
        all_prices = load_yantai_prices()

        if not all_prices:
            logger.warning("[batch_get_prices] 无价格数据")
            return BatchPriceResponse(
                success=False,
                error="价格数据库为空，请先抓取价格数据"
            )

        # 解析品牌偏好
        brand_list = request.brands if request.brands else STEEL_BRANDS_PRIORITY

        # 获取每个材料的价格数据
        results = []
        for material in request.materials:
            data = get_material_price_data(
                material_name=material,
                start_date=request.start_date,
                end_date=request.end_date,
                base_date=request.base_date,
                all_prices=all_prices,
                brands=brand_list
            )
            results.append(data)

        # 汇总统计
        total_materials = len(results)
        valid_base_price_count = sum(1 for r in results if r.base_price > 0)
        warnings_count = sum(1 for r in results if r.warnings)

        logger.info(
            f"[batch_get_prices] 获取完成 | materials={total_materials}, "
            f"valid_base={valid_base_price_count}, warnings={warnings_count}"
        )

        return BatchPriceResponse(
            success=True,
            data={
                "materials": [r.model_dump() for r in results],
                "summary": {
                    "total_materials": total_materials,
                    "valid_base_prices": valid_base_price_count,
                    "average_completeness": sum(r.data_completeness for r in results) / total_materials,
                    "materials_with_warnings": warnings_count
                },
                "query": {
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "base_date": request.base_date
                }
            }
        )

    except Exception as e:
        logger.error(f"[batch_get_prices] 获取失败 | error={e}", exc_info=True)
        return BatchPriceResponse(
            success=False,
            error=str(e)
        )


@router.get("/batch", summary="批量获取材料价格（GET方式）")
async def batch_get_prices_get(
    materials: str = Query(..., description="材料列表，逗号分隔"),
    start_date: str = Query(..., description="施工期开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="施工期结束日期 YYYY-MM-DD"),
    base_date: str = Query("", description="基准日期 YYYY-MM-DD"),
    brands: Optional[str] = Query(None, description="品牌偏好，逗号分隔")
):
    """
    批量获取多个材料的价格数据（GET方式）

    适用于简单查询场景
    """
    material_list = [m.strip() for m in materials.split(',')]

    # 解析品牌偏好
    brand_list = None
    if brands:
        brand_list = [b.strip() for b in brands.split(',')]

    # 构建请求
    request = BatchPriceRequest(
        materials=material_list,
        start_date=start_date,
        end_date=end_date,
        base_date=base_date,
        brands=brand_list
    )

    # 调用批量接口
    return await batch_get_prices(request)


@router.get("/completeness", summary="检查数据完整率")
async def check_data_completeness(
    material: str = Query(..., description="材料名称"),
    start_date: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD")
):
    """
    检查指定材料在时间范围内的数据完整率

    用于判断价格数据是否足够用于调差计算
    """
    logger.info(f"[check_data_completeness] 检查完整率 | material={material}, period={start_date} to {end_date}")

    try:
        all_prices = load_yantai_prices()

        completeness = calculate_data_completeness(material, start_date, end_date, all_prices)

        # 判断是否满足调差要求
        if completeness['completeness'] >= 80:
            status = "充足"
        elif completeness['completeness'] >= 50:
            status = "偏低但可用"
        else:
            status = "不足"

        logger.info(f"[check_data_completeness] 完整率={completeness['completeness']}%, status={status}")

        return {
            "success": True,
            "material": material,
            "start_date": start_date,
            "end_date": end_date,
            "completeness": completeness['completeness'],
            "valid_days": completeness['valid_days'],
            "total_days": completeness['total_days'],
            "missing_dates": completeness['missing_dates'],
            "status": status,
            "note": "数据完整率低于50%时建议更换数据源或调整时间范围"
        }

    except Exception as e:
        logger.error(f"[check_data_completeness] 检查失败 | error={e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }