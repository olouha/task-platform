/**
 * AI 对话窗口组件
 * 悬浮在页面侧边，支持上下文记忆
 */

import React, { useState, useRef, useEffect } from 'react'
import { Button, Input, Spin, Tooltip, Dropdown, List, Empty } from 'antd'
import {
  RobotOutlined,
  CloseOutlined,
  SendOutlined,
  DeleteOutlined,
  PlusOutlined,
  MessageOutlined
} from '@ant-design/icons'
import { useChatStore } from '../stores/chatStore'
import './AIChatWindow.css'

interface AIChatWindowProps {
  // 可以传入一个触发器按钮的显示位置
  position?: 'header' | 'floating'
}

const AIChatWindow: React.FC<AIChatWindowProps> = ({ position = 'header' }) => {
  const {
    messages,
    conversations,
    isOpen,
    isLoading,
    error,
    conversationId,
    openChat,
    closeChat,
    sendMessage,
    createConversation,
    deleteConversation,
    clearMessages,
    loadMessages
  } = useChatStore()

  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // 发送消息
  const handleSend = async () => {
    const trimmedInput = input.trim()
    if (!trimmedInput || isLoading) return

    const message = trimmedInput
    setInput('')

    await sendMessage(message)
  }

  // 键盘事件
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 新建会话
  const handleNewConversation = async () => {
    clearMessages()
    await createConversation()
    setShowHistory(false)
  }

  // 选择历史会话
  const handleSelectConversation = (convId: string) => {
    loadMessages(convId)
    setShowHistory(false)
  }

  // 删除会话
  const handleDeleteConversation = (e: React.MouseEvent, convId: string) => {
    e.stopPropagation()
    deleteConversation(convId)
  }

  // 如果在 header 位置且未打开，显示一个按钮
  if (position === 'header' && !isOpen) {
    return (
      <div className="ai-chat-header-button">
        <Tooltip title="AI 助手">
          <Button
            type="text"
            icon={<img src="/ai-logo.jpg" alt="AI" style={{ width: 18, height: 18, borderRadius: 4, objectFit: 'cover' }} />}
            onClick={openChat}
            className="ai-assistant-btn"
          >
            AI 助手
          </Button>
        </Tooltip>
      </div>
    )
  }

  // 如果是悬浮按钮模式
  if (position === 'floating' && !isOpen) {
    return (
      <Tooltip title="打开 AI 助手">
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<img src="/ai-logo.jpg" alt="AI" style={{ width: 24, height: 24, borderRadius: 6, objectFit: 'cover' }} />}
          className="ai-chat-fab"
          onClick={openChat}
        />
      </Tooltip>
    )
  }

  // 对话窗口主体
  return (
    <div className="ai-chat-container">
      {/* 标题栏 */}
      <div className="ai-chat-header">
        <div className="ai-chat-header-left">
          <img src="/ai-logo.jpg" alt="AI" style={{ width: 20, height: 20, borderRadius: 4, objectFit: 'cover', marginRight: 8 }} />
          <span>AI 助手</span>
          {conversationId && (
            <span className="ai-chat-session-indicator">新会话</span>
          )}
        </div>
        <div className="ai-chat-header-actions">
          <Dropdown
            menu={{
              items: [
                {
                  key: 'new',
                  icon: <PlusOutlined />,
                  label: '新建会话',
                  onClick: handleNewConversation
                },
                {
                  key: 'history',
                  icon: <MessageOutlined />,
                  label: '会话历史',
                  onClick: () => setShowHistory(!showHistory)
                },
                { type: 'divider' },
                {
                  key: 'clear',
                  icon: <DeleteOutlined />,
                  label: '清空对话',
                  danger: true,
                  onClick: clearMessages
                }
              ]
            }}
            trigger={['click']}
          >
            <Button type="text" size="small" className="ai-chat-menu-btn">
              <span className="ai-chat-menu-icon">⋯</span>
            </Button>
          </Dropdown>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={closeChat}
            className="ai-chat-close-btn"
          />
        </div>
      </div>

      {/* 会话历史侧边栏 */}
      {showHistory && (
        <div className="ai-chat-history">
          <div className="ai-chat-history-header">
            <span>会话历史</span>
            <Button
              type="text"
              size="small"
              icon={<PlusOutlined />}
              onClick={handleNewConversation}
            >
              新建
            </Button>
          </div>
          <div className="ai-chat-history-list">
            {conversations.length === 0 ? (
              <Empty
                description="暂无会话历史"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ margin: '20px 0' }}
              />
            ) : (
              <List
                size="small"
                dataSource={conversations}
                renderItem={item => (
                  <List.Item
                    className={`ai-chat-history-item ${
                      item.id === conversationId ? 'active' : ''
                    }`}
                    onClick={() => handleSelectConversation(item.id)}
                    extra={
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={e => handleDeleteConversation(e, item.id)}
                      />
                    }
                  >
                    {item.title}
                  </List.Item>
                )}
              />
            )}
          </div>
        </div>
      )}

      {/* 消息区域 */}
      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <div className="ai-chat-welcome">
            <img src="/ai-logo.jpg" alt="AI" style={{ width: 64, height: 64, borderRadius: 12, objectFit: 'cover', marginBottom: 16 }} />
            <h3>你好，我是AI助手蝌仔</h3>
            <p>可以帮您解答工程调差相关的问题</p>
            <div className="ai-chat-suggestions">
              <Button size="small" onClick={() => setInput('调差是什么？')}>
                调差是什么？
              </Button>
              <Button size="small" onClick={() => setInput('如何计算钢筋调差？')}>
                如何计算钢筋调差？
              </Button>
              <Button size="small" onClick={() => setInput('最新的烟台钢筋价格？')}>
                最新的烟台钢筋价格？
              </Button>
            </div>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? (
                <span>我</span>
              ) : (
                <img src="/ai-logo.jpg" alt="AI" style={{ width: 32, height: 32, borderRadius: 6, objectFit: 'cover' }} />
              )}
            </div>
            <div className="message-content">
              <div className="message-text">{msg.content}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                  <span className="sources-label">参考：</span>
                  {msg.sources.map((source, i) => (
                    <span key={i} className="source-tag">{source.title}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="message-loading">
                <Spin size="small" />
                <span>AI 正在思考...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="ai-chat-error">
            <span>⚠️ {error}</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="ai-chat-input-area">
        <div className="ai-chat-input-wrapper">
          <Input.TextArea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入问题，按 Enter 发送..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={isLoading}
            className="ai-chat-textarea"
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={isLoading}
            disabled={!input.trim()}
            className="ai-chat-send-btn"
          >
            发送
          </Button>
        </div>
        <div className="ai-chat-input-hint">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </div>
  )
}

export default AIChatWindow