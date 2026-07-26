"""
FastAPI 应用入口
工程调差计算系统 - Railway 部署版本
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import asyncio
import os

from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, adjustment_prices_batch, building_schedule, building_adjustment, cost_history, data_manager, adjustment_template, indicator_report, fetch_history, indicator_library, auth
from api import ai_chat, ai_self_review
from api.rebar import router as rebar_router
from services.websocket_manager import ws_manager
from services.rate_limiter import get_rate_limiter
from fastapi import WebSocket, WebSocketDisconnect

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 获取前端目录路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TaskPlatform API",
    description="工程调差计算系统 API",
    version="1.0.0"
)

# 挂载静态文件
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
    logger.info(f"[startup] 前端静态文件已挂载 | path={FRONTEND_DIST}")
else:
    logger.warning(f"[startup] 前端dist目录不存在 | path={FRONTEND_DIST}")

# 根目录静态资源（图片等）—— 用 FileResponse 精确路由，避免 mount 单文件的 307 重定向问题
ROOT_STATIC_FILES = [
    "ai-logo.jpg", "design-logo.png", "logo-title.png", "logo.jpg",
    "knigHts_logo.png", "knigHts_logo_small.png", "knigHts_logo_large.png",
    "vite.svg",
]


def _make_root_file_handler(filename: str):
    """生成单个根目录静态文件的处理器"""
    async def serve_root_file():
        file_path = os.path.join(FRONTEND_DIST, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        logger.warning(f"[serve_root_file] 文件不存在 | file={filename}")
        raise HTTPException(status_code=404, detail="Not Found")
    return serve_root_file


for _fn in ROOT_STATIC_FILES:
    app.add_api_route(f"/{_fn}", _make_root_file_handler(_fn), methods=["GET"])

# CORS 配置（生产环境应限制来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 部署时改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 限流中间件（已禁用，调试时启用）
# @app.middleware("http")
# async def rate_limit_middleware(request, call_next):
#     """HTTP请求限流中间件"""
#     from fastapi.responses import JSONResponse
#
#     limiter = get_rate_limiter()
#     client_ip = request.client.host if request.client else 'unknown'
#
#     # 排除健康检查和根路径
#     if request.url.path in ['/', '/health', '/docs', '/openapi.json', '/redoc']:
#         return await call_next(request)
#
#     allowed, message = limiter.check_ip(client_ip)
#     if not allowed:
#         logger.warning(f"[RateLimit] 限流触发 | ip={client_ip}, path={request.url.path}")
#         return JSONResponse(
#             status_code=429,
#             content={"detail": message}
#         )
#
#     response = await call_next(request)
#     return response

# 注册API路由
app.include_router(auth.router, prefix="/api/auth", tags=["用户认证"])
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(materials.router, prefix="/api/materials", tags=["材料管理"])
app.include_router(price_sources.router, prefix="/api/price-sources", tags=["价格来源"])
app.include_router(price_history.router, prefix="/api/price-history", tags=["价格历史"])
app.include_router(adjustments.router, prefix="/api", tags=["调差计算"])
app.include_router(indicators.router, prefix="/api/indicators", tags=["指标管理"])
app.include_router(sync.router, prefix="/api/sync", tags=["数据同步"])
app.include_router(adjustment_rules.router, prefix="/api", tags=["调差规则管理"])
app.include_router(scheduler_api.router, prefix="/api/scheduler", tags=["定时任务调度"])
app.include_router(fetch_api.router, tags=["人工抓取"])
app.include_router(cron_fetch.router, prefix="/api/cron", tags=["定时抓取"])
app.include_router(cost_reference.router, prefix="/api/cost-reference", tags=["造价参考价"])
app.include_router(adjustment_project.router, tags=["调差项目管理"])
app.include_router(ai_chat.router, prefix="/api", tags=["AI对话"])
app.include_router(price_history_db.router, prefix="/api/price-db", tags=["价格数据库"])
app.include_router(ai_self_review.router, tags=["AI自检复盘"])
app.include_router(file_parser.router, prefix="/api", tags=["文件解析"])
app.include_router(adjustment_prices.router, prefix="/api", tags=["调差价格获取"])
app.include_router(adjustment_prices_batch.router, prefix="/api", tags=["调差价格批量获取"])
app.include_router(building_schedule.router, prefix="/api/building-schedule", tags=["楼栋施工时间"])
app.include_router(building_adjustment.router, prefix="/api/building-adjustment", tags=["楼栋调差计算"])
app.include_router(cost_history.router, prefix="/api/cost-history", tags=["造价历史参考价"])
app.include_router(data_manager.router, prefix="/api/data-manager", tags=["数据管理"])
app.include_router(adjustment_template.router, prefix="/api/adjustment-template", tags=["调差模板"])
app.include_router(indicator_report.router, prefix="/api/indicator-report", tags=["指标库分析报告"])
app.include_router(fetch_history.router, prefix="/api/fetch-history", tags=["历史数据抓取"])
app.include_router(indicator_library.router, prefix="/api/indicator-library", tags=["指标库管理"])

# 烟台钢筋价格统一API
app.include_router(rebar_router)


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    logger.info("[root] 根路径访问")
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "TaskPlatform API", "version": "1.0.0"}


@app.get("/api/stats")
async def get_stats():
    """获取系统统计信息"""
    from services.supabase_service import SupabaseService
    supabase = SupabaseService()
    stats = supabase.get_statistics()
    return {
        "projects": stats.get('total_projects', 0),
        "materials": stats.get('total_materials', 0),
        "priceHistory": stats.get('total_price_sources', 0),
        "categories": stats.get('categories', []),
        "timestamp": ""
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    logger.debug("[health_check] 健康检查")
    limiter = get_rate_limiter()
    limiter_stats = limiter.get_stats()
    return {
        "status": "healthy",
        "rate_limit": limiter_stats
    }


@app.post("/api/admin/init-knowledge-base")
async def init_knowledge_base():
    """初始化知识库数据（管理员功能）"""
    from scripts.init_knowledge_base import init_knowledge_base as init_kb
    logger.info("[init_knowledge_base] 执行知识库初始化")
    result = init_kb()
    return result


@app.get("/api/knowledge-base/stats")
async def get_knowledge_base_stats():
    """获取知识库统计信息"""
    from services.supabase_service import SupabaseService
    supabase = SupabaseService()
    docs = supabase.list_kb_documents(limit=1000)

    # 按分类统计
    categories: Dict[str, int] = {}
    for doc in docs:
        cat = doc.get('category', '未分类')
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total": len(docs),
        "categories": categories
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点 - 接收推送消息"""
    logger.info(f"[websocket] 新连接请求 | client={websocket.client}")
    await ws_manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息（如心跳包 pong）
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                if data == "ping" or data == '{"type":"ping"}':
                    # 响应客户端心跳
                    await websocket.send_text('{"type":"pong"}')
                else:
                    logger.debug(f"[websocket] 收到消息 | data={data[:100]}")
            except asyncio.TimeoutError:
                # 60秒无消息，发送 ping
                try:
                    await websocket.send_text('{"type":"ping"}')
                except:
                    break
    except WebSocketDisconnect:
        logger.info(f"[websocket] 客户端断开连接 | client={websocket.client}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[websocket] 连接异常 | client={websocket.client} | error={e}", exc_info=True)
        ws_manager.disconnect(websocket)


# SPA fallback：前端路由（如 /dashboard、/user-management、/profile）在被刷新或直接访问时，
# 后端需返回 index.html 交由前端路由处理，否则 FastAPI 会返回 404 Not Found。
# 必须放在所有 API/静态路由之后注册（catch-all）。
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    # API 与静态资源走各自路由，未命中的仍按 404 处理（不返回 index.html）
    if (full_path.startswith("api/")
            or full_path.startswith("assets/")
            or full_path in ROOT_STATIC_FILES):
        raise HTTPException(status_code=404, detail="Not Found")
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        logger.debug(f"[spa_fallback] 返回 index.html | path={full_path}")
        return FileResponse(index_path)
    logger.warning(f"[spa_fallback] 前端 dist 未构建 | path={full_path}")
    raise HTTPException(status_code=404, detail="前端未构建")


if __name__ == "__main__":
    import uvicorn
    logger.info("[startup] 启动应用")
    uvicorn.run(app, host="0.0.0.0", port=8000)