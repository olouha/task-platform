"""
AI 自检复盘 API
提供自检状态查询、手动复盘、自动复盘控制等接口
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Dict, Optional

from services.ai_self_review import get_self_review_service

router = APIRouter(prefix="/ai/self-review", tags=["AI自检复盘"])


@router.get("/status")
async def get_review_status():
    """
    获取自检系统状态

    返回:
    - 历史记录数量
    - 统计数据
    - 自动复盘状态
    """
    service = get_self_review_service()
    return {
        "service": "running",
        **service.get_stats()
    }


@router.get("/products")
async def get_products(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    abnormal_only: bool = Query(False, description="仅返回异常产物")
):
    """
    获取最近的 AI 产物记录

    参数:
        limit: 返回数量（默认 20）
        abnormal_only: 仅返回异常产物

    返回:
        产物列表
    """
    service = get_self_review_service()
    return {
        "data": service.get_recent_products(limit, abnormal_only),
        "total": service.stats["total_generated"]
    }


@router.post("/review")
async def trigger_review():
    """
    手动触发全链路复盘

    复盘所有历史产物，生成报告
    """
    service = get_self_review_service()
    report = service.full_review()
    return report


@router.post("/review/start")
async def start_auto_review(interval: int = Query(300, ge=60, le=3600, description="复盘间隔（秒）")):
    """
    启动自动复盘

    参数:
        interval: 复盘间隔（秒），默认 300（5分钟）
    """
    service = get_self_review_service()
    service.start_auto_review(interval)
    return {
        "success": True,
        "message": f"自动复盘已启动，间隔 {interval} 秒"
    }


@router.post("/review/stop")
async def stop_auto_review():
    """
    停止自动复盘
    """
    service = get_self_review_service()
    service.stop_auto_review()
    return {"success": True, "message": "自动复盘已停止"}


@router.get("/rules")
async def get_inspection_rules():
    """
    获取自检规则列表
    """
    service = get_self_review_service()
    return {
        "rules": [
            {"id": 1, "name": "非空检查", "description": "内容不能为空"},
            {"id": 2, "name": "最小长度检查", "description": f"内容长度至少 {service.MIN_CONTENT_LENGTH} 字符"},
            {"id": 3, "name": "最大长度检查", "description": f"内容长度不超过 {service.MAX_CONTENT_LENGTH} 字符"},
            {"id": 4, "name": "敏感词检查", "description": f"禁止包含 {len(service.SENSITIVE_WORDS)} 个敏感词"}
        ],
        "sensitive_words": service.SENSITIVE_WORDS
    }


@router.post("/rules/sensitive-words")
async def add_sensitive_word(word: str = Query(..., description="敏感词")):
    """
    添加敏感词

    参数:
        word: 要添加的敏感词
    """
    service = get_self_review_service()
    if word not in service.SENSITIVE_WORDS:
        service.SENSITIVE_WORDS.append(word)
        return {"success": True, "message": f"已添加敏感词: {word}"}
    return {"success": False, "message": "敏感词已存在"}


@router.delete("/rules/sensitive-words/{word}")
async def remove_sensitive_word(word: str):
    """
    删除敏感词

    参数:
        word: 要删除的敏感词
    """
    service = get_self_review_service()
    if word in service.SENSITIVE_WORDS:
        service.SENSITIVE_WORDS.remove(word)
        return {"success": True, "message": f"已删除敏感词: {word}"}
    return {"success": False, "message": "敏感词不存在"}