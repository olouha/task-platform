import React from 'react'
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'

interface TrendChartProps {
  data: Array<{
    date: string
    avg_price: number
    min_price: number
    max_price: number
    count: number
  }>
}

const TrendChart: React.FC<TrendChartProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📊</div>
        <div className="empty-state-text">暂无价格走势数据</div>
      </div>
    )
  }

  const displayData = data.slice(-15)
  const maxAvg = Math.max(...displayData.map(d => d.avg_price))
  const minAvg = Math.min(...displayData.map(d => d.avg_price))
  const latest = displayData[displayData.length - 1]

  // 计算趋势
  const first = displayData[0]?.avg_price || 0
  const last = latest?.avg_price || 0
  const trend = last - first
  const trendPercent = first > 0 ? ((trend / first) * 100).toFixed(2) : '0'
  const isUp = trend >= 0

  return (
    <div className="trend-chart">
      {/* 统计信息 - 科技风格 */}
      <div className="trend-chart-header">
        <div className="trend-chart-stat">
          <div className="trend-chart-stat-value highlight-number">
            {latest?.avg_price?.toLocaleString()}
          </div>
          <div className="trend-chart-stat-label">最新均价（元/吨）</div>
        </div>
        <div className="trend-chart-stat">
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            color: isUp ? '#EF4444' : '#10B981',
            fontSize: 18,
            fontWeight: 600
          }}>
            {isUp ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
            {Math.abs(trend).toLocaleString()} ({isUp ? '+' : ''}{trendPercent}%)
          </div>
          <div className="trend-chart-stat-label">价格趋势</div>
        </div>
        <div className="trend-chart-stat">
          <div style={{
            fontSize: 18,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            {Math.max(...displayData.map(d => d.max_price)).toLocaleString()}
          </div>
          <div className="trend-chart-stat-label">最高价（元/吨）</div>
        </div>
        <div className="trend-chart-stat">
          <div style={{
            fontSize: 18,
            fontWeight: 600,
            background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            {Math.min(...displayData.map(d => d.min_price)).toLocaleString()}
          </div>
          <div className="trend-chart-stat-label">最低价（元/吨）</div>
        </div>
      </div>

      {/* 柱状图 - 科技风格 */}
      <div className="trend-chart-bars">
        {displayData.map((d, i) => {
          const height = (d.avg_price / maxAvg) * 160
          const isMax = d.avg_price === maxAvg
          const isLatest = i === displayData.length - 1
          return (
            <div key={i} className="trend-chart-bar-wrapper">
              <div
                className="trend-chart-bar"
                style={{
                  height: `${Math.max(height, 4)}px`,
                  background: isLatest
                    ? 'linear-gradient(180deg, #4A86C8 0%, #16325C 100%)'
                    : isMax
                      ? 'linear-gradient(180deg, #EF4444 0%, #B91C1C 100%)'
                      : 'linear-gradient(180deg, #4A86C880 0%, #16325C80 100%)',
                  boxShadow: isLatest ? '0 0 12px rgba(74, 134, 200, 0.5)' : 'none'
                }}
              />
              <div className="trend-chart-bar-label">{d.date.slice(5)}</div>
            </div>
          )
        })}
      </div>

      {/* 底部说明 - 科技风格 */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid #E8EBF0',
        fontSize: 12,
        color: '#666'
      }}>
        <span>展示最近 {displayData.length} 个交易日数据</span>
        <span style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6
        }}>
          <span style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #4A86C8, #16325C)'
          }} />
          数据来源：山东烟台钢筋价格 · 我的钢铁网
        </span>
      </div>
    </div>
  )
}

export default TrendChart