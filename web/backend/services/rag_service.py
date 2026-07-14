"""
RAG 检索服务 - 知识库向量搜索
"""

import os
import logging
from typing import List, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 服务 - 知识库检索"""

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        # 由 config/cloud.json 的 mode 字段控制是否启用：
        #   mode="supabase" → 启用知识库向量检索
        #   mode="local"(或其他) → 禁用，search 直接返回 []，由调用方走规则问答兜底
        if not supabase_url or not supabase_key:
            # services/ 目录上溯三级到项目根，读 config/cloud.json
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'cloud.json')
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if config.get('mode') == 'supabase':
                        supabase_url = config.get('supabase_url')
                        supabase_key = config.get('supabase_key')

        self.url = supabase_url.rstrip('/') if supabase_url else None
        self.api_key = supabase_key
        self.headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.7,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        搜索知识库（向量检索 + 关键词过滤）

        参数:
            query: 查询文本
            top_k: 返回结果数量
            min_similarity: 最低相似度阈值
            category: 分类过滤

        返回:
            检索结果列表
        """
        if not self.url:
            # Supabase 未启用（本地模式），跳过向量检索，由调用方走规则问答兜底
            logger.debug("RAG: Supabase 未启用，跳过知识库检索")
            return []

        try:
            # 1. 获取查询向量
            from services.ai_service import AIService
            ai_service = AIService()
            import asyncio

            # 同步获取向量
            try:
                loop = asyncio.get_event_loop()
            except:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            query_embedding = loop.run_until_complete(ai_service.get_embedding(query))

            # 2. pgvector 相似度搜索
            # 使用 Supabase RPC 调用 match_documents 函数
            response = requests.post(
                f"{self.url}/rest/v1/rpc/match_kb_documents",
                headers=self.headers,
                json={
                    "query_embedding": query_embedding,
                    "match_threshold": min_similarity,
                    "match_count": top_k,
                    "filter_category": category
                }
            )

            if response.status_code == 200:
                results = response.json()
                return self._format_results(results)
            else:
                logger.error(f"向量检索失败: {response.status_code} - {response.text}")
                return self._fallback_search(query, top_k)

        except Exception as e:
            logger.error(f"RAG 检索异常: {e}")
            return self._fallback_search(query, top_k)

    def _format_results(self, results: List[Dict]) -> List[Dict]:
        """
        格式化检索结果

        参数:
            results: 原始结果

        返回:
            格式化后的结果
        """
        formatted = []
        for r in results:
            formatted.append({
                "id": r.get("id"),
                "document_id": r.get("document_id"),
                "title": r.get("title", "未命名"),
                "content_chunk": r.get("content_chunk", r.get("content", "")),
                "similarity": r.get("similarity", r.get("distance", 0)),
                "category": r.get("category"),
                "source_url": r.get("source_url"),
                "metadata": r.get("metadata", {})
            })
        return formatted

    def _fallback_search(self, query: str, top_k: int) -> List[Dict]:
        """
        回退搜索：使用全文搜索代替向量搜索

        参数:
            query: 查询文本
            top_k: 返回结果数量

        返回:
            检索结果
        """
        if not self.url:
            return []

        try:
            # 简单的关键词搜索
            keywords = query.split()[:5]  # 取前5个词
            search_query = " or ".join([f"content.ilik.%{kw}%" for kw in keywords])

            response = requests.get(
                f"{self.url}/rest/v1/kb_documents",
                headers=self.headers,
                params={
                    "select": "id,title,content,category,source_url",
                    "or": search_query,
                    "limit": top_k
                }
            )

            if response.status_code == 200:
                results = response.json()
                return [{
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "content_chunk": r.get("content", "")[:500],  # 截取前500字符
                    "similarity": 0.8,
                    "category": r.get("category"),
                    "source_url": r.get("source_url")
                } for r in results]
            else:
                return []

        except Exception as e:
            logger.error(f"回退搜索失败: {e}")
            return []

    def create_document(
        self,
        title: str,
        content: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Optional[Dict]:
        """
        创建知识库文档（自动分词和向量化）

        参数:
            title: 文档标题
            content: 文档内容
            category: 分类
            tags: 标签
            source_url: 来源 URL
            created_by: 创建者 ID

        返回:
            创建的文档
        """
        if not self.url:
            return None

        import uuid

        try:
            # 1. 保存文档
            doc_id = str(uuid.uuid4())
            doc_data = {
                "id": doc_id,
                "title": title,
                "content": content,
                "category": category,
                "tags": tags or [],
                "source_url": source_url,
                "created_by": created_by
            }

            response = requests.post(
                f"{self.url}/rest/v1/kb_documents",
                headers=self.headers,
                json=doc_data
            )

            if response.status_code not in [200, 201]:
                logger.error(f"保存文档失败: {response.text}")
                return None

            # 2. 分块和向量化
            self._index_document(doc_id, content, {"title": title, "category": category})

            return {"id": doc_id, "title": title, "status": "indexed"}

        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            return None

    def _index_document(self, document_id: str, content: str, metadata: Dict):
        """
        对文档进行分块和向量化

        参数:
            document_id: 文档 ID
            content: 文档内容
            metadata: 元数据
        """
        # 简单的分块策略：按段落或固定长度
        chunk_size = 500  # 每块约 500 字符
        chunks = []

        # 按段落分割
        paragraphs = content.split('\n\n')
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # 如果没有段落，按固定长度分割
        if not chunks:
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size].strip()
                if chunk:
                    chunks.append(chunk)

        # 生成向量并保存
        from services.ai_service import AIService
        import asyncio

        ai_service = AIService()

        try:
            loop = asyncio.get_event_loop()
        except:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        for i, chunk in enumerate(chunks):
            try:
                embedding = loop.run_until_complete(ai_service.get_embedding(chunk))

                # 保存到 kb_embeddings 表
                import uuid
                embedding_id = str(uuid.uuid4())

                response = requests.post(
                    f"{self.url}/rest/v1/kb_embeddings",
                    headers=self.headers,
                    json={
                        "id": embedding_id,
                        "document_id": document_id,
                        "content_chunk": chunk,
                        "embedding": embedding,
                        "chunk_index": i
                    }
                )

                if response.status_code not in [200, 201]:
                    logger.warning(f"保存向量失败: {response.status_code}")

            except Exception as e:
                logger.error(f"生成向量失败: {e}")

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档及其向量

        参数:
            document_id: 文档 ID

        返回:
            是否成功
        """
        if not self.url:
            return False

        try:
            # 删除向量
            requests.delete(
                f"{self.url}/rest/v1/kb_embeddings?document_id=eq.{document_id}",
                headers=self.headers
            )

            # 删除文档
            response = requests.delete(
                f"{self.url}/rest/v1/kb_documents?id=eq.{document_id}",
                headers=self.headers
            )

            return response.status_code in [200, 204, 404]

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def format_context(self, docs: List[Dict]) -> str:
        """
        将检索结果格式化为 AI 可读的上下文

        参数:
            docs: 检索结果

        返回:
            格式化后的上下文
        """
        if not docs:
            return ""

        context = "【参考知识库】\n\n"
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", "未命名")
            content = doc.get("content_chunk", doc.get("content", ""))
            category = doc.get("category", "")

            context += f"[{i}] {title}"
            if category:
                context += f" (分类: {category})"
            context += f"\n{content}\n\n"

        return context