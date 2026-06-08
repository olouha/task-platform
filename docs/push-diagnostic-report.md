# 推送系统诊断报告

## 问题概述
用户报告：推送信息经常加载不出来、丢失或不完整

## 根本原因分析

### 🔴 P0 级问题：后端缺少 WebSocket 端点定义

**位置**：`web/backend/main.py`

**问题描述**：
- `main.py` 第12行导入了 `ws_manager`：`from services.websocket_manager import ws_manager`
- 但**从未定义任何 WebSocket 端点**供前端连接
- 缺少 `@app.websocket("/ws")` 装饰器

**代码证据**：
```python
# main.py - 只有导入，没有端点定义
from services.websocket_manager import ws_manager

# 缺少这样的代码：
# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await ws_manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive_text()
#     except WebSocketDisconnect:
#         ws_manager.disconnect(websocket)
```

**影响**：
- 前端尝试连接 `ws://localhost:8000/ws` 时无法建立连接
- 所有推送消息**完全无法送达**
- 这是最严重的根本问题

**前端连接代码**（`web/frontend/src/pages/PriceMonitor.tsx` 第134行）：
```typescript
const wsUrl = config.apiUrl.replace(/^https?:/, wsProtocol) + '/ws'
const ws = new WebSocket(wsUrl)  // 连接失败，因为后端没有 /ws 端点
```

---

### 🟡 P1 级问题：日志记录不规范

**位置**：`web/backend/services/websocket_manager.py`

**问题描述**：
- 使用 `print()` 而非 `logger`
- 无法统一管理日志级别
- 生产环境难以追踪问题

**代码证据**：
```python
# 第22行
print(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

# 第28行
print(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

# 第42行
print(f"发送消息失败: {e}")
```

**影响**：
- 日志无法写入文件
- 无法设置日志级别过滤
- 生产环境（Railway部署）难以调试

---

### 🟡 P1 级问题：导入失败静默跳过推送

**位置**：`web/backend/services/price/scraper.py` 第325-329行

**问题描述**：
- 导入 `ws_manager` 失败时，将其设为 `None`
- 后续所有推送被 `if ws_manager:` 静默跳过
- 无错误日志，难以诊断

**代码证据**：
```python
try:
    from services.websocket_manager import ws_manager
except ImportError as e:
    self.logger.error(f"[YantaiScraper.fetch] 导入ws_manager失败 | error={e}")
    ws_manager = None  # 设为None后，所有推送被跳过

# 后续代码
if ws_manager:  # 为None时跳过
    await ws_manager.notify_fetch_started()
```

**影响**：
- 推送功能静默失效
- 用户不知道推送已失败
- 难以排查问题

---

### 🟡 P1 级问题：异常处理不完善

**位置**：`web/backend/services/websocket_manager.py` 第40-43行

**问题描述**：
- 异常捕获后只打印，不记录详细信息
- 无法区分不同类型的异常

**代码证据**：
```python
try:
    await connection.send_text(message_json)
except Exception as e:
    print(f"发送消息失败: {e}")  # 没有异常类型，没有堆栈信息
    disconnected.append(connection)
```

**影响**：
- 无法追踪具体失败原因
- 难以区分是网络问题还是序列化问题

---

### 🟢 P2 级问题：潜在的竞态条件

**位置**：`web/backend/services/websocket_manager.py`

**问题描述**：
- `send_to_all()` 遍历列表时可能修改列表
- `disconnect()` 方法非线程安全

**影响**：
- 高并发情况下可能导致异常
- 连接列表状态不一致

---

## 修复计划

### 阶段1：修复 WebSocket 端点缺失（P0）

在 `main.py` 中添加 WebSocket 端点：

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃，接收心跳等
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"[websocket] 连接异常 | {e}", exc_info=True)
        ws_manager.disconnect(websocket)
```

### 阶段2：修复日志记录（P1）

在 `websocket_manager.py` 中：
1. 添加 `logger = logging.getLogger(__name__)`
2. 将所有 `print()` 替换为 `logger.info()`
3. 异常记录使用 `exc_info=True`

### 阶段3：增强错误处理（P1）

1. 导入失败时抛出警告而非静默跳过
2. 添加推送重试机制
3. 记录详细的异常信息

### 阶段4：连接状态监控（P2）

1. 添加心跳机制
2. 连接状态API
3. 推送失败告警

---

## 验证方案

修复后验证步骤：

1. **启动后端**：`python -m uvicorn main:app --host 0.0.0.0 --port 8000`
2. **检查日志**：确认 `WebSocket连接已建立` 日志出现
3. **前端测试**：
   - 打开 PriceMonitor 页面
   - 检查浏览器控制台是否有 `WebSocket已连接` 日志
4. **触发推送**：执行价格抓取
5. **验证推送**：确认收到 `fetch_started`、`fetch_success` 消息

---

## 关键文件清单

| 文件 | 问题 | 修复优先级 |
|------|------|-----------|
| `web/backend/main.py` | 缺少 WebSocket 端点 | P0 |
| `web/backend/services/websocket_manager.py` | print → logger | P1 |
| `web/backend/services/price/scraper.py` | 导入失败静默跳过 | P1 |

---

## 技术栈

- **后端**：FastAPI + WebSocket
- **前端**：原生 WebSocket API
- **部署**：Railway（后端）+ Vercel（前端）
