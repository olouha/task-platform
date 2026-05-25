"""
调差规则配置 API
遵循《地产项目材料调差规则_AI可执行配置规范》v1.0
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from models.adjustment_rules import (
    AdjustmentRuleConfig, PRESET_RULES, MaterialConfig, RiskConfig,
    PhaseDefinition, SupplyPermission, DelayHandling
)
from services.supabase_service import SupabaseService

router = APIRouter(prefix="/adjustment-rules", tags=["调差规则管理"])


# ============================================================
# 依赖注入
# ============================================================

def get_supabase():
    """获取Supabase服务实例"""
    return SupabaseService()


# ============================================================
# Pydantic 请求/响应模型
# ============================================================

class CreateRuleRequest(BaseModel):
    """创建规则请求"""
    项目名称: str
    调差项目: List[Dict] = []
    价格规则: Dict = {}
    周期与阶段: Dict = {}
    计算公式: Dict = {}
    特殊规则: Optional[Dict] = None


class UpdateRuleRequest(BaseModel):
    """更新规则请求"""
    项目名称: Optional[str] = None
    调差项目: Optional[List[Dict]] = None
    价格规则: Optional[Dict] = None
    周期与阶段: Optional[Dict] = None
    计算公式: Optional[Dict] = None


class BidPriceItem(BaseModel):
    """投标价条目"""
    name: str
    spec: str = ""
    unit: str = "t"
    bid_price: float


class SaveBidPricesRequest(BaseModel):
    """保存投标价请求"""
    rule_id: str
    bid_prices: List[BidPriceItem]
    特殊规则: Optional[Dict] = None


class ApplyPresetRequest(BaseModel):
    """应用预设规则请求"""
    项目名称: str
    自定义名称: Optional[str] = None  # 自定义名称，为空则使用预设名称


# ============================================================
# 辅助函数
# ============================================================

def parse_risk_config(raw: Dict[str, Any]) -> Dict[str, RiskConfig]:
    """解析风险幅度配置"""
    result = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict):
            result[name] = RiskConfig(
                类型=cfg.get('类型', '百分比'),
                值=cfg.get('值', 0)
            )
    return result


def build_config_from_request(data: Dict) -> Dict[str, Any]:
    """从请求数据构建配置"""
    config = {
        '项目名称': data.get('项目名称'),
        '调差项目': [
            MaterialConfig(**item) if isinstance(item, dict) else item
            for item in data.get('调差项目', [])
        ],
        '价格规则': data.get('价格规则', {}),
        '周期与阶段': data.get('周期与阶段', {}),
        '计算公式': data.get('计算公式', {}),
        '使用规则版本': 'v1.0',
    }

    # 解析风险幅度
    if '风险幅度' in data.get('价格规则', {}):
        raw_risks = data['价格规则']['风险幅度']
        config['风险幅度'] = parse_risk_config(raw_risks)
    else:
        config['风险幅度'] = {}

    # 解析阶段划分
    if '阶段划分' in data.get('周期与阶段', {}):
        phases = data['周期与阶段']['阶段划分']
        config['阶段划分'] = [
            PhaseDefinition(**p) if isinstance(p, dict) else p
            for p in phases
        ]

    return config


# ============================================================
# API 端点
# ============================================================

@router.get("/presets", summary="获取预设规则列表")
async def get_preset_rules():
    """获取4套预设规则"""
    return {
        "presets": list(PRESET_RULES.keys()),
        "details": PRESET_RULES
    }


@router.get("/presets/{preset_name}", summary="获取单个预设规则")
async def get_preset_rule(preset_name: str):
    """获取指定预设规则的完整配置"""
    if preset_name not in PRESET_RULES:
        raise HTTPException(status_code=404, detail=f"预设规则 '{preset_name}' 不存在")

    return PRESET_RULES[preset_name]


@router.get("/", summary="获取所有规则配置")
async def list_rules(supabase: SupabaseService = Depends(get_supabase)):
    """获取所有调差规则配置"""
    try:
        result = supabase.get_adjustment_rules()
        if result is None:
            return {"rules": []}
        return {"rules": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则失败: {str(e)}")


@router.get("/{rule_id}", summary="获取单个规则配置")
async def get_rule(rule_id: str, supabase: SupabaseService = Depends(get_supabase)):
    """获取指定规则的完整配置"""
    try:
        rule = supabase.get_adjustment_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        return rule
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则失败: {str(e)}")


@router.post("/", summary="创建规则配置", response_model=Dict)
async def create_rule(
    request: CreateRuleRequest,
    supabase: SupabaseService = Depends(get_supabase)
):
    """创建新的调差规则配置"""
    try:
        rule_data = {
            'id': str(uuid.uuid4()),
            'name': request.项目名称,
            'config': {
                '项目名称': request.项目名称,
                '调差项目': request.调差项目,
                '价格规则': request.价格规则,
                '周期与阶段': request.周期与阶段,
                '计算公式': request.计算公式,
                '特殊规则': request.特殊规则 or {},
                '使用规则版本': 'v1.0',
            },
            'is_preset': False,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

        success = supabase.create_adjustment_rule(rule_data)
        if not success:
            raise HTTPException(status_code=500, detail="创建规则失败")

        return {"id": rule_data['id'], "name": rule_data['name'], "success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建规则失败: {str(e)}")


@router.put("/{rule_id}", summary="更新规则配置")
async def update_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    supabase: SupabaseService = Depends(get_supabase)
):
    """更新指定的调差规则配置"""
    try:
        update_data = {'updated_at': datetime.now().isoformat()}

        if request.项目名称 is not None:
            update_data['name'] = request.项目名称
            update_data['config'] = {'项目名称': request.项目名称}

        if request.调差项目 is not None:
            update_data['config'] = update_data.get('config', {})
            update_data['config']['调差项目'] = request.调差项目

        if request.价格规则 is not None:
            update_data['config'] = update_data.get('config', {})
            update_data['config']['价格规则'] = request.价格规则

        if request.周期与阶段 is not None:
            update_data['config'] = update_data.get('config', {})
            update_data['config']['周期与阶段'] = request.周期与阶段

        if request.计算公式 is not None:
            update_data['config'] = update_data.get('config', {})
            update_data['config']['计算公式'] = request.计算公式

        if request.特殊规则 is not None:
            update_data['config'] = update_data.get('config', {})
            update_data['config']['特殊规则'] = request.特殊规则

        success = supabase.update_adjustment_rule(rule_id, update_data)
        if not success:
            raise HTTPException(status_code=500, detail="更新规则失败")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新规则失败: {str(e)}")


@router.delete("/{rule_id}", summary="删除规则配置")
async def delete_rule(
    rule_id: str,
    supabase: SupabaseService = Depends(get_supabase)
):
    """删除指定的调差规则配置"""
    try:
        success = supabase.delete_adjustment_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除规则失败: {str(e)}")


@router.post("/apply-preset", summary="应用预设规则")
async def apply_preset_rule(
    preset_name: str,
    request: ApplyPresetRequest,
    supabase: SupabaseService = Depends(get_supabase)
):
    """将预设规则应用到新项目"""
    if preset_name not in PRESET_RULES:
        raise HTTPException(status_code=404, detail=f"预设规则 '{preset_name}' 不存在")

    preset = PRESET_RULES[preset_name]
    project_name = request.自定义名称 or request.项目名称

    try:
        rule_data = {
            'id': str(uuid.uuid4()),
            'name': project_name,
            'config': {
                **preset,
                '项目名称': project_name,
            },
            'is_preset': False,
            'derived_from': preset_name,  # 记录来源
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }

        success = supabase.create_adjustment_rule(rule_data)
        if not success:
            raise HTTPException(status_code=500, detail="应用预设规则失败")

        return {
            "id": rule_data['id'],
            "name": project_name,
            "derived_from": preset_name,
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用预设规则失败: {str(e)}")


@router.get("/validate/config", summary="校验规则配置")
async def validate_rule_config(config: Dict):
    """校验规则配置的完整性"""
    errors = []

    # 检查必填项
    if '调差项目' not in config or not config['调差项目']:
        errors.append("缺少必填项: 调差项目")

    if '价格规则' not in config:
        errors.append("缺少必填项: 价格规则")
    else:
        price_rule = config['价格规则']
        if '基准价来源' not in price_rule:
            errors.append("缺少必填项: 基准价来源")
        if '风险幅度' not in price_rule:
            errors.append("缺少必填项: 风险幅度")

    if '计算公式' not in config:
        errors.append("缺少必填项: 计算公式")
    else:
        formula = config['计算公式']
        if '调差公式模板' not in formula:
            errors.append("缺少必填项: 调差公式模板")
        if '税率' not in formula:
            errors.append("缺少必填项: 税率")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


@router.post("/bid-prices", summary="保存投标价")
async def save_bid_prices(
    request: SaveBidPricesRequest,
    supabase: SupabaseService = Depends(get_supabase)
):
    """保存规则的投标价数据"""
    try:
        # 获取当前规则
        rule = supabase.get_adjustment_rule(request.rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {request.rule_id} 不存在")

        # 准备投标价数据
        bid_prices_data = [item.model_dump() for item in request.bid_prices]

        # 更新规则配置
        update_data = {
            'updated_at': datetime.now().isoformat(),
            'config': rule.get('config', {})
        }
        update_data['config']['投标价'] = bid_prices_data

        success = supabase.update_adjustment_rule(request.rule_id, update_data)
        if not success:
            raise HTTPException(status_code=500, detail="保存投标价失败")

        return {"success": True, "count": len(bid_prices_data)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存投标价失败: {str(e)}")


@router.get("/{rule_id}/bid-prices", summary="获取投标价")
async def get_bid_prices(
    rule_id: str,
    supabase: SupabaseService = Depends(get_supabase)
):
    """获取规则的投标价数据"""
    try:
        rule = supabase.get_adjustment_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        config = rule.get('config', {})
        bid_prices = config.get('投标价', [])

        return {"bid_prices": bid_prices}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取投标价失败: {str(e)}")
