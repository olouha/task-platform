/**
 * 材料含量Section组件
 * 展示和编辑项目的材料含量（混凝土、钢筋、模板等地上/地下分项）
 */
import React from 'react'
import { Form, InputNumber, Typography, Divider, Tabs } from 'antd'
import './MaterialSection.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 材料含量数据 */
export interface MaterialData {
  // 混凝土含量（m³/㎡）
  concrete_above?: number    // 地上混凝土
  concrete_below?: number    // 地下混凝土
  concrete_total?: number    // 混凝土合计

  // 钢筋含量（kg/㎡）
  rebar_above?: number       // 地上钢筋
  rebar_below?: number       // 地下钢筋
  rebar_total?: number       // 钢筋合计

  // 模板含量（㎡/㎡）
  formwork_above?: number    // 地上模板
  formwork_below?: number    // 地下模板
  formwork_total?: number    // 模板合计

  // 砌体含量（m³/㎡）
  block_above?: number       // 地上砌体
  block_below?: number       // 地下砌体
  block_total?: number       // 砌体合计

  // 电缆含量（m/㎡）
  cable?: number             // 电缆

  // 管道含量（m/㎡）
  pipe?: number              // 管道

  // 风管含量（㎡/㎡）
  duct?: number              // 风管
}

export interface MaterialSectionProps {
  data: MaterialData
  editMode: boolean
  onChange?: (field: keyof MaterialData, value: number | undefined) => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** 材料含量类别配置 */
const MATERIAL_CATEGORIES = [
  {
    key: 'concrete',
    label: '混凝土',
    unit: 'm³/㎡',
    fields: ['above', 'below', 'total'] as const,
    fieldLabels: { above: '地上', below: '地下', total: '合计' },
  },
  {
    key: 'rebar',
    label: '钢筋',
    unit: 'kg/㎡',
    fields: ['above', 'below', 'total'] as const,
    fieldLabels: { above: '地上', below: '地下', total: '合计' },
  },
  {
    key: 'formwork',
    label: '模板',
    unit: '㎡/㎡',
    fields: ['above', 'below', 'total'] as const,
    fieldLabels: { above: '地上', below: '地下', total: '合计' },
  },
  {
    key: 'block',
    label: '砌体',
    unit: 'm³/㎡',
    fields: ['above', 'below', 'total'] as const,
    fieldLabels: { above: '地上', below: '地下', total: '合计' },
  },
]

/** 其他材料配置 */
const OTHER_MATERIALS: {
  key: keyof Pick<MaterialData, 'cable' | 'pipe' | 'duct'>
  label: string
  unit: string
}[] = [
  { key: 'cable', label: '电缆', unit: 'm/㎡' },
  { key: 'pipe', label: '管道', unit: 'm/㎡' },
  { key: 'duct', label: '风管', unit: '㎡/㎡' },
]

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化数字
 */
const formatNumber = (num?: number, decimals: number = 3): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// ============================================================================
// 组件定义
// ============================================================================

const { Text } = Typography

export default function MaterialSection({
  data,
  editMode,
  onChange,
}: MaterialSectionProps) {
  /**
   * 获取字段值
   */
  const getValue = (category: string, field: 'above' | 'below' | 'total'): number | undefined => {
    const key = `${category}_${field}` as keyof MaterialData
    return data[key] as number | undefined
  }

  /**
   * 处理变更
   */
  const handleChange = (category: string, field: 'above' | 'below' | 'total') => (
    value: number | null
  ) => {
    const key = `${category}_${field}` as keyof MaterialData
    onChange?.(key, value ?? undefined)
  }

  /**
   * 渲染查看模式的材料行
   */
  const renderViewRow = (category: typeof MATERIAL_CATEGORIES[0]) => {
    const above = getValue(category.key, 'above')
    const below = getValue(category.key, 'below')
    const total = getValue(category.key, 'total')

    return (
      <div key={category.key} className="material-row">
        <div className="material-row-label">
          <Text strong>{category.label}</Text>
          <Text type="secondary" className="material-unit">({category.unit})</Text>
        </div>
        <div className="material-row-values">
          <div className="material-value-item">
            <Text type="secondary">{category.fieldLabels.above}</Text>
            <Text className="material-value">{formatNumber(above)}</Text>
          </div>
          <div className="material-value-item">
            <Text type="secondary">{category.fieldLabels.below}</Text>
            <Text className="material-value">{formatNumber(below)}</Text>
          </div>
          <div className="material-value-item total">
            <Text type="secondary">{category.fieldLabels.total}</Text>
            <Text className="material-value">{formatNumber(total)}</Text>
          </div>
        </div>
      </div>
    )
  }

  /**
   * 渲染编辑模式的材料行
   */
  const renderEditRow = (category: typeof MATERIAL_CATEGORIES[0]) => (
    <div key={category.key} className="material-row material-row-edit">
      <div className="material-row-label">
        <Text strong>{category.label}</Text>
        <Text type="secondary" className="material-unit">({category.unit})</Text>
      </div>
      <div className="material-row-inputs">
        <Form.Item label={category.fieldLabels.above} className="material-form-item">
          <InputNumber
            value={getValue(category.key, 'above')}
            onChange={handleChange(category.key, 'above')}
            min={0}
            step={0.001}
            placeholder="0.000"
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label={category.fieldLabels.below} className="material-form-item">
          <InputNumber
            value={getValue(category.key, 'below')}
            onChange={handleChange(category.key, 'below')}
            min={0}
            step={0.001}
            placeholder="0.000"
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label={category.fieldLabels.total} className="material-form-item">
          <InputNumber
            value={getValue(category.key, 'total')}
            onChange={handleChange(category.key, 'total')}
            min={0}
            step={0.001}
            placeholder="0.000"
            style={{ width: '100%' }}
          />
        </Form.Item>
      </div>
    </div>
  )

  /**
   * 渲染其他材料项
   */
  const renderOtherMaterial = (item: typeof OTHER_MATERIALS[0], index: number) => {
    const value = data[item.key]

    return (
      <div key={item.key} className="material-other-item">
        <Text type="secondary">{item.label}</Text>
        {editMode ? (
          <Form.Item className="material-form-item-inline">
            <InputNumber
              value={value}
              onChange={(v) => onChange?.(item.key, v ?? undefined)}
              min={0}
              step={0.001}
              placeholder="0.000"
              style={{ width: '100%' }}
              addonAfter={item.unit}
            />
          </Form.Item>
        ) : (
          <Text className="material-value">
            {value !== undefined && value !== null ? formatNumber(value) : '-'}
            <Text type="secondary" style={{ fontSize: 11 }}> {item.unit}</Text>
          </Text>
        )}
      </div>
    )
  }

  return (
    <div className="material-section">
      <div className="material-title">
        <Text strong>主要材料含量</Text>
      </div>

      {/* 主要材料（混凝土、钢筋、模板、砌体） */}
      <div className="material-main">
        {editMode
          ? MATERIAL_CATEGORIES.map(renderEditRow)
          : MATERIAL_CATEGORIES.map(renderViewRow)}
      </div>

      <Divider style={{ margin: '16px 0' }} />

      {/* 其他材料 */}
      <div className="material-other">
        <div className="material-other-title">
          <Text strong>其他材料</Text>
        </div>
        <div className="material-other-grid">
          {OTHER_MATERIALS.map(renderOtherMaterial)}
        </div>
      </div>
    </div>
  )
}