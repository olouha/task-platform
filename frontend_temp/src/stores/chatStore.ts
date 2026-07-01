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

// API 基础地址
const getApiBase = () => {
  // Vite 开发模式下使用代理，访问 /api 自动转发到后端
  // 生产环境通过环境变量配置
  return import.meta.env.VITE_API_URL || ''
}

export const useChatStore = create<ChatState>((set, get) => ({
  // 初始状态
  messages: [],
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

  // 发送消息
  sendMessage: async (content: string) => {
    if (!content.trim()) return

    const { messages } = get()

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
      // 调用 RAG 对话 API (使用相对路径，Vite 代理到后端)
      const response = await fetch('/api/ai/chat/rag', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: [
            ...messages.map(m => ({ role: m.role, content: m.content })),
            { role: 'user', content }
          ]
        })
      })

      console.log('API response status:', response.status)

      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const result = await response.json()

      // 提取 AI 回复
      const aiContent = result?.choices?.[0]?.message?.content || '抱歉，AI 服务暂时不可用。'

      // 添加 AI 消息
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

  // 加载会话列表
  loadConversations: async () => {
    try {
      // TODO: 从后端获取会话列表（需要登录后才有 user_id）
      // const response = await fetch(`${apiBase}/api/ai/conversations`, {
      //   headers: { 'x-user-id': userId }
      // })
      // const data = await response.json()
      // set({ conversations: data.data || [] })

      // 目前暂时使用空列表
      set({ conversations: [] })
    } catch (error) {
      console.error('加载会话列表失败:', error)
    }
  },

  // 加载历史消息
  loadMessages: async (conversationId: string) => {
    set({ conversationId, isLoading: true })

    try {
      // TODO: 从后端获取消息历史
      // const response = await fetch(`${apiBase}/api/ai/conversations/${conversationId}/messages`)
      // const data = await response.json()
      // set({ messages: data.data || [] })

      // 暂时清空
      set({ messages: [], isLoading: false })
    } catch (error) {
      console.error('加载消息历史失败:', error)
      set({ isLoading: false })
    }
  },

  // 创建新会话
  createConversation: async (title?: string) => {
    try {
      // TODO: 调用后端创建会话
      // const response = await fetch(`${apiBase}/api/ai/conversations`, {
      //   method: 'POST',
      //   params: { title }
      // })
      // const newConv = await response.json()

      // 暂时生成一个临时 ID
      const tempId = `temp-${Date.now()}`
      set(state => ({
        conversationId: tempId,
        messages: []
      }))

      return tempId
    } catch (error) {
      console.error('创建会话失败:', error)
      return null
    }
  },

  // 删除会话
  deleteConversation: async (conversationId: string) => {
    try {
      // TODO: 调用后端删除会话
      // await fetch(`${apiBase}/api/ai/conversations/${conversationId}`, {
      //   method: 'DELETE'
      // })

      set(state => ({
        conversations: state.conversations.filter(c => c.id !== conversationId),
        conversationId: state.conversationId === conversationId ? null : state.conversationId
      }))
    } catch (error) {
      console.error('删除会话失败:', error)
    }
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