/**
 * 登录页 - 16:9 宽屏商务科技风
 * 深藏蓝→蓝紫→柔雾紫渐变夜空 + 半透明磨砂玻璃卡片 + 城市剪影
 */
import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Form, Input, Button, Checkbox, Typography, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import {
  isAuthenticated,
  login as apiLogin,
  saveRememberedAccount,
  clearRememberedAccount,
  getRememberedAccount,
} from '../auth'
import LoadingAnimation from './LoadingAnimation'
import './Login.css'

const { Title, Text, Link } = Typography

interface LoginForm {
  account: string
  password: string
  remember: boolean
}

/**
 * 远景城市天际线 - 轻柔远景轮廓
 * 建筑更低更淡，营造远景透视感
 */
interface Building {
  x: number
  w: number
  h: number
}

const BUILDINGS: Building[] = [
  { x: 0, w: 35, h: 28 },
  { x: 38, w: 28, h: 18 },
  { x: 70, w: 42, h: 38 },
  { x: 115, w: 25, h: 22 },
  { x: 143, w: 55, h: 32 },
  { x: 202, w: 32, h: 45 },
  { x: 238, w: 30, h: 25 },
  { x: 272, w: 60, h: 35 },
  { x: 336, w: 22, h: 18 },
  { x: 362, w: 48, h: 40 },
  { x: 414, w: 35, h: 28 },
  { x: 453, w: 55, h: 42 },
  { x: 512, w: 28, h: 22 },
  { x: 544, w: 42, h: 32 },
  { x: 590, w: 32, h: 26 },
  { x: 626, w: 50, h: 38 },
  { x: 680, w: 25, h: 20 },
  { x: 709, w: 52, h: 35 },
  { x: 765, w: 35, h: 28 },
  { x: 804, w: 48, h: 42 },
  { x: 856, w: 28, h: 22 },
  { x: 888, w: 42, h: 32 },
  { x: 934, w: 32, h: 25 },
  { x: 970, w: 55, h: 38 },
  { x: 1029, w: 38, h: 30 },
  { x: 1071, w: 52, h: 40 },
  { x: 1127, w: 73, h: 35 },
]

export default function Login() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [showLoading, setShowLoading] = useState(false)
  const [form] = Form.useForm<LoginForm>()

  // 夜空动态星点（随机位置/大小/亮度/节奏）
  const stars = useMemo(
    () =>
      Array.from({ length: 35 }, (_, i) => {
        const isBright = i % 7 === 0
        const speedType = i % 3
        return {
          top: Math.random() * 68,
          left: Math.random() * 100,
          size: isBright ? Math.random() * 1.0 + 1.2 : Math.random() * 0.8 + 0.4,
          delay: Math.random() * 10,
          duration: speedType === 0
            ? Math.random() * 2 + 2
            : speedType === 1
              ? Math.random() * 4 + 4
              : Math.random() * 5 + 6,
          isBright,
          speedType,
        }
      }),
    []
  )

  // 轻微漂浮粒子
  const particles = useMemo(
    () =>
      Array.from({ length: 15 }, () => ({
        top: Math.random() * 80 + 10,
        left: Math.random() * 100,
        size: Math.random() * 4 + 2,
        delay: Math.random() * 15,
        duration: Math.random() * 20 + 15,
      })),
    []
  )

  if (isAuthenticated()) {
    navigate('/dashboard', { replace: true })
  }

  const onFinish = async (values: LoginForm) => {
    const account = (values.account || '').trim()
    const password = values.password || ''

    if (!account) {
      message.error('请输入账号')
      return
    }
    if (password.length < 4) {
      message.error('登录码至少4位')
      return
    }

    setSubmitting(true)
    try {
      await apiLogin(account, password)
      if (values.remember) {
        saveRememberedAccount(account)
      } else {
        clearRememberedAccount()
      }
      message.success('登录成功')
      // 显示加载动画
      setShowLoading(true)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败，请检查账号密码')
      setSubmitting(false)
    }
  }

  const handleLoadingComplete = () => {
    navigate('/dashboard', { replace: true })
  }

  if (showLoading) {
    return <LoadingAnimation onComplete={handleLoadingComplete} />
  }

  return (
    <div className="login-page">
      {/* 深空云雾层（轻微3D流动感） */}
      <div className="nebula-layer">
        <div className="nebula-stream-1" />
        <div className="nebula-stream-2" />
        <div className="nebula-stream-3" />
      </div>

      {/* 背景夜空区 */}
      <div className="login-page-bg" />

      {/* 轻微漂浮粒子 */}
      <div className="floating-particles">
        {particles.map((p, i) => (
          <span
            key={i}
            className="floating-particle"
            style={{
              top: `${p.top}%`,
              left: `${p.left}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.duration}s`,
            }}
          />
        ))}
      </div>

      {/* 夜空动态星点 */}
      <div className="star-field">
        {stars.map((s, i) => (
          <span
            key={i}
            className={`star ${s.isBright ? 'star-bright' : ''}`}
            style={{
              top: `${s.top}%`,
              left: `${s.left}%`,
              width: `${s.size}px`,
              height: `${s.size}px`,
              animationDelay: `${s.delay}s`,
              animationDuration: `${s.duration}s`,
              animationName: s.speedType === 0 ? 'starTwinkleFast' : s.speedType === 1 ? 'starTwinkle' : 'starTwinkleSlow',
            }}
          />
        ))}
      </div>

      {/* 底部城市剪影区 - 远景城市天际线 */}
      <div className="skyline">
        <svg viewBox="0 0 1200 200" preserveAspectRatio="xMidYMax slice" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="bldGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0A1220" />
              <stop offset="100%" stopColor="#050A12" />
            </linearGradient>
          </defs>

          {/* 远景建筑剪影 */}
          {BUILDINGS.map((b, i) => {
            const y = 200 - b.h
            return (
              <rect
                key={i}
                x={b.x}
                y={y}
                width={b.w}
                height={b.h}
                fill="url(#bldGrad)"
                opacity="0.55"
              />
            )
          })}

          {/* 楼体窗户光点 - 错落有致，模拟办公楼灯光 */}
          {BUILDINGS.map((b, i) => {
            const y = 200 - b.h
            const innerPadding = 2
            // 固定随机种子，让错落效果保持一致
            const seed = i * 1000
            return (
              <g key={`w-${i}`}>
                {Array.from({ length: Math.floor((b.h - innerPadding * 2) / 9) }).map((_, r) =>
                  Array.from({ length: Math.max(1, Math.floor((b.w - innerPadding * 2) / 9)) }).map((_, c) => {
                    // 轻微随机偏移，营造错落感
                    const offsetX = ((seed + r * 17 + c * 31) % 3) - 1
                    const offsetY = ((seed + r * 23 + c * 19) % 3) - 1
                    const wx = b.x + innerPadding + c * 9 + offsetX
                    const wy = y + innerPadding + r * 9 + offsetY
                    // 严格边界检查
                    if (wx < b.x + innerPadding || wx > b.x + b.w - innerPadding - 1) return null
                    if (wy < y + innerPadding || wy > 200 - innerPadding - 1) return null
                    // 约15%的窗户随机不亮
                    if ((seed + r * 13 + c * 29) % 7 === 0) return null
                    return (
                      <rect
                        key={`${r}-${c}`}
                        x={wx}
                        y={wy}
                        width="2"
                        height="2"
                        rx="0.25"
                        fill="rgba(185, 205, 235, 0.4)"
                      />
                    )
                  })
                )}
              </g>
            )
          })}
        </svg>
        {/* 底部淡紫雾气 */}
        <div className="skyline-fog" />
        {/* 地平线光晕 */}
        <div className="skyline-glow" />
      </div>

      {/* 内容层（严格居中对称） */}
      <div className="login-center">
        {/* 顶部标题区 */}
        <div className="login-brand">
          <div className="login-brand-logo">
            <svg width="32" height="32" viewBox="0 0 36 36" fill="none">
              <rect x="4" y="16" width="12" height="16" rx="1.5" stroke="#5B8CFF" strokeWidth="1.8" fill="rgba(91, 140, 255, 0.1)" />
              <rect x="18" y="10" width="14" height="22" rx="1.5" stroke="#5B8CFF" strokeWidth="1.8" fill="rgba(91, 140, 255, 0.1)" />
              <rect x="7" y="20" width="3" height="3" rx="0.5" fill="#5B8CFF" />
              <rect x="12" y="20" width="3" height="3" rx="0.5" fill="#5B8CFF" />
              <rect x="21" y="14" width="4" height="4" rx="0.5" fill="#5B8CFF" />
              <rect x="27" y="14" width="4" height="4" rx="0.5" fill="#5B8CFF" />
              <rect x="21" y="22" width="4" height="4" rx="0.5" fill="#5B8CFF" />
              <rect x="27" y="22" width="4" height="4" rx="0.5" fill="#5B8CFF" />
            </svg>
          </div>
          <div className="login-brand-text">
            <div className="login-brand-title">Knights AI 系统</div>
            <div className="login-brand-sub">AI・COST・ANALYSIS</div>
          </div>
        </div>

        {/* 登录卡片 */}
        <div className="login-card">
          <div className="login-card-header">
            <div className="login-card-badge">INTERNAL</div>
            <Title level={3} className="login-card-title">
              欢迎登录
            </Title>
            <Text className="login-card-subtitle">Knights AI 系统</Text>
            <Text className="login-card-note">内部管控系统，仅限授权人员访问</Text>
          </div>

          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            initialValues={{
              account: getRememberedAccount(),
              remember: !!getRememberedAccount(),
            }}
            className="login-form"
            requiredMark={false}
          >
            <Form.Item
              name="account"
              label="账号"
              rules={[{ required: true, message: '请输入账号' }]}
            >
              <Input
                size="large"
                prefix={<UserOutlined style={{ color: '#5B8CFF' }} />}
                placeholder="请输入账号"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="登录码"
              rules={[{ required: true, message: '请输入登录码' }]}
            >
              <Input.Password
                size="large"
                prefix={<LockOutlined style={{ color: '#5B8CFF' }} />}
                placeholder="请输入登录码"
                autoComplete="current-password"
              />
            </Form.Item>

            <div className="login-form-options">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>记住账号</Checkbox>
              </Form.Item>
              <Link className="login-forgot" disabled>
                忘记登录码？（联系管理员）
              </Link>
            </div>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={submitting}
                className="login-submit-btn"
              >
                登录
              </Button>
            </Form.Item>

            {/* 安全警示（低饱和淡红圆角提示框） */}
            <div className="login-security-warning">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M7 1L13 12H1L7 1Z" stroke="#FFB4B4" strokeWidth="1.2" strokeLinejoin="round" />
                <line x1="7" y1="5.5" x2="7" y2="8.5" stroke="#FFB4B4" strokeWidth="1.2" strokeLinecap="round" />
                <circle cx="7" cy="10.3" r="0.7" fill="#FFB4B4" />
              </svg>
              <Text className="login-security-text">
                安全警示：系统涉及造价敏感数据，禁止账号转借，无关人员禁止访问。
              </Text>
            </div>
          </Form>
        </div>
      </div>

      {/* 版权文字 */}
      <Text className="login-copyright">© 2026 Knights AI 系统・内部使用</Text>
    </div>
  )
}
