/**
 * 专项工程费用Section组件
 * 展示和编辑项目的专项工程费用（8个类别）
 */
import React from 'react'
import { Form, InputNumber, Typography, Divider, Row, Col } from 'antd'
import './SpecialCostSection.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 专项工程费用数据 */
export interface SpecialCostData {
  // 8个专项工程费用类别
  pile?: number              // 桩基工程
  foundation_support?: number // 基坑支护
  curtain_wall?: number      // 幕墙工程
  decoration?: number        // 精装修工程
  landscape?: number         // 景观绿化
  intelligent?: number       // 智能化工程
  gas?: number               // 燃气工程
  solar?: number             // 光伏/太阳能
}

export interface SpecialCostSectionProps {
  data: SpecialCostData
  editMode: boolean
  onChange?: (field: keyof SpecialCostData, value: number | undefined) => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** 专项工程费用配置 */
const SPECIAL_COST_ITEMS: {
  key: keyof SpecialCostData
  label: string
  unit: string
  description?: string
}[] = [
  { key: 'pile', label: '桩基工程', unit: '元/㎡', description: '地基处理、桩基施工费用' },
  { key: 'foundation_support', label: '基坑支护', unit: '元/㎡', description: '基坑开挖、支护结构费用' },
  { key: 'curtain_wall', label: '幕墙工程', unit: '元/㎡', description: '玻璃幕墙、石材幕墙等' },
  { key: 'decoration', label: '精装修工程', unit: '元/㎡', description: '室内精装修费用' },
  { key: 'landscape', label: '景观绿化', unit: '元/㎡', description: '园林景观、绿化工程' },
  { key: 'intelligent', label: '智能化工程', unit: '元/㎡', description: '安防、楼宇智能化系统' },
  { key: 'gas', label: '燃气工程', unit: '元/㎡', description: '燃气管道、设备安装' },
  { key: 'solar', label: '光伏/太阳能', unit: '元/㎡', description: '太阳能系统、光伏发电' },
]

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化数字（千分位）
 */
const formatNumber = (num?: number): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

// ============================================================================
// 组件定义
// ============================================================================

const { Text } = Typography

export default function SpecialCostSection({
  data,
  editMode,
  onChange,
}: SpecialCostSectionProps) {
  /**
   * 渲染查看模式下的专项费用项
   */
  const renderViewItem = (item: typeof SPECIAL_COST_ITEMS[0]) => {
    const value = data[item.key]
    return (
      <div key={item.key} className="special-cost-item">
        <div className="special-cost-item-header">
          <Text strong>{item.label}</Text>
          <Text type="secondary" className="special-cost-unit">
            {item.unit}
          </Text>
        </div>
        <div className="special-cost-item-value">
          {value !== undefined && value !== null
            ? formatNumber(value)
            : '-'}
        </div>
        {item.description && (
          <Text type="secondary" className="special-cost-item-desc">
            {item.description}
          </Text>
        )}
      </div>
    )
  }

  /**
   * 渲染编辑模式下的专项费用项
   */
  const renderEditItem = (item: typeof SPECIAL_COST_ITEMS[0]) => (
    <Col key={item.key} span={12}>
      <Form.Item
        label={
          <span className="special-cost-edit-label">
            {item.label}
            <Text type="secondary" style={{ fontSize: 12 }}>
              ({item.unit})
            </Text>
          </span>
        }
        className="special-cost-form-item"
      >
        <InputNumber
          value={data[item.key]}
          onChange={(v) => onChange?.(item.key, v ?? undefined)}
          min={0}
          step={0.01}
          placeholder="0.00"
          style={{ width: '100%' }}
        />
      </Form.Item>
    </Col>
  )

  return (
    <div className="special-cost-section">
      <div className="special-cost-title">
        <Text strong>专项工程费用（元/㎡）</Text>
      </div>

      {editMode ? (
        // 编辑模式：两列布局的表单
        <Row gutter={[16, 8]}>
          {SPECIAL_COST_ITEMS.map(renderEditItem)}
        </Row>
      ) : (
        // 查看模式：网格布局展示
        <div className="special-cost-grid">
          {SPECIAL_COST_ITEMS.map(renderViewItem)}
        </div>
      )}

      {/* 统计信息 */}
      {!editMode && (
        <>
          <Divider style={{ margin: '16px 0' }} />
          <div className="special-cost-summary">
            <div className="special-cost-summary-item">
              <Text type="secondary">已填写项目：</Text>
              <Text strong>
                {SPECIAL_COST_ITEMS.filter(item => data[item.key] !== undefined && data[item.key] !== null).length} / {SPECIAL_COST_ITEMS.length}
              </Text>
            </div>
            <div className="special-cost-summary-item">
              <Text type="secondary">专项费用合计：</Text>
              <Text strong style={{ color: '#1890ff' }}>
                {formatNumber(
                  SPECIAL_COST_ITEMS.reduce(
                    (sum, item) => sum + (data[item.key] || 0),
                    0
                  )
                )} 元/㎡
              </Text>
            </div>
          </div>
        </>
      )}
    </div>
  )
}