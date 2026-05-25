-- ============================================
-- AI 对话系统数据库 Schema
-- ============================================

-- AI 对话会话表
CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT DEFAULT '新对话',
    model TEXT DEFAULT 'gpt-4',
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT true,
    last_message_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- AI 消息表
CREATE TABLE IF NOT EXISTS ai_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES ai_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens INT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 知识库文档表
CREATE TABLE IF NOT EXISTS kb_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_url TEXT,
    category TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 知识库向量表（pgvector）
CREATE TABLE IF NOT EXISTS kb_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    content_chunk TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ========== 索引 ==========

CREATE INDEX IF NOT EXISTS idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_active ON ai_conversations(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_ai_conversations_last_message ON ai_conversations(user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation ON ai_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ai_messages_created ON ai_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_kb_documents_category ON kb_documents(category);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_document ON kb_embeddings(document_id);

-- 向量索引（使用 IVFFlat 加速）
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_vector ON kb_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========== RLS (行级安全策略) ==========

ALTER TABLE ai_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE kb_embeddings ENABLE ROW LEVEL SECURITY;

-- AI 对话：用户只能访问自己的对话
CREATE POLICY "ai_conversations_select" ON ai_conversations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "ai_conversations_insert" ON ai_conversations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "ai_conversations_update" ON ai_conversations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "ai_conversations_delete" ON ai_conversations
    FOR DELETE USING (auth.uid() = user_id);

-- AI 消息：通过 conversation 的 user_id 验证
CREATE POLICY "ai_messages_select" ON ai_messages
    FOR SELECT USING (
        conversation_id IN (SELECT id FROM ai_conversations WHERE user_id = auth.uid())
    );

CREATE POLICY "ai_messages_insert" ON ai_messages
    FOR INSERT WITH CHECK (
        conversation_id IN (SELECT id FROM ai_conversations WHERE user_id = auth.uid())
    );

CREATE POLICY "ai_messages_delete" ON ai_messages
    FOR DELETE USING (
        conversation_id IN (SELECT id FROM ai_conversations WHERE user_id = auth.uid())
    );

-- 知识库：所有人可读，管理员可写
CREATE POLICY "kb_documents_select" ON kb_documents
    FOR SELECT USING (true);

CREATE POLICY "kb_documents_insert" ON kb_documents
    FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "kb_documents_update" ON kb_documents
    FOR UPDATE USING (
        created_by = auth.uid() OR
        EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND (raw_user_meta_data->>'role') = 'admin')
    );

CREATE POLICY "kb_documents_delete" ON kb_documents
    FOR DELETE USING (
        created_by = auth.uid() OR
        EXISTS (SELECT 1 FROM auth.users WHERE id = auth.uid() AND (raw_user_meta_data->>'role') = 'admin')
    );

-- 知识库向量：可公开检索
CREATE POLICY "kb_embeddings_select" ON kb_embeddings
    FOR SELECT USING (true);

CREATE POLICY "kb_embeddings_insert" ON kb_embeddings
    FOR INSERT WITH CHECK (
        document_id IN (SELECT id FROM kb_documents WHERE created_by = auth.uid())
    );

CREATE POLICY "kb_embeddings_delete" ON kb_embeddings
    FOR DELETE USING (
        document_id IN (SELECT id FROM kb_documents WHERE created_by = auth.uid())
    );

-- ========== 向量搜索函数 ==========

-- 创建向量匹配函数（用于 RPC 调用）
CREATE OR REPLACE FUNCTION match_kb_documents(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    title TEXT,
    content_chunk TEXT,
    category TEXT,
    source_url TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.document_id,
        d.title,
        e.content_chunk,
        d.category,
        d.source_url,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM kb_embeddings e
    JOIN kb_documents d ON d.id = e.document_id
    WHERE (1 - (e.embedding <=> query_embedding)) >= match_threshold
      AND (filter_category IS NULL OR d.category = filter_category)
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 简单的全文搜索函数（回退方案）
CREATE OR REPLACE FUNCTION search_kb_documents_simple(
    search_query TEXT,
    search_limit INT DEFAULT 10,
    filter_category TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    content TEXT,
    category TEXT,
    source_url TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.title,
        d.content,
        d.category,
        d.source_url
    FROM kb_documents d
    WHERE d.content ILIKE '%' || search_query || '%'
      AND (filter_category IS NULL OR d.category = filter_category)
    LIMIT search_limit;
END;
$$;