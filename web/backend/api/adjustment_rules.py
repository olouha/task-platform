"""
调差规则配置 API（本地 SQLite 版）

数据落本地 SQLite，不再依赖 Supabase。
- 规则表: adjustment_rules(id, name, config_json, is_preset, derived_from, created_at, updated_at)
- 预设规则: 来自 models.adjustment_rules.PRESET_RULES（硬编码）
- 端点路径与响应字段保持前端现有契约不变
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from models.adjustment_rules import PRESET_RULES
from api.deps import get_current_user_can_delete

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/adjustment-rules", tags=["调差规则管理"])


# ============================================================
# 数据库初始化
# ============================================================

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_FILE = DB_DIR / "task_platform.db"


def _get_conn() -> sqlite3.Connection:
    """获取 SQLite 连接（每次新建，统一 row_factory）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """初始化规则表（幂等）"""
    logger.info(f"[init_db] 初始化调差规则表 | db={DB_FILE}")
    conn = _get_conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adjustment_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                config_json TEXT NOT NULL DEFAULT '{}',
                is_preset INTEGER NOT NULL DEFAULT 0,
                derived_from TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_adjustment_rules_created ON adjustment_rules(created_at)"
        )
        conn.commit()
        logger.info("[init_db] 调差规则表就绪")
    except Exception as e:
        logger.error(f"[init_db] 初始化失败 | {e}", exc_info=True)
        raise
    finally:
        conn.close()


# 模块导入时建表（FastAPI 启动时即生效）
init_db()


# ============================================================
# Pydantic 模型
# ============================================================


class CreateRuleRequest(BaseModel):
    """创建规则请求"""

    项目名称: str = Field(..., min_length=1, max_length=200)
    调差项目: List[Dict] = Field(default_factory=list)
    价格规则: Dict = Field(default_factory=dict)
    周期与阶段: Dict = Field(default_factory=dict)
    计算公式: Dict = Field(default_factory=dict)
    特殊规则: Optional[Dict] = None


class UpdateRuleRequest(BaseModel):
    """更新规则请求"""

    项目名称: Optional[str] = Field(default=None, min_length=1, max_length=200)
    调差项目: Optional[List[Dict]] = None
    价格规则: Optional[Dict] = None
    周期与阶段: Optional[Dict] = None
    计算公式: Optional[Dict] = None
    特殊规则: Optional[Dict] = None


class BidPriceItem(BaseModel):
    """投标价条目"""

    name: str = Field(..., min_length=1)
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

    preset_name: str = Field(..., min_length=1)
    项目名称: str = Field(..., min_length=1, max_length=200)
    自定义名称: Optional[str] = Field(default=None, max_length=200)


# ============================================================
# 行 -> 响应对象辅助
# ============================================================


def _row_to_rule(row: sqlite3.Row) -> Dict[str, Any]:
    """数据库行转为前端期望的规则对象"""
    try:
        cfg = json.loads(row["config_json"]) if row["config_json"] else {}
    except json.JSONDecodeError:
        logger.warning(f"[row_to_rule] config_json 解析失败 | id={row['id']}")
        cfg = {}

    return {
        "id": row["id"],
        "name": row["name"],
        "is_preset": bool(row["is_preset"]),
        "derived_from": row["derived_from"],
        "config": cfg,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


# ============================================================
# 端点
# ============================================================


@router.get("/presets", summary="获取预设规则列表")
async def get_preset_rules() -> Dict[str, Any]:
    """获取内置的预设规则（来自 models.PRESET_RULES）"""
    logger.info("[presets] 获取预设规则列表")
    return {
        "presets": list(PRESET_RULES.keys()),
        "details": PRESET_RULES,
    }


@router.get("/presets/{preset_name}", summary="获取单个预设规则")
async def get_preset_rule(preset_name: str) -> Dict[str, Any]:
    """获取单个预设规则完整配置"""
    logger.info(f"[presets_get] 获取预设 | name={preset_name}")
    if preset_name not in PRESET_RULES:
        raise HTTPException(status_code=404, detail=f"预设规则 '{preset_name}' 不存在")
    return PRESET_RULES[preset_name]


@router.get("/", summary="获取所有规则配置")
async def list_rules() -> Dict[str, Any]:
    """获取所有调差规则（按创建时间倒序）"""
    logger.info("[rules_list] 获取规则列表")
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM adjustment_rules ORDER BY created_at DESC"
        ).fetchall()
        rules = [_row_to_rule(r) for r in rows]
        logger.info(f"[rules_list] 返回 {len(rules)} 条规则")
        return {"rules": rules}
    except Exception as e:
        logger.error(f"[rules_list] 获取失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取规则失败: {e}")
    finally:
        conn.close()


@router.get("/{rule_id}", summary="获取单个规则配置")
async def get_rule(rule_id: str) -> Dict[str, Any]:
    """获取单条规则的完整配置"""
    logger.info(f"[rules_get] 获取规则 | id={rule_id}")
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM adjustment_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        return _row_to_rule(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[rules_get] 获取失败 | id={rule_id} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取规则失败: {e}")
    finally:
        conn.close()


@router.post("/", summary="创建规则配置")
async def create_rule(request: CreateRuleRequest) -> Dict[str, Any]:
    """创建新的调差规则配置"""
    rule_id = str(uuid.uuid4())
    now = _now_iso()

    config: Dict[str, Any] = {
        "项目名称": request.项目名称,
        "调差项目": request.调差项目,
        "价格规则": request.价格规则,
        "周期与阶段": request.周期与阶段,
        "计算公式": request.计算公式,
        "特殊规则": request.特殊规则 or {},
        "使用规则版本": "v1.0",
    }

    logger.info(
        f"[rules_create] 创建规则 | id={rule_id} | name={request.项目名称} | "
        f"items={len(request.调差项目)}"
    )

    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO adjustment_rules
                (id, name, config_json, is_preset, derived_from, created_at, updated_at)
            VALUES (?, ?, ?, 0, NULL, ?, ?)
            """,
            (rule_id, request.项目名称, json.dumps(config, ensure_ascii=False), now, now),
        )
        conn.commit()
        logger.info(f"[rules_create] 创建成功 | id={rule_id}")
        return {"id": rule_id, "name": request.项目名称, "success": True}
    except Exception as e:
        logger.error(f"[rules_create] 创建失败 | {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"创建规则失败: {e}")
    finally:
        conn.close()


@router.put("/{rule_id}", summary="更新规则配置")
async def update_rule(rule_id: str, request: UpdateRuleRequest, admin_account: str = Depends(get_current_user_can_delete)) -> Dict[str, Any]:
    """更新指定规则的字段"""
    logger.info(f"[rules_update] 更新规则 | id={rule_id}")

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM adjustment_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        try:
            cfg = json.loads(row["config_json"]) if row["config_json"] else {}
        except json.JSONDecodeError:
            cfg = {}

        # 按需覆盖字段
        if request.项目名称 is not None:
            cfg["项目名称"] = request.项目名称
        if request.调差项目 is not None:
            cfg["调差项目"] = request.调差项目
        if request.价格规则 is not None:
            cfg["价格规则"] = request.价格规则
        if request.周期与阶段 is not None:
            cfg["周期与阶段"] = request.周期与阶段
        if request.计算公式 is not None:
            cfg["计算公式"] = request.计算公式
        if request.特殊规则 is not None:
            cfg["特殊规则"] = request.特殊规则

        now = _now_iso()
        conn.execute(
            """
            UPDATE adjustment_rules
               SET name = ?,
                   config_json = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (
                cfg.get("项目名称", row["name"]),
                json.dumps(cfg, ensure_ascii=False),
                now,
                rule_id,
            ),
        )
        conn.commit()
        logger.info(f"[rules_update] 更新成功 | id={rule_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[rules_update] 更新失败 | id={rule_id} | {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新规则失败: {e}")
    finally:
        conn.close()


@router.delete("/{rule_id}", summary="删除规则配置")
async def delete_rule(rule_id: str, admin_account: str = Depends(get_current_user_can_delete)) -> Dict[str, Any]:
    """删除指定规则"""
    logger.info(f"[rules_delete] 删除规则 | id={rule_id}")

    conn = _get_conn()
    try:
        cur = conn.execute(
            "DELETE FROM adjustment_rules WHERE id = ?", (rule_id,)
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        logger.info(f"[rules_delete] 删除成功 | id={rule_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[rules_delete] 删除失败 | id={rule_id} | {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"删除规则失败: {e}")
    finally:
        conn.close()


@router.post("/apply-preset", summary="应用预设规则")
async def apply_preset_rule(request: ApplyPresetRequest) -> Dict[str, Any]:
    """将预设规则复制为新项目规则"""
    preset_name = request.preset_name
    logger.info(
        f"[rules_apply_preset] 应用预设 | preset={preset_name} | "
        f"project={request.项目名称}"
    )

    if preset_name not in PRESET_RULES:
        raise HTTPException(status_code=404, detail=f"预设规则 '{preset_name}' 不存在")

    preset = PRESET_RULES[preset_name]
    project_name = request.自定义名称 or request.项目名称

    rule_id = str(uuid.uuid4())
    now = _now_iso()

    # 把预设里的项目名称覆盖掉
    cfg: Dict[str, Any] = {**preset, "项目名称": project_name}

    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO adjustment_rules
                (id, name, config_json, is_preset, derived_from, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?, ?)
            """,
            (
                rule_id,
                project_name,
                json.dumps(cfg, ensure_ascii=False),
                preset_name,
                now,
                now,
            ),
        )
        conn.commit()
        logger.info(
            f"[rules_apply_preset] 应用成功 | id={rule_id} | from={preset_name}"
        )
        return {
            "id": rule_id,
            "name": project_name,
            "derived_from": preset_name,
            "success": True,
        }
    except Exception as e:
        logger.error(f"[rules_apply_preset] 失败 | {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"应用预设规则失败: {e}")
    finally:
        conn.close()


@router.get("/validate/config", summary="校验规则配置")
async def validate_rule_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """校验规则配置的完整性（与原 Supabase 版本保持一致）"""
    errors: List[str] = []

    if "调差项目" not in config or not config["调差项目"]:
        errors.append("缺少必填项: 调差项目")

    if "价格规则" not in config:
        errors.append("缺少必填项: 价格规则")
    else:
        price_rule = config["价格规则"]
        if "基准价来源" not in price_rule:
            errors.append("缺少必填项: 基准价来源")
        if "风险幅度" not in price_rule:
            errors.append("缺少必填项: 风险幅度")

    if "计算公式" not in config:
        errors.append("缺少必填项: 计算公式")
    else:
        formula = config["计算公式"]
        if "调差公式模板" not in formula:
            errors.append("缺少必填项: 调差公式模板")
        if "税率" not in formula:
            errors.append("缺少必填项: 税率")

    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/bid-prices", summary="保存投标价")
async def save_bid_prices(request: SaveBidPricesRequest) -> Dict[str, Any]:
    """为指定规则保存投标价列表"""
    logger.info(
        f"[bid_prices_save] 保存投标价 | rule_id={request.rule_id} | "
        f"count={len(request.bid_prices)}"
    )

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM adjustment_rules WHERE id = ?", (request.rule_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"规则 {request.rule_id} 不存在")

        try:
            cfg = json.loads(row["config_json"]) if row["config_json"] else {}
        except json.JSONDecodeError:
            cfg = {}

        cfg["投标价"] = [item.model_dump() for item in request.bid_prices]
        if request.特殊规则 is not None:
            cfg["特殊规则"] = request.特殊规则

        now = _now_iso()
        conn.execute(
            """
            UPDATE adjustment_rules
               SET config_json = ?, updated_at = ?
             WHERE id = ?
            """,
            (json.dumps(cfg, ensure_ascii=False), now, request.rule_id),
        )
        conn.commit()
        logger.info(
            f"[bid_prices_save] 保存成功 | rule_id={request.rule_id} | "
            f"count={len(request.bid_prices)}"
        )
        return {"success": True, "count": len(request.bid_prices)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[bid_prices_save] 失败 | {e}", exc_info=True)
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"保存投标价失败: {e}")
    finally:
        conn.close()


@router.get("/{rule_id}/bid-prices", summary="获取投标价")
async def get_bid_prices(rule_id: str) -> Dict[str, Any]:
    """获取规则的投标价数据"""
    logger.info(f"[bid_prices_get] 获取投标价 | rule_id={rule_id}")

    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT config_json FROM adjustment_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")

        try:
            cfg = json.loads(row["config_json"]) if row["config_json"] else {}
        except json.JSONDecodeError:
            cfg = {}

        return {"bid_prices": cfg.get("投标价", [])}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[bid_prices_get] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取投标价失败: {e}")
    finally:
        conn.close()