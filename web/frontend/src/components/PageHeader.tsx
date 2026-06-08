/**
 * 页面通用标题组件
 * 包含页面标题 + KnigHts 品牌标识
 */
import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle }) => {
  return (
    <div className="page-header" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div>
        <h2 className="page-title">{title}</h2>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      <span style={{
        fontFamily: "'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
        fontWeight: 700,
        fontSize: 40,
        letterSpacing: 2,
        transform: 'skewX(-8deg)',
        display: 'inline-block',
      }}>
        <span style={{ color: '#1a3a6b' }}>Knig</span>
        <span style={{ color: '#1a3a6b' }}>H</span>
        <span style={{ color: '#1a3a6b' }}>ts</span>
      </span>
    </div>
  )
}

export default PageHeader