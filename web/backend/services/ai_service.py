"""
AI 服务 - 调用内部 AI 接口（OpenAI 兼容）
"""

import os
import logging
from typing import List, Dict, Optional, AsyncGenerator

import httpx

from services.ai_self_review import get_self_review_service

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务封装 - 调用内部 OpenAI 兼容 API"""

    def __init__(self):
        self.base_url = os.environ.get("AI_API_URL", "https://api.internal.ai/v1")
        self.api_key = os.environ.get("AI_API_KEY", "")
        self.default_model = os.environ.get("AI_MODEL", "gpt-4")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-ada-002")
        self.embedding_dim = 1536

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict:
        """
        调用 AI 对话接口

        参数:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数 (0-1)
            max_tokens: 最大 token 数

        返回:
            AI 响应结果
        """
        if not self.base_url or not self.api_key:
            logger.warning("未配置 AI 服务，将返回模拟响应")
            return self._mock_response(messages)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.default_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    # 【统一自检】所有 AI 内容生成后自动自检
                    self_review = get_self_review_service()
                    self_review.self_review(
                        content=result.get("choices", [{}])[0].get("message", {}).get("content", ""),
                        content_type="chat",
                        metadata={"model": self.default_model}
                    )
                    return result
                else:
                    logger.error(f"AI 服务请求失败: {response.status_code} - {response.text}")
                    return self._mock_response(messages)

        except Exception as e:
            logger.error(f"调用 AI 服务异常: {e}")
            return self._mock_response(messages)

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 AI 对话接口 (SSE)

        参数:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数

        Yields:
            每个 token 的文本片段
        """
        if not self.base_url or not self.api_key:
            # 返回模拟流
            response_text = "抱歉，AI 服务暂未配置。请联系管理员配置 AI 服务地址。"
            for char in response_text:
                yield char
            return

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json={
                        "model": self.default_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": True
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str == "[DONE]":
                                    break
                                try:
                                    import json
                                    data = json.loads(data_str)
                                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                                except:
                                    pass

        except Exception as e:
            logger.error(f"流式调用 AI 服务异常: {e}")
            yield "调用 AI 服务失败，请稍后重试。"

    async def chat_stream_with_review(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 AI 对话接口（带自检）

        流式响应结束时对完整内容进行自检
        """
        full_content = []

        async for chunk in self.chat_stream(messages, temperature, max_tokens):
            full_content.append(chunk)
            yield chunk

        # 【统一自检】流式结束后对完整内容自检
        if full_content:
            complete_content = "".join(full_content)
            self_review = get_self_review_service()
            self_review.self_review(
                content=complete_content,
                content_type="chat_stream",
                metadata={"model": self.default_model}
            )

    async def get_embedding(self, text: str) -> List[float]:
        """
        获取文本向量（用于知识库检索）

        参数:
            text: 输入文本

        返回:
            向量列表
        """
        if not self.base_url or not self.api_key:
            logger.warning("未配置 AI 服务，无法生成向量")
            return [0.0] * self.embedding_dim

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json={
                        "input": text,
                        "model": self.embedding_model
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    logger.error(f"获取向量失败: {response.status_code}")
                    return [0.0] * self.embedding_dim

        except Exception as e:
            logger.error(f"获取向量异常: {e}")
            return [0.0] * self.embedding_dim

    def _mock_response(self, messages: List[Dict]) -> Dict:
        """
        返回模拟响应（当 AI 服务未配置时使用）
        """
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        mock_answer = f"【模拟响应】收到您的问题：{user_message}\n\n"

        # 根据问题类型返回不同的模拟回答
        if "调差" in user_message or "价格" in user_message:
            mock_answer += "根据系统知识库，调差是指根据合同约定，当材料价格波动超过一定幅度时，对合同价格进行调整的机制。\n\n常见调差方法：\n1. 简单比例法\n2. 造价信息调整法\n3. 钢筋节点法"
        elif "钢筋" in user_message:
            mock_answer += "烟台地区钢筋价格最近呈上涨趋势，建议关注市场动态。\n\n当前调差参考价：\n- HRB400: 约 4200 元/吨\n- HRB500: 约 4500 元/吨"
        else:
            mock_answer += "感谢您的提问！我是工程调差系统的 AI 助手，可以帮您：\n- 解答调差计算问题\n- 提供材料价格参考\n- 解释调差规则"

        return {
            "id": "mock-" + str(hash(user_message)),
            "object": "chat.completion",
            "created": 1234567890,
            "model": self.default_model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": mock_answer
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 50,
                "total_tokens": 60
            }
        }

    def format_rag_context(self, docs: List[Dict]) -> str:
        """
        将检索结果格式化为 AI 可读的上下文

        参数:
            docs: 检索到的文档列表

        返回:
            格式化的上下文字符串
        """
        if not docs:
            return ""

        context = "【参考知识库】\n\n"
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "未命名")
            content = doc.get("content_chunk", doc.get("content", ""))
            context += f"[{i}] {title}\n{content}\n\n"

        return context