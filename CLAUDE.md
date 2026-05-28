# TaskPlatform 代码规范

## 项目概述
- **名称**: TaskPlatform - 工程调差计算系统
- **类型**: FastAPI 后端 + 桌面客户端
- **部署**: Railway 后端 + Vercel 前端

## 代码规范

### 1. 日志记录要求（强制）

**每次函数调用必须记录日志**，格式统一：

```python
import logging
logger = logging.getLogger(__name__)

# 函数入口
logger.info(f"[函数名] 开始执行 | 参数: xxx")

# 函数结束
logger.info(f"[函数名] 执行完成 | 结果: xxx")

# 异常捕获
logger.error(f"[函数名] 执行失败 | 错误: {e}", exc_info=True)
```

**日志级别使用规则**:
- `DEBUG`: 调试信息，仅开发时使用
- `INFO`: 正常业务流程
- `WARNING`: 潜在问题
- `ERROR`: 错误但程序可继续
- `CRITICAL`: 严重错误，程序无法继续

### 2. 输入验证要求（强制）

**所有API端点必须验证输入参数**：

```python
from pydantic import BaseModel, Field

class InputSchema(BaseModel):
    param: str = Field(..., min_length=1, max_length=100)

@app.post("/api/endpoint")
async def endpoint(data: InputSchema):
    logger.info(f"[endpoint] 接收请求 | param={data.param}")
    # 业务逻辑
```

**验证规则**:
- 必填字段：`Field(..., min_length=1)` 或 `Field(..., gt=0)`
- 字符串长度：使用 `min_length`/`max_length`
- 数值范围：使用 `ge`/`le`/`gt`/`lt`
- 枚举值：使用 `Literal` 或 `Enum`

### 3. 错误处理要求（强制）

```python
try:
    result = do_something()
    logger.info(f"[函数名] 操作成功")
    return result
except ValueError as e:
    logger.error(f"[函数名] 参数错误 | {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"[函数名] 未知错误 | {type(e).__name__}: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="内部错误")
```

**错误处理规则**:
- 不允许 `except Exception: pass`
- 不允许裸 `except:` 捕获所有异常
- 必须记录异常堆栈：`exc_info=True`
- 向上抛出时保留原始异常信息

### 4. 返回值类型要求

**函数必须使用类型注解**：

```python
from typing import Optional, List, Dict, Any

def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理数据并返回结果"""
    logger.debug(f"[process_data] 输入: {data}")
    # ...
    return result

async def get_data(id: int) -> Optional[Dict[str, Any]]:
    """获取数据，不存在返回None"""
    # ...
```

### 5. API 路由规范

**每个路由必须包含**:
1. `logger` 实例
2. 输入参数验证
3. 入口/出口日志
4. 异常处理
5. 适当的HTTP状态码

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    value: int = Field(..., gt=0)

@router.post("/", status_code=201)
async def create_item(data: CreateItemRequest):
    logger.info(f"[create_item] 创建项目 | name={data.name}, value={data.value}")
    try:
        result = await db.insert(data)
        logger.info(f"[create_item] 创建成功 | id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"[create_item] 创建失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建失败")
```

### 6. 数据库操作规范

**数据库操作必须记录**:
- 操作类型（查询/插入/更新/删除）
- 影响行数
- 错误信息

```python
async def update_record(id: int, data: Dict):
    logger.info(f"[update_record] 更新记录 | id={id}")
    result = await db.update(id, data)
    logger.info(f"[update_record] 更新完成 | affected={result.rowcount}")
    return result
```

### 7. WebSocket 推送规范

**推送消息必须记录**:
```python
logger.info(f"[ws_push] 推送消息 | type={msg_type}, recipient={user_id}")
ws_manager.send_to_user(user_id, {"type": msg_type, "data": data})
```

### 8. 代码审查清单

生成代码后自检：

- [ ] 是否有 `logger = logging.getLogger(__name__)`
- [ ] 函数是否有类型注解
- [ ] API端点是否有输入验证
- [ ] 是否记录了入口/出口日志
- [ ] 异常处理是否包含 `exc_info=True`
- [ ] 是否有裸 `except:` 或 `except Exception: pass`

### 9. 提交前检查

1. 运行语法检查：`python -m py_compile <file>`
2. 检查是否有明显错误
3. 确认日志覆盖关键路径
4. 确保没有遗留的调试代码（如 `print`、`import pdb`）

## 常见错误警示

### 不要这样写：

```python
# 错误1: 没有日志
def get_data(id):
    return db.query(id)  # 谁调用了？何时调用？结果是什么？

# 错误2: 裸异常捕获
try:
    do_something()
except:  # 捕获所有异常，包括 KeyboardInterrupt
    pass

# 错误3: 没有类型注解
def process(data):  # data是什么类型？返回什么？
    return data.get("result")

# 错误4: 缺少输入验证
@app.post("/api/create")
async def create(name: str):  # name可能为空、空字符串、过长
    db.insert({"name": name})

# 错误5: 异常后不记录
try:
    risky_operation()
except Exception as e:
    raise  # 错误原因完全丢失
```

### 应该这样写：

```python
# 正确1: 完整日志
logger = logging.getLogger(__name__)

def get_data(id: int) -> Optional[Dict]:
    logger.info(f"[get_data] 查询数据 | id={id}")
    result = db.query(id)
    logger.info(f"[get_data] 查询完成 | found={result is not None}")
    return result

# 正确2: 类型注解 + 验证
from pydantic import BaseModel, Field

class CreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    value: int = Field(..., gt=0)

@app.post("/api/create", status_code=201)
async def create(data: CreateRequest):
    logger.info(f"[create] 创建 | name={data.name}")
    try:
        result = await db.insert(data.dict())
        logger.info(f"[create] 成功 | id={result['id']}")
        return result
    except Exception as e:
        logger.error(f"[create] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建失败")
```

## 日志格式约定

```
[模块名] 操作描述 | 关键参数1=值1 | 关键参数2=值2
```

示例：
```
[price_fetch] 抓取价格 | source=mysteel | date=2026-05-28
[yantai_db] 查询完成 | found=5 | duration=0.23s
[adjustment] 计算调差 | project_id=123 | items=10
```

## 环境变量配置

### 必选环境变量（部署时设置）

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `SUPABASE_URL` | Supabase 数据库地址 | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase API Key | `eyJhbGciOiJIUzI...` |
| `AI_API_URL` | AI 服务地址 | `https://api.openai.com/v1` |
| `AI_API_KEY` | AI 服务密钥 | `sk-xxx` |

### 可选环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `TASKPLATFORM_MASTER_KEY` | 凭据加密主密钥 | `your-strong-password` |

### 配置优先级

1. **环境变量**（最高优先级）
2. **构造函数参数**
3. **配置文件**（最低优先级，如 `config/cloud.json`）