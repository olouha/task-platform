"""
定时任务 API v2.0
支持多材料抓取
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

_scheduler = None


def get_scheduler():
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        from services.price_fetch_scheduler import PriceFetchScheduler, MaterialPriceResult, FetchResult
        _scheduler = PriceFetchScheduler()
    return _scheduler


class MaterialPriceResponse(BaseModel):
    """材料价格响应"""
    material_id: str
    material_name: str
    spec: str
    price: float
    unit: str
    change_rate: float


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    source_id: str
    source_name: str
    scraper_type: str
    status: str
    last_fetch: Optional[str] = None
    next_fetch: Optional[str] = None
    last_prices: List[dict] = []
    last_error: Optional[str] = None


class ExecuteResponse(BaseModel):
    """执行结果响应"""
    success: bool
    source_name: str
    prices: List[MaterialPriceResponse] = []
    error_message: str = ""
    fetched_at: str = ""


@router.get("/status", response_model=List[TaskStatusResponse])
async def get_all_task_status():
    """获取所有任务状态"""
    scheduler = get_scheduler()
    tasks = scheduler.list_tasks()

    return [
        TaskStatusResponse(
            source_id=t['source_id'],
            source_name=t['source_name'],
            scraper_type=t['scraper_type'],
            status=t['status'],
            last_fetch=t.get('last_fetch'),
            next_fetch=t.get('next_fetch'),
            last_prices=t.get('last_prices', []),
            last_error=t.get('last_error')
        )
        for t in tasks
    ]


@router.get("/{source_id}/status", response_model=TaskStatusResponse)
async def get_task_status(source_id: str):
    """获取特定任务状态"""
    scheduler = get_scheduler()
    status = scheduler.get_task_status(source_id)

    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(**status)


@router.post("/{source_id}/execute", response_model=ExecuteResponse)
async def execute_task(source_id: str, force: bool = False):
    """执行指定任务"""
    scheduler = get_scheduler()
    task = scheduler.tasks.get(source_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not force:
        can_execute, reason = task.check_rate_limit()
        if not can_execute:
            raise HTTPException(status_code=429, detail=reason)

    result = scheduler.execute_task(task)

    return ExecuteResponse(
        success=result.success,
        source_name=result.source_name,
        prices=[
            MaterialPriceResponse(
                material_id=p.material_id,
                material_name=p.material_name,
                spec=p.spec,
                price=p.price,
                unit=p.unit,
                change_rate=p.change_rate
            )
            for p in result.prices
        ],
        error_message=result.error_message,
        fetched_at=result.fetched_at
    )


@router.post("/execute-all")
async def execute_all_pending():
    """执行所有待处理任务"""
    scheduler = get_scheduler()
    results = scheduler.execute_all_pending()

    return {
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
        "failed_count": sum(1 for r in results if not r.success),
        "total_prices": sum(len(r.prices) for r in results),
        "results": [
            {
                "success": r.success,
                "source_name": r.source_name,
                "prices": [
                    {
                        "material_id": p.material_id,
                        "material_name": p.material_name,
                        "price": p.price,
                        "unit": p.unit
                    }
                    for p in r.prices
                ],
                "error_message": r.error_message
            }
            for r in results
        ]
    }


@router.post("/execute-all-sites")
async def execute_all_sites(force: bool = False):
    """执行所有网站（每天一次）"""
    scheduler = get_scheduler()
    results = scheduler.execute_all_sites(force=force)

    return {
        "total_sites": len(scheduler.tasks),
        "executed": len(results),
        "success_count": sum(1 for r in results if r.success),
        "total_prices": sum(len(r.prices) for r in results),
        "results": [
            {
                "success": r.success,
                "source_name": r.source_name,
                "prices": [
                    {
                        "material_name": p.material_name,
                        "price": p.price,
                        "unit": p.unit
                    }
                    for p in r.prices
                ],
                "error_message": r.error_message
            }
            for r in results
        ]
    }


@router.post("/force-fetch-all")
async def force_fetch_all():
    """强制执行所有任务（忽略频率限制）"""
    scheduler = get_scheduler()
    results = scheduler.force_fetch_all()

    return {
        "total": len(results),
        "success_count": sum(1 for r in results if r.success),
        "total_prices": sum(len(r.prices) for r in results),
        "results": [
            {
                "success": r.success,
                "source_name": r.source_name,
                "prices_count": len(r.prices),
                "prices": [
                    {
                        "material_name": p.material_name,
                        "price": p.price,
                        "unit": p.unit
                    }
                    for p in r.prices
                ],
                "error_message": r.error_message
            }
            for r in results
        ]
    }


@router.post("/sync")
async def sync_from_database():
    """从数据库同步任务"""
    scheduler = get_scheduler()

    try:
        from supabase import create_client

        supabase_url = "YOUR_SUPABASE_URL"
        supabase_key = "YOUR_SUPABASE_KEY"
        client = create_client(supabase_url, supabase_key)

        response = client.table('price_sources').select('*').eq('is_active', True).execute()

        sources = [
            {
                'id': s['id'],
                'name': s['name'],
                'website_url': s.get('website_url', ''),
                'price_url': s.get('price_url', ''),
                'auth_username': s.get('auth_username'),
                'auth_type': s.get('auth_type', 'form')
            }
            for s in response.data
        ]

        scheduler.sync_from_database(sources)

        return {
            "success": True,
            "message": f"已同步 {len(sources)} 个任务"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/next-execution")
async def get_next_execution():
    """获取下次执行时间"""
    scheduler = get_scheduler()

    next_times = []
    for task in scheduler.tasks.values():
        if task.next_fetch:
            next_times.append({
                'source_id': task.source_id,
                'source_name': task.source_name,
                'next_fetch': task.next_fetch.isoformat()
            })

    next_times.sort(key=lambda x: x['next_fetch'])

    return {
        "next_executions": next_times[:10]
    }


@router.get("/supported-materials")
async def get_supported_materials():
    """获取支持的材料列表"""
    from services.authenticated_scraper import ScraperFactory

    all_materials = ScraperFactory.get_all_materials()

    result = []
    for scraper_type, materials in all_materials.items():
        for m in materials:
            result.append({
                'scraper_type': scraper_type,
                'material_id_prefix': m['id_prefix'],
                'material_name': m['name'],
                'spec': m.get('spec', ''),
                'unit': m['unit']
            })

    return {
        "total_materials": len(result),
        "materials": result
    }