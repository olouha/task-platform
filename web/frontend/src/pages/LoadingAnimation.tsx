/**
 * 登录成功加载动画 - 约10秒
 * 政企科技系统风格，沉稳专业
 */
import { useState, useEffect } from 'react'
import './LoadingAnimation.css'

interface LoadingAnimationProps {
  onComplete: () => void
}

const LOADING_STEPS = [
  { text: '登录成功', delay: 0 },
  { text: '正在进入 Knights AI 系统', delay: 800 },
  { text: '加载基础数据 35%', delay: 2200 },
  { text: '加载基础数据 62%', delay: 3800 },
  { text: '加载基础数据 78%', delay: 4800 },
  { text: '同步造价模型中，请稍候', delay: 6200 },
  { text: '加载完成', delay: 8200 },
]

const INFO_CARDS = [
  { title: '造价指标', value: '2,847 条', x: 'right', y: 'top' },
  { title: '工程量清单', value: '156 项', x: 'right', y: 'middle' },
  { title: '材料价格', value: '1,203 条', x: 'right', y: 'bottom' },
  { title: '风险预警', value: '3 项待处理', x: 'bottom', y: 'left' },
  { title: '标准工期', value: '98.5% 达标', x: 'bottom', y: 'center' },
]

export default function LoadingAnimation({ onComplete }: LoadingAnimationProps) {
  const [progress, setProgress] = useState(0)
  const [ringRotation, setRingRotation] = useState(0)
  const [showBuilding, setShowBuilding] = useState(false)
  const [showGrid, setShowGrid] = useState(false)
  const [showInfoCards, setShowInfoCards] = useState(false)
  const [currentStep, setCurrentStep] = useState(-1)
  const [fadeOut, setFadeOut] = useState(false)

  useEffect(() => {
    // 环形进度条旋转
    const ringInterval = setInterval(() => {
      setRingRotation(prev => (prev + 1) % 360)
    }, 30)

    // 进度条
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          return 100
        }
        return prev + 0.8
      })
    }, 60)

    // 加载步骤
    LOADING_STEPS.forEach(step => {
      setTimeout(() => {
        setCurrentStep(step.delay === 0 ? 0 : LOADING_STEPS.indexOf(step))
      }, step.delay)
    })

    // 显示建筑线框
    setTimeout(() => setShowBuilding(true), 1500)

    // 显示数据网格
    setTimeout(() => setShowGrid(true), 2500)

    // 显示信息卡片
    setTimeout(() => setShowInfoCards(true), 6000)

    // 淡出并完成
    setTimeout(() => {
      setFadeOut(true)
      setTimeout(onComplete, 800)
    }, 9500)

    return () => {
      clearInterval(ringInterval)
      clearInterval(progressInterval)
    }
  }, [onComplete])

  return (
    <div className={`loading-page ${fadeOut ? 'fade-out' : ''}`}>
      {/* 流动数据网格背景 */}
      <div className={`data-grid ${showGrid ? 'visible' : ''}`}>
        <svg viewBox="0 0 1200 675" preserveAspectRatio="xMidYMid slice">
          <defs>
            <linearGradient id="gridGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="rgba(91, 140, 255, 0.08)" />
              <stop offset="50%" stopColor="rgba(106, 90, 205, 0.05)" />
              <stop offset="100%" stopColor="rgba(91, 140, 255, 0.08)" />
            </linearGradient>
          </defs>
          {/* 水平线 */}
          {Array.from({ length: 12 }).map((_, i) => (
            <line
              key={`h-${i}`}
              x1="0"
              y1={i * 60}
              x2="1200"
              y2={i * 60}
              stroke="url(#gridGrad)"
              strokeWidth="0.5"
              style={{
                animation: `gridLineH 4s ease-in-out ${i * 0.3}s infinite`,
              }}
            />
          ))}
          {/* 垂直线 */}
          {Array.from({ length: 20 }).map((_, i) => (
            <line
              key={`v-${i}`}
              x1={i * 60 + (i % 2) * 30}
              y1="0"
              x2={i * 60 + (i % 2) * 30}
              y2="675"
              stroke="url(#gridGrad)"
              strokeWidth="0.5"
              style={{
                animation: `gridLineV 5s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </svg>
      </div>

      {/* 右侧信息卡片 */}
      <div className={`info-cards-right ${showInfoCards ? 'visible' : ''}`}>
        {INFO_CARDS.filter(c => c.x === 'right').map((card, i) => (
          <div key={card.title} className="info-card" style={{ animationDelay: `${i * 0.15}s` }}>
            <div className="info-card-title">{card.title}</div>
            <div className="info-card-value">{card.value}</div>
          </div>
        ))}
      </div>

      {/* 底部信息卡片 */}
      <div className={`info-cards-bottom ${showInfoCards ? 'visible' : ''}`}>
        {INFO_CARDS.filter(c => c.x === 'bottom').map((card, i) => (
          <div key={card.title} className="info-card info-card-small" style={{ animationDelay: `${i * 0.15}s` }}>
            <div className="info-card-title">{card.title}</div>
            <div className="info-card-value">{card.value}</div>
          </div>
        ))}
      </div>

      {/* 中央加载卡片 */}
      <div className="loading-card">
        {/* 环形进度条 */}
        <div className="progress-ring-container">
          <svg className="progress-ring" width="120" height="120">
            <defs>
              <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#5B8CFF" />
                <stop offset="100%" stopColor="#A87BFF" />
              </linearGradient>
            </defs>
            {/* 背景环 */}
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="rgba(91, 140, 255, 0.15)"
              strokeWidth="3"
            />
            {/* 进度环 */}
            <circle
              cx="60"
              cy="60"
              r="52"
              fill="none"
              stroke="url(#ringGrad)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={`${progress * 3.27} 327`}
              transform="rotate(-90 60 60)"
              style={{
                transition: 'stroke-dasharray 0.1s ease',
              }}
            />
          </svg>
          {/* 旋转指示器 */}
          <div
            className="ring-indicator"
            style={{ transform: `rotate(${ringRotation}deg)` }}
          />
        </div>

        {/* 建筑线框模型 */}
        <div className={`building-wireframe ${showBuilding ? 'visible' : ''}`}>
          <svg viewBox="0 0 80 80" fill="none">
            {/* 建筑主体 */}
            <rect x="15" y="30" width="20" height="45" stroke="rgba(91, 140, 255, 0.6)" strokeWidth="0.8" fill="none" />
            <rect x="40" y="15" width="25" height="60" stroke="rgba(106, 90, 205, 0.6)" strokeWidth="0.8" fill="none" />
            {/* 顶部塔尖 */}
            <line x1="52.5" y1="15" x2="52.5" y2="5" stroke="rgba(91, 140, 255, 0.5)" strokeWidth="0.6" />
            {/* 窗户 */}
            <rect x="18" y="35" width="5" height="6" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="26" y="35" width="5" height="6" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="18" y="45" width="5" height="6" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="26" y="45" width="5" height="6" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="44" y="20" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="54" y="20" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="44" y="32" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="54" y="32" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="44" y="44" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="54" y="44" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="44" y="56" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
            <rect x="54" y="56" width="6" height="7" stroke="rgba(200, 220, 255, 0.4)" strokeWidth="0.4" fill="none" />
          </svg>
        </div>

        {/* 加载文字 */}
        <div className="loading-steps">
          {LOADING_STEPS.slice(0, currentStep + 1).map((step, i) => (
            <div
              key={step.text}
              className={`loading-step ${i === currentStep ? 'current' : 'done'}`}
            >
              {step.text}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
