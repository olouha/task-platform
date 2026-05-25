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

router = APIRouter(prefix="/ai", tags=["AI对话"])
ai_service = AIService()
rag_service = RAGService()

logger = logging.getLogger(__name__)


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
    user_id: Optional[str] = Header(None)
):
    """
    普通 AI 对话（不带知识库检索）

    请求体:
    {
        "messages": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮您？"}
        ]
    }
    """
    try:
        # 构建消息列表
        messages = [msg.dict() for msg in request.messages]

        # 调用 AI 服务
        result = await ai_service.chat(
            messages=messages,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 2000
        )

        # 保存对话记录（如果已登录）
        if user_id:
            _save_message(user_id, messages, result)

        return result

    except Exception as e:
        logger.error(f"AI 对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/completions/stream")
async def chat_completions_stream(
    request: ChatRequest,
    user_id: Optional[str] = Header(None)
):
    """
    流式 AI 对话（SSE）

    请求体同 /chat/completions
    """
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
    user_id: Optional[str] = Header(None),
    enable_rag: bool = Query(True, description="是否启用知识库检索")
):
    """
    AI 对话（带 RAG 知识库检索增强）

    自动从知识库检索相关内容，注入到 system prompt
    """
    try:
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
            _save_message(user_id, request.messages, result, sources=sources)

        # 7. 在结果中加入 sources 信息
        if sources and "choices" in result:
            result["sources"] = sources

        return result

    except Exception as e:
        logger.error(f"RAG 对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/rag/stream")
async def chat_with_rag_stream(
    request: ChatRequest,
    user_id: Optional[str] = Header(None)
):
    """
    流式 RAG 对话
    """
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


# ========== 会话管理 API ==========

@router.get("/conversations")
async def list_conversations(
    user_id: str = Header(..., alias="x-user-id"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
):
    """
    获取用户的对话会话列表
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        conversations = supabase.get_ai_conversations(user_id, limit, offset)
        return {"data": conversations}
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations")
async def create_conversation(
    title: str = Query("新对话"),
    model: str = Query("gpt-4"),
    system_prompt: Optional[str] = None,
    user_id: str = Header(..., alias="x-user-id")
):
    """
    创建新对话会话
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        conversation = supabase.create_ai_conversation(
            user_id=user_id,
            title=title,
            model=model,
            system_prompt=system_prompt
        )
        return conversation
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Header(..., alias="x-user-id")
):
    """
    获取会话详情
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        conversation = supabase.get_ai_conversation(conversation_id, user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    user_id: str = Header(..., alias="x-user-id"),
    limit: int = Query(50, le=100)
):
    """
    获取会话的消息历史
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        messages = supabase.get_ai_messages(conversation_id, user_id, limit)
        return {"data": messages}
    except Exception as e:
        logger.error(f"获取消息历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Header(..., alias="x-user-id")
):
    """
    删除对话会话
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()
        success = supabase.delete_ai_conversation(conversation_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 辅助函数 ==========

def _save_message(
    user_id: str,
    messages: List[Dict],
    result: Dict,
    sources: List[Dict] = None
):
    """
    保存对话消息到数据库
    """
    try:
        from services.supabase_service import SupabaseService
        supabase = SupabaseService()

        # 从结果中提取 AI 回复
        ai_content = ""
        if "choices" in result and len(result["choices"]) > 0:
            ai_content = result["choices"][0].get("message", {}).get("content", "")

        # 保存用户最后一条消息和 AI 回复
        user_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_content = msg.get("content", "")
                break

        if user_content:
            supabase.save_ai_message(
                user_id=user_id,
                role="user",
                content=user_content
            )

        if ai_content:
            supabase.save_ai_message(
                user_id=user_id,
                role="assistant",
                content=ai_content,
                metadata={"sources": sources} if sources else None
            )

    except Exception as e:
        logger.error(f"保存消息失败: {e}")


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