"""
WebSocket 推送服务
用于实时推送抓取状态到前端
"""
from fastapi import WebSocket
from typing import List
import asyncio
import json
from datetime import datetime


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_to_all(self, message: dict):
        """向所有连接的客户端发送消息"""
        if not self.active_connections:
            return

        message_json = json.dumps(message, ensure_ascii=False)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"发送消息失败: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_price_update(self, event: str, data: dict):
        """广播价格更新消息"""
        message = {
            "type": event,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        await self.send_to_all(message)

    async def notify_fetch_started(self):
        """通知抓取开始"""
        await self.broadcast_price_update("fetch_started", {
            "message": "开始抓取数据..."
        })

    async def notify_fetch_success(self, prices_count: int, date: str):
        """通知抓取成功"""
        await self.broadcast_price_update("fetch_success", {
            "message": f"抓取成功！共{prices_count}条数据",
            "prices_count": prices_count,
            "date": date
        })

    async def notify_fetch_failed(self, error: str):
        """通知抓取失败"""
        await self.broadcast_price_update("fetch_failed", {
            "message": f"抓取失败: {error}",
            "error": error
        })


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()
