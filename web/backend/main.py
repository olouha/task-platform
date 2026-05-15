"""
FastAPI 应用入口
工程调差计算系统 - Railway 部署版本
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices
from services.websocket_manager import ws_manager


app = FastAPI(
    title="TaskPlatform API",
    description="工程调差计算系统 API",
    version="1.0.0"
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


@app.get("/")
async def root():
    """根路径"""
    return {"message": "TaskPlatform API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)