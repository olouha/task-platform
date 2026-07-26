"""
AI 对话 API
支持普通对话、RAG 增强对话、会话管理
"""

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import logging

from services.ai_service import AIService
from services.rag_service import RAGService
from services.local_qa_service import LocalQAService
from services.ai_chat_db import AIChatDBService, init_db as init_ai_chat_db

router = APIRouter(prefix="/ai", tags=["AI对话"])
ai_service = AIService()
rag_service = RAGService()
local_qa = LocalQAService()  # 本地问答服务
ai_chat_db = AIChatDBService()  # 本地会话历史（取代已禁用的 Supabase）

logger = logging.getLogger(__name__)

# 启动时确保表存在
try:
    init_ai_chat_db()
    logger.info("[ai_chat] 本地会话数据库已就绪")
except Exception as _e:
    logger.error(f"[ai_chat] 初始化本地会话数据库失败 | {_e}", exc_info=True)


# ========== Pydantic 模型 ==========

class Message(BaseModel):
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000


class RAGRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3
    category: Optional[str] = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    last_message_at: str
    message_count: int = 0


# ========== 依赖 ==========

def get_user_id(x_user_id: Optional[str] = Header(None)) -> Optional[str]:
    """获取用户 ID"""
    return x_user_id


# ========== AI 对话 API ==========

@router.post("/chat/completions")
async def chat_completions(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    x_conversation_id: Optional[str] = Header(None, alias="x-conversation-id")
):
    """
    普通 AI 对话

    如果未配置外部AI服务，将使用本地知识库问答
    """
    try:
        # 检查是否配置了AI服务
        import os
        has_ai = bool(os.environ.get("AI_API_URL") and os.environ.get("AI_API_KEY"))

        if has_ai:
            # 使用外部AI服务
            messages = [msg.dict() for msg in request.messages]
            result = await ai_service.chat(
                messages=messages,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000
            )

            # 保存对话记录（如果已登录）
            if user_id:
                _save_message(user_id, messages, result, conversation_id=x_conversation_id)

            return result
        else:
            # 使用本地问答服务
            logger.info("[chat_completions] 使用本地问答服务")
            result = await local_qa.chat(
                messages=[msg.dict() for msg in request.messages],
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000
            )

            # 保存对话记录
            if user_id:
                _save_message(user_id, [msg.dict() for msg in request.messages], result, conversation_id=x_conversation_id)

            return result

    except Exception as e:
        logger.error(f"AI 对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/completions/stream")
async def chat_completions_stream(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    流式 AI 对话（SSE）

    如果未配置外部AI服务，将使用本地问答（非流式返回）
    """
    import os
    has_ai = bool(os.environ.get("AI_API_URL") and os.environ.get("AI_API_KEY"))

    if not has_ai:
        # 本地模式：一次性返回结果
        result = await local_qa.chat(
            messages=[msg.dict() for msg in request.messages],
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        async def generate_local():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_local(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-Id": user_id or ""
            }
        )

    # 外部AI模式：流式返回
    async def generate():
        try:
            messages = [msg.dict() for msg in request.messages]

            async for chunk in ai_service.chat_stream(
                messages=messages,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000
            ):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error = {"error": {"message": str(e), "type": "api_error"}}
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-Id": user_id or ""
        }
    )


@router.post("/chat/rag")
async def chat_with_rag(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    enable_rag: bool = Query(True, description="是否启用知识库检索"),
    x_conversation_id: Optional[str] = Header(None, alias="x-conversation-id")
):
    """
    AI 对话（带 RAG 知识库检索增强）

    如果未配置外部AI服务，将使用本地知识库问答
    """
    try:
        import os
        has_ai = bool(os.environ.get("AI_API_URL") and os.environ.get("AI_API_KEY"))

        if not has_ai:
            # 本地模式：使用本地问答服务
            logger.info("[chat_with_rag] 使用本地问答服务")
            result = await local_qa.chat(
                messages=[msg.dict() for msg in request.messages],
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000
            )

            # 保存对话记录
            if user_id:
                _save_message(user_id, request.messages, result, conversation_id=x_conversation_id)

            return result

        # 外部AI模式：使用 RAG 检索增强
        # 1. 获取用户问题
        user_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_query = msg.content
                break

        # 2. 搜索知识库（如果启用）
        rag_context = ""
        sources = []
        if enable_rag and user_query:
            docs = rag_service.search(
                query=user_query,
                top_k=3,
                min_similarity=0.7
            )
            if docs:
                rag_context = rag_service.format_context(docs)
                sources = [{"title": d.get("title"), "id": d.get("id")} for d in docs]

        # 3. 构建带上下文的系统消息
        system_content = "你是一个专业的工程调差计算助手。请根据用户提供的问题，结合参考知识库给出准确的回答。"

        if rag_context:
            system_content = f"""{system_content}

{rag_context}

请在回答中适当引用上述参考内容。"""

        # 4. 在消息开头插入 system 消息
        messages = [{"role": "system", "content": system_content}]
        messages.extend([msg.dict() for msg in request.messages])

        # 5. 调用 AI 服务
        result = await ai_service.chat(
            messages=messages,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )

        # 6. 保存对话记录
        if user_id:
            _save_message(user_id, request.messages, result, sources=sources, conversation_id=x_conversation_id)

        # 7. 在结果中加入 sources 信息
        if sources and "choices" in result:
            result["sources"] = sources

        return result

    except Exception as e:
        logger.error(f"RAG 对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/rag/stream")
async def chat_with_rag_stream(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    流式 RAG 对话

    如果未配置外部AI服务，将使用本地问答服务（非流式返回）
    """
    import os
    has_ai = bool(os.environ.get("AI_API_URL") and os.environ.get("AI_API_KEY"))

    if not has_ai:
        # 本地模式：一次性返回结果
        result = await local_qa.chat(
            messages=[msg.dict() for msg in request.messages],
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

        async def generate_local():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_local(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-Id": user_id or ""
            }
        )

    # 外部AI模式：流式返回
    user_query = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_query = msg.content
            break

    # 搜索知识库
    docs = rag_service.search(query=user_query, top_k=3) if user_query else []
    rag_context = rag_service.format_context(docs) if docs else ""

    system_content = "你是一个专业的工程调差计算助手。"
    if rag_context:
        system_content += f"\n\n{rag_context}\n\n请在回答中适当引用上述参考内容。"

    messages = [{"role": "system", "content": system_content}]
    messages.extend([msg.dict() for msg in request.messages])

    async def generate():
        try:
            async for chunk in ai_service.chat_stream(messages=messages):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"

            # 结束时返回 sources
            if docs:
                sources = [{"title": d.get("title"), "id": d.get("id")} for d in docs]
                yield f"data: {json.dumps({'sources': sources})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# ========== 会话管理 API（本地 SQLite 持久化）==========

@router.get("/conversations")
async def list_conversations(
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """
    获取用户的对话会话列表

    user_id 为空时使用 'default'，避免匿名访问 422
    """
    uid = user_id or "default"
    logger.info(f"[list_conversations] user_id={uid} | limit={limit} | offset={offset}")
    try:
        conversations = ai_chat_db.list_conversations(uid, limit, offset)
        logger.info(f"[list_conversations] 返回 | count={len(conversations)}")
        return {"data": conversations}
    except Exception as e:
        logger.error(f"[list_conversations] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations")
async def create_conversation(
    title: str = Query("新对话"),
    model: str = Query("gpt-4"),
    system_prompt: Optional[str] = None,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    x_conversation_id: Optional[str] = Header(None, alias="x-conversation-id")
):
    """
    创建新对话会话

    支持通过 x-conversation-id 头传入自定义 ID（兼容 chatStore 临时 ID 流）
    """
    uid = user_id or "default"
    logger.info(f"[create_conversation] user_id={uid} | title={title} | model={model}")
    try:
        # 如果前端传入了 temp- ID，不入库，直接回包一个新 ID
        if x_conversation_id and x_conversation_id.startswith("temp-"):
            import uuid as _uuid
            x_conversation_id = str(_uuid.uuid4())

        conversation = ai_chat_db.create_conversation(
            user_id=uid,
            title=title,
            model=model,
            system_prompt=system_prompt,
            conversation_id=x_conversation_id,
        )
        logger.info(f"[create_conversation] 创建成功 | id={conversation.get('id')}")
        return conversation
    except Exception as e:
        logger.error(f"[create_conversation] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    获取会话详情
    """
    uid = user_id or "default"
    logger.info(f"[get_conversation] id={conversation_id} | user_id={uid}")
    try:
        conversation = ai_chat_db.get_conversation(conversation_id, uid)
        if not conversation:
            logger.info(f"[get_conversation] 未找到 | id={conversation_id}")
            raise HTTPException(status_code=404, detail="会话不存在")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[get_conversation] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    limit: int = Query(50, le=100)
):
    """
    获取会话的消息历史
    """
    uid = user_id or "default"
    logger.info(f"[get_conversation_messages] id={conversation_id} | user_id={uid} | limit={limit}")
    try:
        messages = ai_chat_db.list_messages(conversation_id, uid, limit)
        logger.info(f"[get_conversation_messages] 返回 | count={len(messages)}")
        return {"data": messages}
    except Exception as e:
        logger.error(f"[get_conversation_messages] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    删除对话会话
    """
    uid = user_id or "default"
    logger.info(f"[delete_conversation] id={conversation_id} | user_id={uid}")
    try:
        success = ai_chat_db.delete_conversation(conversation_id, uid)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[delete_conversation] 失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== 辅助函数 ==========

def _save_message(
    user_id: Optional[str],
    messages: List[Dict],
    result: Dict,
    sources: List[Dict] = None,
    conversation_id: Optional[str] = None,
):
    """
    保存对话消息到本地 SQLite

    Args:
        user_id: 用户 ID（默认 'default'）
        conversation_id: 来自 x-conversation-id 头；为空则跳过保存
        sources: RAG 来源（写入 assistant 消息的 metadata）
    """
    # 无 conversation_id 或为临时 ID 时不持久化（前端会兜底）
    if not conversation_id or conversation_id.startswith("temp-"):
        logger.debug("[_save_message] 跳过：conversation_id 缺失或为临时 ID")
        return

    try:
        uid = user_id or "default"

        # 确保会话存在（首次发消息时尚未 create_conversation）
        ai_chat_db.get_or_create_conversation(
            conversation_id=conversation_id,
            user_id=uid,
            title=messages[-1].get("content", "新对话")[:30] if messages else "新对话",
            model="gpt-4",
        )

        # 从结果中提取 AI 回复
        ai_content = ""
        if "choices" in result and len(result["choices"]) > 0:
            ai_content = result["choices"][0].get("message", {}).get("content", "")

        # 保存用户最后一条消息
        user_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        if user_content:
            ai_chat_db.save_message(
                conversation_id=conversation_id,
                role="user",
                content=user_content,
            )

        if ai_content:
            ai_chat_db.save_message(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_content,
                metadata={"sources": sources} if sources else None,
            )

        logger.info(f"[_save_message] 保存完成 | conv_id={conversation_id}")

    except Exception as e:
        logger.error(f"[_save_message] 失败 | {e}", exc_info=True)


# ========== 知识库管理 API ==========

@router.post("/rag/search")
async def rag_search(
    query: str = Query(..., description="查询文本"),
    top_k: int = Query(3, ge=1, le=10, description="返回结果数量"),
    category: Optional[str] = Query(None, description="分类过滤")
):
    """
    搜索知识库（独立检索接口）
    """
    try:
        results = rag_service.search(
            query=query,
            top_k=top_k,
            min_similarity=0.7,
            category=category
        )
        return {"data": results, "query": query}
    except Exception as e:
        logger.error(f"RAG 搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/documents")
async def create_document(
    title: str = Query(..., description="文档标题"),
    content: str = Query(..., description="文档内容"),
    category: Optional[str] = Query(None, description="分类"),
    tags: Optional[str] = Query(None, description="标签，逗号分隔"),
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    创建知识库文档（自动向量化）
    """
    try:
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        result = rag_service.create_document(
            title=title,
            content=content,
            category=category,
            tags=tag_list,
            created_by=user_id
        )

        if result:
            return result
        else:
            raise HTTPException(status_code=500, detail="创建文档失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/documents")
async def list_documents(
    category: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """
    获取知识库文档列表
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        docs = supabase.list_kb_documents(category, limit, offset)
        return {"data": docs}
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rag/documents/{document_id}")
async def delete_document(document_id: str):
    """
    删除知识库文档
    """
    try:
        success = rag_service.delete_document(document_id)
        if success:
            return {"success": True}
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 工具调用 API ==========

from services.tool_executor import ToolExecutor
from services.ai_tools import get_tools_definitions

tool_executor = ToolExecutor()


@router.post("/chat/tools")
async def chat_with_tools(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id"),
    x_conversation_id: Optional[str] = Header(None, alias="x-conversation-id")
):
    """
    支持工具调用的AI对话

    如果未配置外部AI服务，将使用本地问答服务（支持工具调用）

    可用工具：
    - query_price_by_date: 按日期查询价格
    - query_price_range: 查询日期范围价格
    - query_price_trend: 查询价格趋势
    - search_materials: 搜索材料
    - get_latest_prices: 获取最新价格
    - compare_prices: 价格对比
    """
    try:
        logger.info(f"[chat_with_tools] 收到请求 | messages={len(request.messages)}")

        import os
        has_ai = bool(os.environ.get("AI_API_URL") and os.environ.get("AI_API_KEY"))

        if not has_ai:
            # 本地模式：使用本地问答服务
            logger.info("[chat_with_tools] 使用本地问答服务")
            result = await local_qa.chat(
                messages=[msg.dict() for msg in request.messages],
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000
            )

            # 保存对话记录
            if user_id:
                _save_message(user_id, request.messages, result, conversation_id=x_conversation_id)

            logger.info(f"[chat_with_tools] 返回结果")
            return result

        # 外部AI模式：使用工具调用
        from services.tool_executor import ToolExecutor
        from services.ai_tools import get_tools_definitions

        tool_executor = ToolExecutor()
        tools = get_tools_definitions()

        result = await ai_service.chat_with_tools(
            messages=[msg.dict() for msg in request.messages],
            tools=tools,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000,
            tool_executor=tool_executor
        )

        # 保存对话记录
        if user_id:
            _save_message(user_id, request.messages, result, conversation_id=x_conversation_id)

        logger.info(f"[chat_with_tools] 返回结果")
        return result

    except Exception as e:
        logger.error(f"[chat_with_tools] 请求失败 | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/tools/stream")
async def chat_with_tools_stream(
    request: ChatRequest,
    user_id: Optional[str] = Header(None, alias="x-user-id")
):
    """
    流式工具调用对话

    AI助手会实时返回思考过程和工具调用结果
    """
    logger.info(f"[chat_with_tools_stream] 收到请求 | messages={len(request.messages)}")

    # 获取工具定义
    tools = get_tools_definitions()

    async def generate():
        full_content = []
        try:
            async for chunk in ai_service.chat_with_tools_stream(
                messages=[msg.dict() for msg in request.messages],
                tools=tools,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 2000,
                tool_executor=tool_executor
            ):
                full_content.append(chunk)
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"[chat_with_tools_stream] 生成失败 | {e}", exc_info=True)
            error = {"error": {"message": str(e), "type": "api_error"}}
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-Id": user_id or ""
        }
    )


@router.get("/tools")
async def list_tools():
    """
    获取可用的工具列表

    返回所有AI助手可以调用的工具定义
    """
    tools = get_tools_definitions()
    return {
        "success": True,
        "count": len(tools),
        "tools": [
            {
                "name": tool.get("function", {}).get("name"),
                "description": tool.get("function", {}).get("description"),
                "parameters": tool.get("function", {}).get("parameters", {}).get("properties", {})
            }
            for tool in tools
        ]
    }