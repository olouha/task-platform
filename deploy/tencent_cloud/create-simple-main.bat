@echo off
chcp 65001 >nul
echo Creating simplified main.py for server...

(
echo """
echo FastAPI Application Entry Point - Server Compatible Version
echo """
echo.
echo from fastapi import FastAPI
echo from fastapi.middleware.cors import CORSMiddleware
echo import logging
echo import os
echo import asyncio
echo.
echo from api import projects, materials, price_sources, price_history, adjustments, indicators, sync, yantai_prices, adjustment_rules, scheduler_api, fetch as fetch_api, cron_fetch, cost_reference, adjustment_project, history_fetch, price_history_db, file_parser, adjustment_prices, building_schedule, building_adjustment, cost_history
echo from api import ai_chat, ai_self_review
echo from services.websocket_manager import ws_manager
echo from fastapi import WebSocket, WebSocketDisconnect
echo.
echo logging.basicConfig^(level=logging.INFO, format='%%(asctime^)s - %%(name^)s - %^(levelname^)s - %^(message^)s'^)
echo logger = logging.getLogger^(__name__^)
echo.
echo app = FastAPI^(title="TaskPlatform API", description="Engineering Adjustment System", version="1.0.0"^)
echo.
echo app.add_middleware^(
echo     CORSMiddleware,
echo     allow_origins=["*"],
echo     allow_credentials=True,
echo     allow_methods=["*"],
echo     allow_headers=["*"],
echo ^)
echo.
echo # Register routes
echo app.include_router^(projects.router, prefix="/api/projects", tags=["Projects"]^)
echo app.include_router^(materials.router, prefix="/api/materials", tags=["Materials"]^)
echo app.include_router^(price_sources.router, prefix="/api/price-sources", tags=["Price Sources"]^)
echo app.include_router^(price_history.router, prefix="/api/price-history", tags=["Price History"]^)
echo app.include_router^(adjustments.router, prefix="/api", tags=["Adjustments"]^)
echo app.include_router^(indicators.router, prefix="/api/indicators", tags=["Indicators"]^)
echo app.include_router^(sync.router, prefix="/api/sync", tags=["Sync"]^)
echo app.include_router^(yantai_prices.router, prefix="/api/yantai-prices", tags=["Yantai Prices"]^)
echo app.include_router^(adjustment_rules.router, prefix="/api/adjustment-rules", tags=["Adjustment Rules"]^)
echo app.include_router^(scheduler_api.router, prefix="/api/scheduler", tags=["Scheduler"]^)
echo app.include_router^(fetch_api.router, prefix="/api/fetch", tags=["Fetch"]^)
echo app.include_router^(cron_fetch.router, prefix="/api/cron", tags=["Cron Fetch"]^)
echo app.include_router^(cost_reference.router, prefix="/api/cost-reference", tags=["Cost Reference"]^)
echo app.include_router^(adjustment_project.router, tags=["Adjustment Project"]^)
echo app.include_router^(ai_chat.router, prefix="/api", tags=["AI Chat"]^)
echo app.include_router^(price_history_db.router, prefix="/api/price-db", tags=["Price DB"]^)
echo app.include_router^(ai_self_review.router, tags=["AI Self Review"]^)
echo app.include_router^(file_parser.router, prefix="/api", tags=["File Parser"]^)
echo app.include_router^(adjustment_prices.router, prefix="/api/adjustment-prices", tags=["Adjustment Prices"]^)
echo app.include_router^(building_schedule.router, prefix="/api/building-schedule", tags=["Building Schedule"]^)
echo app.include_router^(building_adjustment.router, prefix="/api/building-adjustment", tags=["Building Adjustment"]^)
echo app.include_router^(cost_history.router, prefix="/api/cost-history", tags=["Cost History"]^)
echo.
echo @app.get^("/")
echo async def root^(^):
echo     return {"message": "TaskPlatform API", "version": "1.0.0"}
echo.
echo @app.get^("/health"^)
echo async def health_check^(^):
echo     return {"status": "healthy"}
echo.
echo @app.websocket^("/ws"^)
echo async def websocket_endpoint^(websocket: WebSocket^):
echo     await ws_manager.connect^(websocket^)
echo     try:
echo         while True:
echo             try:
echo                 data = await asyncio.wait_for^(websocket.receive_text^(^), timeout=60^)
echo                 if data == "ping" or data == '{"type":"ping"}':
echo                     await websocket.send_text^('{"type":"pong"}'^)
echo             except asyncio.TimeoutError:
echo                 try:
echo                     await websocket.send_text^('{"type":"ping"}'^)
echo                 except:
echo                     break
echo     except WebSocketDisconnect:
echo         ws_manager.disconnect^(websocket^)
echo     except Exception as e:
echo         logger.error^(f"WS error: {e}"^)
echo         ws_manager.disconnect^(websocket^)
echo.
echo if __name__ == "__main__":
echo     import uvicorn
echo     uvicorn.run^(app, host="0.0.0.0", port=8000^)
) > "%TEMP%\main_py_content.txt"

echo File created at %TEMP%\main_py_content.txt
echo Please copy this content to C:\task-platform-main\web\backend\main.py
echo.
pause
