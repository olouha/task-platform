"""
FastAPI 应用入口
工程调差计算系统 - Railway 部署版本
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, building_schedule, building_adjustment, cost_history, yantai_db
from api import ai_chat, ai_self_review
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
app.include_router(adjustments.router, prefix="/api", tags=["调差计算"])
app.include_router(indicators.router, prefix="/api/indicators", tags=["指标管理"])
app.include_router(sync.router, prefix="/api/sync", tags=["数据同步"])
app.include_router(yantai_prices.router, prefix="/api/yantai-prices", tags=["烟台钢筋价格"])
app.include_router(adjustment_rules.router, prefix="/api/adjustment-rules", tags=["调差规则管理"])
app.include_router(scheduler_api.router, prefix="/api/scheduler", tags=["定时任务调度"])
app.include_router(fetch_api.router, prefix="/api/fetch", tags=["人工抓取"])
app.include_router(cron_fetch.router, prefix="/api/cron", tags=["定时抓取"])
app.include_router(cost_reference.router, prefix="/api/cost-reference", tags=["造价参考价"])
app.include_router(adjustment_project.router, tags=["调差项目管理"])
app.include_router(ai_chat.router, prefix="/api", tags=["AI对话"])
app.include_router(price_history_db.router, prefix="/api/price-db", tags=["价格数据库"])
app.include_router(ai_self_review.router, tags=["AI自检复盘"])
app.include_router(file_parser.router, prefix="/api", tags=["文件解析"])
app.include_router(adjustment_prices.router, prefix="/api/adjustment-prices", tags=["调差价格获取"])
app.include_router(building_schedule.router, prefix="/api/building-schedule", tags=["楼栋施工时间"])
app.include_router(building_adjustment.router, prefix="/api/building-adjustment", tags=["楼栋调差计算"])
app.include_router(yantai_db.router, prefix="/api/yantai-db", tags=["烟台钢筋数据库"])
app.include_router(cost_history.router, prefix="/api/cost-history", tags=["造价历史参考价"])


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