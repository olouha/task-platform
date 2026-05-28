"""
调差计算 API
包含旧版和新版调差计算端点
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import logging

from services.adjustment_calculator import AdjustmentCalculator
from services.adjustment_engine import AdjustmentEngine, CalculationInput, PriceData, QuantityData
from services.supabase_service import SupabaseService
from models.schemas import AdjustmentRecord, AdjustmentResult
from models.adjustment_rules import AdjustmentRuleConfig, PRESET_RULES

router = APIRouter(prefix="/adjustments", tags=["调差计算"])
logger = logging.getLogger(__name__)
calculator = AdjustmentCalculator()

# 模拟数据存储
_adjustment_records_db = {}


# ============================================================
# Pydantic 请求/响应模型
# ============================================================

class CalculateRequest(BaseModel):
    """调差计算请求"""
    rule_id: Optional[str] = None
    config: Optional[Dict] = None  # 直接传入配置
    base_prices: Dict[str, float] = {}  # 材料基准价
    period_prices: Dict[str, List[Dict]] = {}  # 材料施工期价格
    quantities: List[Dict] = []  # 工程量数据


class CalculationResponse(BaseModel):
    """调差计算响应"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None


# ============================================================
# 依赖注入
# ============================================================

def get_supabase():
    return SupabaseService()


# ============================================================
# 新版调差计算 API（遵循AI可执行配置规范）
# ============================================================

@router.post("/calculate", response_model=CalculationResponse)
async def calculate_adjustment_v2(
    request: CalculateRequest,
    supabase: SupabaseService = Depends(get_supabase)
):
    """
    按新规范执行调差计算

    请求参数:
    - rule_id: 规则ID（从数据库加载）
    - config: 直接传入配置JSON
    - base_prices: 材料基准价字典
    - period_prices: 施工期价格字典
    - quantities: 工程量列表
    """
    logger.info(f"[calculate_adjustment_v2] 计算调差 | rule_id={request.rule_id}, materials={len(request.quantities)}")
    try:
        # Step 1: 获取或解析配置
        if request.rule_id:
            rule = supabase.get_adjustment_rule(request.rule_id)
            if not rule:
                logger.warning(f"[calculate_adjustment_v2] 规则不存在 | rule_id={request.rule_id}")
                raise HTTPException(status_code=404, detail=f"规则 {request.rule_id} 不存在")
            config_dict = rule.get('config', {})
        elif request.config:
            config_dict = request.config
        else:
            logger.warning("[calculate_adjustment_v2] 缺少参数")
            return CalculationResponse(
                success=False,
                error="必须提供 rule_id 或 config"
            )

        config = AdjustmentRuleConfig(**config_dict)

        input_data = CalculationInput(
            base_prices=request.base_prices,
            period_prices={
                k: [PriceData(**p) for p in v]
                for k, v in request.period_prices.items()
            },
            quantities=[
                QuantityData(**q) for q in request.quantities
            ]
        )

        engine = AdjustmentEngine(config)
        result = engine.calculate(input_data)

        logger.info(f"[calculate_adjustment_v2] 计算成功 | total={result.total_adjustment}")
        return CalculationResponse(
            success=True,
            data=result.model_dump()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[calculate_adjustment_v2] 计算失败 | {e}", exc_info=True)
        return CalculationResponse(
            success=False,
            error=str(e)
        )


@router.post("/calculate-simple")
async def calculate_adjustment_simple(
    base_price: float,
    avg_price: float,
    quantity: float,
    risk_percent: float = 0,
    risk_fixed: float = 0,
    tax_rate: float = 9
):
    """
    简单调差计算

    直接输入参数计算单个材料的调差金额
    适用于快速计算，无需完整配置
    """
    logger.info(f"[calculate_adjustment_simple] 计算 | base={base_price}, avg={avg_price}, qty={quantity}")
    result = AdjustmentEngine.calculate_simple(
        base_price=base_price,
        avg_price=avg_price,
        quantity=quantity,
        risk_percent=risk_percent,
        risk_fixed=risk_fixed,
        tax_rate=tax_rate
    )

    logger.info(f"[calculate_adjustment_simple] 完成 | result={result}")
    return {
        "success": True,
        "data": result,
        "formula": f"调整金额 = {quantity} × ({avg_price} - {base_price} ± 风险幅度) × (1 + {tax_rate}%)"
    }


@router.get("/presets")
async def get_adjustment_presets():
    """获取预设规则列表"""
    logger.info("[get_adjustment_presets] 获取预设规则")
    presets = [
        {"name": name, "description": _get_preset_description(name)}
        for name in PRESET_RULES.keys()
    ]
    logger.info(f"[get_adjustment_presets] 返回 {len(presets)} 个预设")
    return {"presets": presets}


def _get_preset_description(name: str) -> str:
    """获取预设规则描述"""
    descriptions = {
        "青特地产": "分三阶段（地下室/单体结构/建筑），风险幅度±3%（电缆为±1000元/吨）",
        "专用条款项目": "无风险幅度，所有波动全额调差，不分阶段",
        "豪森海天映月": "分两阶段（地库/楼栋），风险幅度±3%或±5%",
        "莱山实验小学": "固定单价模式，不调差"
    }
    return descriptions.get(name, "")


@router.post("/validate-config")
async def validate_adjustment_config(config: Dict):
    """校验调差配置"""
    logger.info("[validate_adjustment_config] 校验配置")
    errors = []

    if '调差项目' not in config:
        errors.append("缺少必填项: 调差项目")

    if '价格规则' not in config:
        errors.append("缺少必填项: 价格规则")
    else:
        price_rule = config.get('价格规则', {})
        if '基准价来源' not in price_rule:
            errors.append("缺少必填项: 基准价来源")
        if '风险幅度' not in price_rule:
            errors.append("缺少必填项: 风险幅度")

    if '计算公式' not in config:
        errors.append("缺少必填项: 计算公式")
    else:
        formula = config.get('计算公式', {})
        if '调差公式模板' not in formula:
            errors.append("缺少必填项: 调差公式模板")
        if '税率' not in formula:
            errors.append("缺少必填项: 税率")

    logger.info(f"[validate_adjustment_config] 校验完成 | valid={len(errors)==0}, errors={len(errors)}")
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "config_complete": len(errors) == 0
    }


@router.post("/calculate", response_model=List[AdjustmentResult])
async def calculate_adjustment(
    project_id: str,
    phase_id: str = None,
    materials: List[dict] = [],
    price_history: dict = {}
):
    """计算调差"""
    logger.info(f"[calculate_adjustment] 计算调差 | project_id={project_id}, materials={len(materials)}")
    phases = [{'id': phase_id, 'phase_name': '阶段一', 'start_date': '2024-01-01', 'end_date': '2024-06-30'}]

    result = calculator.calculate_project_adjustment(
        project_id,
        phases,
        materials,
        price_history
    )

    logger.info(f"[calculate_adjustment] 计算完成 | phases={len(result.get('phases', []))}")
    return result.get('phases', [])


@router.get("/records", response_model=List[AdjustmentRecord])
async def list_adjustment_records(project_id: str = None, phase_id: str = None):
    """获取调差记录"""
    logger.info(f"[list_adjustment_records] 查询记录 | project_id={project_id}, phase_id={phase_id}")
    records = list(_adjustment_records_db.values())

    if project_id:
        records = [r for r in records if r.project_id == project_id]
    if phase_id:
        records = [r for r in records if r.phase_id == phase_id]

    logger.info(f"[list_adjustment_records] 返回 {len(records)} 条记录")
    return records


@router.post("/records", response_model=AdjustmentRecord)
async def create_adjustment_record(record: AdjustmentRecord):
    """创建调差记录"""
    logger.info(f"[create_adjustment_record] 创建记录 | project={record.project_id}, material={record.material_id}")
    try:
        import uuid
        record.id = str(uuid.uuid4())
        _adjustment_records_db[record.id] = record
        logger.info(f"[create_adjustment_record] 创建成功 | id={record.id}")
        return record
    except Exception as e:
        logger.error(f"[create_adjustment_record] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建记录失败")


@router.get("/project/{project_id}/summary")
async def get_project_adjustment_summary(project_id: str):
    """获取项目调差汇总"""
    logger.info(f"[get_project_adjustment_summary] 查询汇总 | project_id={project_id}")
    records = [r for r in _adjustment_records_db.values() if r.project_id == project_id]

    if not records:
        logger.info("[get_project_adjustment_summary] 无记录")
        return {
            'project_id': project_id,
            'total_adjustment': 0,
            'phases': [],
            'materials': []
        }

    phase_summary = {}
    material_summary = {}

    for record in records:
        phase_id = record.phase_id
        if phase_id not in phase_summary:
            phase_summary[phase_id] = {
                'phase_id': phase_id,
                'phase_name': record.phase_name,
                'total': 0
            }
        phase_summary[phase_id]['total'] += record.adjustment_amount

        material_id = record.material_id
        if material_id not in material_summary:
            material_summary[material_id] = {
                'material_id': material_id,
                'total': 0
            }
        material_summary[material_id]['total'] += record.adjustment_amount

    total = sum(r.adjustment_amount for r in records)

    result = {
        'project_id': project_id,
        'total_adjustment': round(total, 2),
        'adjustment_text': calculator.number_to_chinese(total),
        'phases': list(phase_summary.values()),
        'materials': list(material_summary.values())
    }
    logger.info(f"[get_project_adjustment_summary] 汇总完成 | total={result['total_adjustment']}")
    return result


@router.post("/export/{project_id}")
async def export_adjustment_report(project_id: str):
    """导出调差报告"""
    logger.info(f"[export_adjustment_report] 导出报告 | project_id={project_id}")
    records = [r for r in _adjustment_records_db.values() if r.project_id == project_id]

    if not records:
        logger.warning("[export_adjustment_report] 无调差记录")
        raise HTTPException(status_code=404, detail="无调差记录")

    total = sum(r.adjustment_amount for r in records)
    result = {
        'project_id': project_id,
        'total_adjustment': total,
        'adjustment_text': calculator.number_to_chinese(total),
        'records': [
            {
                'phase_name': r.phase_name,
                'base_price': r.base_price,
                'current_price': r.current_price,
                'change_rate': f"{r.change_rate:+.2f}%",
                'adjustment_amount': r.adjustment_amount
            }
            for r in records
        ]
    }
    logger.info(f"[export_adjustment_report] 导出成功 | total={total}")
    return result


# ============================================================
# 按项目调差计算 API（完整流程）
# ============================================================

@router.post("/calculate-by-project/{project_id}")
async def calculate_by_project(project_id: str):
    """
    按项目执行调差计算（完整流程）

    1. 获取项目数据和材料清单
    2. 获取预设规则配置
    3. 获取施工期价格（从价格数据或最新价格）
    4. 调用计算引擎
    5. 返回结果
    """
    logger.info(f"[calculate_by_project] 开始计算 | project_id={project_id}")
    try:
        from api.adjustment_project import load_projects

        projects = load_projects()
        project = None
        for p in projects:
            if p.get('id') == project_id:
                project = p
                break

        if not project:
            logger.warning(f"[calculate_by_project] 项目不存在 | project_id={project_id}")
            raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

        materials = project.get('materials', [])

        if not materials:
            logger.warning("[calculate_by_project] 项目未配置材料")
            return {
                "success": False,
                "error": "该项目尚未配置材料清单，请在'配置'中添加材料后重试"
            }

        rule_name = project.get('rule_name', '')
        preset_config = PRESET_RULES.get(rule_name)

        if not preset_config:
            preset_config = PRESET_RULES.get("朱家庄")

        base_prices = {}
        period_prices = {}

        for m in materials:
            material_name = m.get('name', '')
            base_price = m.get('base_price', 0)

            if not base_price:
                base_price = 4500

            base_prices[material_name] = base_price

            simulated_price = base_price * 1.05
            period_prices[material_name] = [{
                'date': datetime.now().strftime('%Y-%m-%d'),
                'price': round(simulated_price, 2),
                'source': '模拟数据'
            }]

        quantities = []
        for m in materials:
            quantities.append({
                'material_name': m.get('name', ''),
                'quantity': m.get('quantity', 0),
                'unit': m.get('unit', 't'),
                'phase': m.get('phase', '整体')
            })

        config_dict = _convert_preset_to_config(preset_config, rule_name)
        config = AdjustmentRuleConfig(**config_dict)

        input_data = CalculationInput(
            base_prices=base_prices,
            period_prices={
                k: [PriceData(**p) for p in v]
                for k, v in period_prices.items()
            },
            quantities=[
                QuantityData(**q) for q in quantities
            ]
        )

        engine = AdjustmentEngine(config)
        result = engine.calculate(input_data)

        for i, p in enumerate(projects):
            if p.get('id') == project_id:
                projects[i]['status'] = 'calculated'
                projects[i]['adjustment_result'] = result.model_dump(mode='json')
                projects[i]['updated_at'] = datetime.now().isoformat()
                break

        from api.adjustment_project import save_projects
        save_projects(projects)

        logger.info(f"[calculate_by_project] 计算完成 | total={result.total_adjustment}")
        return {
            "success": True,
            "data": result.model_dump(mode='json'),
            "rule_name": rule_name,
            "message": "计算完成"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[calculate_by_project] 计算失败 | {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def _convert_preset_to_config(preset: Dict, rule_name: str) -> Dict:
    """将预设规则转换为计算引擎配置格式"""
    # 基础配置
    config = {
        '项目名称': rule_name,
        '使用规则版本': preset.get('使用规则版本', 'v2.0'),
        '基础信息': preset.get('基础信息', {}),
        '调差项目': preset.get('基础信息', {}).get('调差项目', []),
        '价格规则': preset.get('价格规则', {}),
        '周期与阶段': preset.get('周期与阶段', {}),
        '计算公式': preset.get('计算公式', {}),
    }

    # 提取价格规则类配置
    price_rule = preset.get('价格规则', {})

    # 风险幅度
    risk_config = price_rule.get('风险幅度', {})
    risks = {}
    for mat_name, risk in risk_config.items():
        if isinstance(risk, dict):
            risks[mat_name] = {
                '类型': risk.get('类型', '百分比'),
                '值': risk.get('值', 3)
            }
    config['风险幅度'] = risks

    # 基准价来源
    source_map = {
        '造价信息': '造价信息',
        '我的钢铁网': '我的钢铁网',
        '上海有色网': '上海有色网',
        '投标价': '投标价',
        '合同约定价': '合同约定价'
    }
    config['基准价来源'] = source_map.get(price_rule.get('基准价来源', ''), '造价信息')
    config['基准价取价规则'] = price_rule.get('基准价取价规则', '')
    config['施工期价格采集规则'] = price_rule.get('施工期价格采集规则', '按月算术平均')
    config['价格取整规则'] = price_rule.get('价格取整规则', '保留2位小数')

    # 周期与阶段
    phase_config = preset.get('周期与阶段', {})
    config['是否分阶段调差'] = phase_config.get('是否分阶段调差', '否')
    config['阶段划分'] = phase_config.get('阶段划分', [])
    config['短周期处理'] = phase_config.get('短周期处理', '并入相邻月份')

    # 计算公式
    formula_config = preset.get('计算公式', {})

    # 调差公式模板映射
    formula_map = {
        '标准三段式': '标准三段式',
        '无风险幅度': '无风险幅度',
        '比例调差法': '比例调差法',
        '造价信息调整法': '造价信息调整法',
        '龙湖增值税率换算法': '龙湖增值税率换算法',
    }
    config['调差公式模板'] = formula_map.get(formula_config.get('调差公式模板', ''), '标准三段式')
    config['税率'] = formula_config.get('税率', 9)
    config['负数处理'] = formula_config.get('负数处理', '按实计算')
    config['取费规则'] = formula_config.get('取费规则', '只计税金')

    # 龙湖模式专用
    if rule_name == '龙湖集团':
        config['增值税率'] = formula_config.get('增值税率', 13)
        config['合同税率'] = formula_config.get('合同税率', 9)

    return config