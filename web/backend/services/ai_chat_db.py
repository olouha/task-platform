"""
AI 对话会话历史本地持久化服务

由于 Supabase 已被禁用，会话历史改为本地 SQLite 存储。
遵循 yantai_db_service.py 的连接/初始化模式：
- 绝对路径 DB_FILE
- row_factory = sqlite3.Row
- 模块级 init_db() 自动建表
"""

import sqlite3
import logging
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# 数据库文件路径 - 与其他本地 DB 同目录
DB_FILE = Path(__file__).parent.parent.parent / 'data' / 'ai_chat.db'


def get_db_connection() -> sqlite3.Connection:
    """
    获取数据库连接

    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    logger.debug(f"[ai_chat_db] 连接数据库 | db={DB_FILE}")
    # 确保父目录存在
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    初始化 AI 对话数据库表

    Creates:
        conversations 表 - 会话元数据（id/user_id/title/model/last_message_at/...）
        messages 表 - 消息明细（id/conversation_id/role/content/created_at/metadata）
        索引 - user_id, conversation_id 索引
    """
    logger.info("[ai_chat_db.init] 开始初始化数据库")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '新对话',
                model TEXT NOT NULL DEFAULT 'gpt-4',
                system_prompt TEXT,
                last_message_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_last_msg ON conversations(last_message_at)')

        conn.commit()
        logger.info("[ai_chat_db.init] 数据库初始化完成")
    except Exception as e:
        logger.error(f"[ai_chat_db.init] 初始化失败 | error={e}", exc_info=True)
        conn.rollback()
        raise
    finally:
        conn.close()


# 模块加载时自动初始化（与其他 service 保持一致）
try:
    init_db()
except Exception as _init_err:
    logger.error(f"[ai_chat_db] 启动初始化失败 | {_init_err}", exc_info=True)


class AIChatDBService:
    """
    AI 对话本地持久化服务

    提供会话与消息的 CRUD，对外暴露与原 Supabase 兼容的字段名。
    """

    def __init__(self, db_file: Optional[Path] = None):
        self.db_file = db_file or DB_FILE
        logger.info(f"[AIChatDBService] 初始化 | db={self.db_file}")

    # ---------- 会话 ----------

    def list_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户的会话列表（按最后活跃时间倒序）

        Returns:
            List[Dict]: 每个会话含 id, user_id, title, model, last_message_at, created_at, message_count
        """
        logger.info(f"[list_conversations] user_id={user_id} | limit={limit} | offset={offset}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT c.id, c.user_id, c.title, c.model,
                       c.last_message_at, c.created_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
                FROM conversations c
                WHERE c.user_id = ?
                ORDER BY c.last_message_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            rows = cursor.fetchall()
            items = [dict(r) for r in rows]
            logger.info(f"[list_conversations] 查询完成 | count={len(items)}")
            return items
        except Exception as e:
            logger.error(f"[list_conversations] 查询失败 | error={e}", exc_info=True)
            raise
        finally:
            conn.close()

    def create_conversation(
        self,
        user_id: str,
        title: str = "新对话",
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        创建新会话

        Args:
            conversation_id: 可选，前端传入的 ID（兼容 x-conversation-id 头）；为空则生成 UUID

        Returns:
            Dict: 会话对象
        """
        conv_id = conversation_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat(timespec='seconds')
        logger.info(f"[create_conversation] user_id={user_id} | id={conv_id} | title={title}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO conversations (id, user_id, title, model, system_prompt, last_message_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (conv_id, user_id, title, model, system_prompt, now, now))
            conn.commit()
            logger.info(f"[create_conversation] 创建成功 | id={conv_id}")
            return self.get_conversation(conv_id, user_id) or {
                "id": conv_id, "user_id": user_id, "title": title,
                "model": model, "system_prompt": system_prompt,
                "last_message_at": now, "created_at": now,
                "message_count": 0
            }
        except Exception as e:
            logger.error(f"[create_conversation] 失败 | error={e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取单个会话详情"""
        logger.info(f"[get_conversation] id={conversation_id} | user_id={user_id}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT c.id, c.user_id, c.title, c.model, c.system_prompt,
                       c.last_message_at, c.created_at,
                       (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
                FROM conversations c
                WHERE c.id = ? AND c.user_id = ?
            ''', (conversation_id, user_id))
            row = cursor.fetchone()
            if row is None:
                logger.info(f"[get_conversation] 未找到 | id={conversation_id}")
                return None
            return dict(row)
        except Exception as e:
            logger.error(f"[get_conversation] 失败 | error={e}", exc_info=True)
            raise
        finally:
            conn.close()

    def get_or_create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str = "新对话",
        model: str = "gpt-4"
    ) -> Dict[str, Any]:
        """获取会话，不存在则创建（用于 _save_message 自动归档）"""
        existing = self.get_conversation(conversation_id, user_id)
        if existing:
            return existing
        return self.create_conversation(
            user_id=user_id, title=title, model=model,
            conversation_id=conversation_id
        )

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        删除会话（同时级联删除其消息）

        Returns:
            bool: 是否成功删除
        """
        logger.info(f"[delete_conversation] id={conversation_id} | user_id={user_id}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # 先删消息（即使没有 ON DELETE CASCADE 也能工作）
            cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
            msg_deleted = cursor.rowcount

            cursor.execute('DELETE FROM conversations WHERE id = ? AND user_id = ?',
                           (conversation_id, user_id))
            conv_deleted = cursor.rowcount

            conn.commit()
            logger.info(f"[delete_conversation] 完成 | conv_deleted={conv_deleted} | msg_deleted={msg_deleted}")
            return conv_deleted > 0
        except Exception as e:
            logger.error(f"[delete_conversation] 失败 | error={e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()

    def touch_conversation(self, conversation_id: str) -> None:
        """更新会话的 last_message_at"""
        now = datetime.utcnow().isoformat(timespec='seconds')
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE conversations SET last_message_at = ? WHERE id = ?',
                (now, conversation_id)
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"[touch_conversation] 更新失败 | id={conversation_id} | error={e}")
        finally:
            conn.close()

    # ---------- 消息 ----------

    def list_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取会话的消息历史

        Returns:
            List[Dict]: 消息按 created_at 升序，每条含 id, conversation_id, role, content, created_at, metadata
        """
        logger.info(f"[list_messages] conv_id={conversation_id} | user_id={user_id} | limit={limit}")

        # 先校验会话归属
        conv = self.get_conversation(conversation_id, user_id)
        if conv is None:
            logger.warning(f"[list_messages] 会话不存在或无权访问 | conv_id={conversation_id}")
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT id, conversation_id, role, content, metadata, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id ASC
                LIMIT ?
            ''', (conversation_id, limit))
            rows = cursor.fetchall()
            items = []
            for r in rows:
                item = dict(r)
                # metadata 是 JSON 字符串，反序列化
                if item.get("metadata"):
                    try:
                        item["metadata"] = json.loads(item["metadata"])
                    except Exception:
                        pass
                items.append(item)
            logger.info(f"[list_messages] 查询完成 | count={len(items)}")
            return items
        except Exception as e:
            logger.error(f"[list_messages] 失败 | error={e}", exc_info=True)
            raise
        finally:
            conn.close()

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        保存一条消息，并刷新会话的 last_message_at

        Returns:
            int: 新插入的消息 id
        """
        logger.info(f"[save_message] conv_id={conversation_id} | role={role} | len={len(content)}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            cursor.execute('''
                INSERT INTO messages (conversation_id, role, content, metadata)
                VALUES (?, ?, ?, ?)
            ''', (conversation_id, role, content, meta_json))
            msg_id = cursor.lastrowid

            now = datetime.utcnow().isoformat(timespec='seconds')
            cursor.execute(
                'UPDATE conversations SET last_message_at = ? WHERE id = ?',
                (now, conversation_id)
            )
            conn.commit()
            logger.info(f"[save_message] 保存成功 | msg_id={msg_id}")
            return msg_id
        except Exception as e:
            logger.error(f"[save_message] 失败 | error={e}", exc_info=True)
            conn.rollback()
            raise
        finally:
            conn.close()


# 模块级单例
_service: Optional[AIChatDBService] = None


def get_service() -> AIChatDBService:
    """获取服务单例"""
    global _service
    if _service is None:
        _service = AIChatDBService()
    return _service