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
      <img
        src="/knigHts_logo.png"
        alt="KnigHts"
        style={{
          height: 40,
          display: 'inline-block',
          verticalAlign: 'middle',
        }}
      />
    </div>
  )
}

export default PageHeader