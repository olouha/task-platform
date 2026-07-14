/**
 * AI 对话状态管理
 * 使用 Zustand 管理对话状态
 */

import { create } from 'zustand'

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
  sources?: Array<{ id: string; title: string }>
}

interface ChatState {
  // 状态
  messages: Message[]
  userId: string
  conversationId: string | null
  conversations: Array<{
    id: string
    title: string
    last_message_at: string
  }>
  isOpen: boolean
  isLoading: boolean
  error: string | null

  // 操作
  openChat: () => void
  closeChat: () => void
  sendMessage: (content: string) => Promise<void>
  loadConversations: () => Promise<void>
  loadMessages: (conversationId: string) => Promise<void>
  createConversation: (title?: string) => Promise<string | null>
  deleteConversation: (conversationId: string) => Promise<void>
  clearMessages: () => void
  setError: (error: string | null) => void
}

// API 基础路径（代理模式下为空字符串，避免与拼接的 /api/... 路径重复）
const getApiBase = () => {
  const base = import.meta.env.VITE_API_URL || ''
  return base.replace(/\/api\/?$/, '')
}

// 匿名用户 ID（localStorage 持久化）
const getOrCreateUserId = (): string => {
  const KEY = 'task-platform:user-id'
  try {
    const stored = localStorage.getItem(KEY)
    if (stored) return stored
    const id = crypto.randomUUID()
    localStorage.setItem(KEY, id)
    return id
  } catch {
    // SSR 或 localStorage 不可用时用临时 ID
    return 'temp-' + Date.now()
  }
}

export const useChatStore = create<ChatState>((set, get) => ({
  // 初始状态
  messages: [],
  userId: getOrCreateUserId(),
  conversationId: null,
  conversations: [],
  isOpen: false,
  isLoading: false,
  error: null,

  // 打开对话窗口
  openChat: () => {
    set({ isOpen: true })
    // 加载会话列表
    get().loadConversations()
  },

  // 关闭对话窗口
  closeChat: () => {
    set({ isOpen: false })
  },

  // 发送消息（P2-1: 改调 /chat/tools，P2-3: 注入 x-user-id）
  sendMessage: async (content: string) => {
    if (!content.trim()) return

    const { messages, userId, conversationId } = get()

    // 添加用户消息
    set(state => ({
      messages: [
        ...state.messages,
        { role: 'user', content, timestamp: Date.now() }
      ],
      isLoading: true,
      error: null
    }))

    try {
      // 确保有会话 ID（首次发消息前创建）
      let convId = conversationId
      if (!convId) {
        convId = await get().createConversation()
      }

      const response = await fetch(`${getApiBase()}/api/ai/chat/tools`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': userId,
          ...(convId ? { 'x-conversation-id': convId } : {}),
        },
        body: JSON.stringify({
          messages: [
            ...messages.map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content }
          ]
        })
      })

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const result = await response.json()

      // 提取 AI 回复（兼容 /chat/tools 和 /chat/rag 的响应结构）
      const aiContent = result?.choices?.[0]?.message?.content || '抱歉，AI 服务暂时不可用。'

      set(state => ({
        messages: [
          ...state.messages,
          {
            role: 'assistant',
            content: aiContent,
            timestamp: Date.now(),
            sources: result?.sources || []
          }
        ],
        isLoading: false
      }))

    } catch (error) {
      console.error('发送消息失败:', error)
      const errorMessage = error instanceof Error ? error.message : '未知错误'
      set({
        isLoading: false,
        error: '发送消息失败，请稍后重试'
      })

      // 添加错误提示消息
      set(state => ({
        messages: [
          ...state.messages,
          {
            role: 'assistant',
            content: `抱歉，发送消息失败了 (${errorMessage})。请检查网络连接后重试。`,
            timestamp: Date.now()
          }
        ]
      }))
    }
  },

  // 加载会话列表（P2-4: 接 REST）
  loadConversations: async () => {
    const { userId } = get()
    try {
      const response = await fetch(`${getApiBase()}/api/ai/conversations?limit=20`, {
        headers: { 'x-user-id': userId }
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      set({ conversations: data.data || [] })
    } catch (error) {
      console.error('加载会话列表失败:', error)
    }
  },

  // 加载历史消息（P2-4: 接 REST）
  loadMessages: async (conversationId: string) => {
    const { userId } = get()
    set({ conversationId, isLoading: true })

    try {
      const response = await fetch(
        `${getApiBase()}/api/ai/conversations/${conversationId}/messages?limit=50`,
        { headers: { 'x-user-id': userId } }
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      // 后端返回的消息格式兼容 Message 接口
      const msgs: Message[] = (data.data || []).map((m: any) => ({
        role: m.role,
        content: m.content,
        timestamp: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
      }))
      set({ messages: msgs, isLoading: false })
    } catch (error) {
      console.error('加载消息历史失败:', error)
      set({ messages: [], isLoading: false })
    }
  },

  // 创建新会话（P2-4: 接 REST）
  createConversation: async (title?: string) => {
    const { userId } = get()
    try {
      const url = `${getApiBase()}/api/ai/conversations` +
        (title ? `?title=${encodeURIComponent(title)}` : '')
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'x-user-id': userId }
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      // mode=local 时后端可能返回 null，此时生成临时 ID 保证流程不中断
      const newId = (data && data.id) ? data.id : `temp-${Date.now()}`
      if (newId.startsWith('temp-') || !data) {
        // 后端无持久化，使用临时 ID；不影响后续消息发送（save_ai_message 会自动归档）
        set(state => ({
          conversationId: newId,
          messages: [],
          conversations: data ? [data, ...state.conversations] : state.conversations
        }))
      } else {
        set(state => ({
          conversationId: newId,
          messages: [],
          conversations: [data, ...state.conversations]
        }))
      }
      return newId
    } catch (error) {
      console.error('创建会话失败:', error)
      // 即使创建失败也返回临时 ID，确保 sendMessage 不中断
      const tempId = `temp-${Date.now()}`
      set(state => ({ conversationId: tempId }))
      return tempId
    }
  },

  // 删除会话（P2-4: 接 REST）
  deleteConversation: async (conversationId: string) => {
    const { userId } = get()
    try {
      await fetch(`${getApiBase()}/api/ai/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: { 'x-user-id': userId }
      })
    } catch (error) {
      console.error('删除会话失败:', error)
    }
    set(state => ({
      conversations: state.conversations.filter(c => c.id !== conversationId),
      conversationId: state.conversationId === conversationId ? null : state.conversationId
    }))
  },

  // 清空消息
  clearMessages: () => {
    set({ messages: [], conversationId: null })
  },

  // 设置错误
  setError: (error: string | null) => {
    set({ error })
  }
}))
