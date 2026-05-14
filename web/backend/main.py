"""
FastAPI 应用入口
工程调差计算系统
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from contextlib import asynccontextmanager
import os
import json

from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices
from services.websocket_manager import ws_manager


# 前端路径
FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("App started")
    print(f"Frontend path: {FRONTEND_PATH}")
    print(f"Frontend exists: {os.path.exists(FRONTEND_PATH)}")
    yield
    print("App stopped")


app = FastAPI(
    title="TaskPlatform API",
    description="工程调差计算系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(materials.router, prefix="/api/materials", tags=["材料管理"])
app.include_router(price_sources.router, prefix="/api/price-sources", tags=["价格来源"])
app.include_router(price_history.router, prefix="/api/price-history", tags=["价格历史"])
app.include_router(adjustments.router, prefix="/api/adjustments", tags=["调差计算"])
app.include_router(indicators.router, prefix="/api/indicators", tags=["指标管理"])
app.include_router(sync.router, prefix="/api/sync", tags=["数据同步"])
app.include_router(yantai_prices.router, prefix="/api/yantai-prices", tags=["烟台钢筋价格"])


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接，可以接收前端消息
            data = await websocket.receive_text()
            # 解析并处理消息
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket错误: {e}")
        ws_manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    index_path = os.path.join(FRONTEND_PATH, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return f.read()
    return {"message": "TaskPlatform API", "version": "1.0.0"}


@app.get("/{full_path:path}")
async def serve_static(full_path: str):
    """服务静态文件"""
    # API路由已经在上面，不会匹配到这里
    # 只处理前端静态文件
    if full_path.startswith('api/'):
        return {"error": "API not found"}

    file_path = os.path.join(FRONTEND_PATH, full_path)

    # 安全检查
    if '..' in full_path or full_path.startswith('/'):
        return {"error": "Invalid path"}

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    # 返回index.html（SPA路由支持）
    index_path = os.path.join(FRONTEND_PATH, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {"error": "File not found"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}