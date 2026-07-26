/**
 * 建筑指标 Section 组件
 * 展示和编辑项目的建筑指标（墙地比、窗墙比、窗含量、门含量、内墙含量、阳台占比、装配率、装配构件含量）
 */
import React from 'react'
import { Form, InputNumber, Typography } from 'antd'
import './BuildingIndexSection.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 建筑指标数据 */
export interface BuildingIndexData {
  wall_floor_ratio?: number       // 墙地比 (%)
  window_wall_ratio?: number      // 窗墙比 (%)
  window_content?: number         // 窗含量 (㎡/㎡)
  door_content?: number           // 门含量 (㎡/㎡)
  interior_wall_content?: number  // 内墙含量 (㎡/㎡)
  balcony_ratio?: number          // 阳台占比 (%)
  assembly_rate?: number          // 装配率 (%)
  assembly_content?: number       // 装配构件含量 (m³/㎡)
}

export interface BuildingIndexSectionProps {
  data: BuildingIndexData
  editMode: boolean
  onChange?: (field: keyof BuildingIndexData, value: number | undefined) => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** 建筑指标字段配置 */
const FIELDS: { key: keyof BuildingIndexData; label: string; unit: string }[] = [
  { key: 'wall_floor_ratio', label: '墙地比', unit: '%' },
  { key: 'window_wall_ratio', label: '窗墙比', unit: '%' },
  { key: 'window_content', label: '窗含量', unit: '㎡/㎡' },
  { key: 'door_content', label: '门含量', unit: '㎡/㎡' },
  { key: 'interior_wall_content', label: '内墙含量', unit: '㎡/㎡' },
  { key: 'balcony_ratio', label: '阳台占比', unit: '%' },
  { key: 'assembly_rate', label: '装配率', unit: '%' },
  { key: 'assembly_content', label: '装配构件含量', unit: 'm³/㎡' },
]

// ============================================================================
// 工具函数
// ============================================================================

const formatNumber = (num?: number, decimals = 2): string => {
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

export default function BuildingIndexSection({
  data,
  editMode,
  onChange,
}: BuildingIndexSectionProps) {
  return (
    <div className="building-index-section">
      <div className="building-index-grid">
        {FIELDS.map((f) => {
          const value = data[f.key]
          return (
            <div key={f.key} className="building-index-item">
              <Text type="secondary">{f.label}</Text>
              {editMode ? (
                <Form.Item className="building-index-form-item">
                  <InputNumber
                    value={value}
                    onChange={(v) => onChange?.(f.key, v ?? undefined)}
                    min={0}
                    step={0.01}
                    placeholder="0.00"
                    style={{ width: '100%' }}
                    addonAfter={f.unit}
                  />
                </Form.Item>
              ) : (
                <Text className="building-index-value">
                  {value !== undefined && value !== null ? formatNumber(value) : '-'}
                  <Text type="secondary" style={{ fontSize: 11 }}> {f.unit}</Text>
                </Text>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
