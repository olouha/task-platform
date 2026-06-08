"""
WebSocket 推送服务
用于实时推送抓取状态到前端
"""
from fastapi import WebSocket
from typing import List, Set
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_ids: Set[str] = set()  # 用于去重
        self._heartbeat_task: asyncio.Task = None
        self._heartbeat_interval = 30  # 心跳间隔（秒）

    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        # 避免重复连接
        client_id = f"{websocket.client.host}:{websocket.client.port}"
        if client_id in self.connection_ids:
            logger.warning(f"[ws_manager] 检测到重复连接，断开旧连接 | client={client_id}")
            # 查找并断开旧连接
            for conn in self.active_connections:
                if f"{conn.client.host}:{conn.client.port}" == client_id:
                    self.disconnect(conn)
                    break

        self.active_connections.append(websocket)
        self.connection_ids.add(client_id)
        logger.info(f"[ws_manager] 连接已建立 | 当前连接数={len(self.active_connections)} | client={websocket.client}")

        # 启动心跳任务（如果尚未启动）
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            client_id = f"{websocket.client.host}:{websocket.client.port}"
            self.active_connections.remove(websocket)
            self.connection_ids.discard(client_id)
            logger.info(f"[ws_manager] 连接已断开 | 当前连接数={len(self.active_connections)} | client={websocket.client}")

    async def send_to_all(self, message: dict, timeout: float = 2.0):
        """
        向所有连接的客户端发送消息（并发推送，带超时）

        Args:
            message: 要发送的消息字典
            timeout: 每个连接的超时时间（秒）
        """
        if not self.active_connections:
            logger.warning(f"[ws_manager] 无活跃连接，跳过推送 | message_type={message.get('type')}")
            return

        logger.info(f"[ws_manager] 推送消息 | type={message.get('type')} | 连接数={len(self.active_connections)}")

        message_json = json.dumps(message, ensure_ascii=False)

        # 并发发送到所有连接，带超时
        tasks = []
        for connection in self.active_connections:
            tasks.append(self._send_with_timeout(connection, message_json, timeout))

        # 等待所有发送任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查结果并清理断开的连接
        disconnected = []
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[ws_manager] 发送失败 | 连接={i+1}/{len(self.active_connections)} | error={type(result).__name__}: {result}")
                disconnected.append(self.active_connections[i])
            else:
                success_count += 1

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

        if disconnected:
            logger.info(f"[ws_manager] 清理断开连接 | 数量={len(disconnected)} | 剩余={len(self.active_connections)}")

        logger.info(f"[ws_manager] 推送完成 | 成功={success_count}/{len(self.active_connections)}")

    async def _send_with_timeout(self, connection: WebSocket, message: str, timeout: float):
        """带超时的发送"""
        try:
            await asyncio.wait_for(connection.send_text(message), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"发送超时（{timeout}秒）")
        except Exception as e:
            raise e

    async def _heartbeat_loop(self):
        """心跳循环 - 定期发送 ping 消息检测连接状态"""
        logger.info(f"[ws_manager] 心跳任务已启动 | 间隔={self._heartbeat_interval}秒")
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if self.active_connections:
                    await self._send_heartbeat()
            except asyncio.CancelledError:
                logger.info(f"[ws_manager] 心跳任务已取消")
                break
            except Exception as e:
                logger.error(f"[ws_manager] 心跳任务异常 | {e}", exc_info=True)

    async def _send_heartbeat(self):
        """发送心跳消息"""
        ping_msg = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        ping_json = json.dumps(ping_msg, ensure_ascii=False)

        tasks = []
        for connection in self.active_connections:
            tasks.append(self._send_with_timeout(connection, ping_json, timeout=1.0))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 清理无响应的连接
        disconnected = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.debug(f"[ws_manager] 心跳失败 | 连接={i+1} | error={type(result).__name__}")
                disconnected.append(self.active_connections[i])

        for conn in disconnected:
            self.disconnect(conn)

        if disconnected:
            logger.info(f"[ws_manager] 心跳清理断开连接 | 数量={len(disconnected)}")

    async def broadcast_price_update(self, event: str, data: dict):
        """广播价格更新消息"""
        message = {
            "type": event,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        logger.info(f"[ws_manager] 广播消息 | event={event} | data_keys={list(data.keys())}")
        await self.send_to_all(message)

    async def notify_fetch_started(self):
        """通知抓取开始"""
        await self.broadcast_price_update("fetch_started", {
            "message": "开始抓取数据..."
        })

    async def notify_fetch_progress(self, current: int, total: int, message: str = ""):
        """通知抓取进度"""
        await self.broadcast_price_update("fetch_progress", {
            "message": f"抓取中... {current}/{total} {message}",
            "current": current,
            "total": total
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

    async def cleanup_all(self):
        """清理所有连接（用于服务关闭）"""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        self.active_connections.clear()
        self.connection_ids.clear()
        logger.info(f"[ws_manager] 所有连接已清理")


# 全局WebSocket管理器实例
ws_manager = WebSocketManager()
