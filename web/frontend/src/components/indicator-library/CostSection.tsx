/**
 * 造价指标Section组件
 * 展示和编辑项目的造价指标（单方造价、总造价、分项造价等）
 */
import React from 'react'
import { Form, InputNumber, Typography, Divider, Tooltip } from 'antd'
import { DollarOutlined, PercentageOutlined, InfoCircleOutlined } from '@ant-design/icons'
import './CostSection.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 造价指标数据 */
export interface CostData {
  // 整体造价
  unit_cost?: number        // 单方造价（元/㎡）
  total_cost?: number       // 总造价（万元）

  // 分项单方造价
  unit_structure?: number   // 结构（万元/㎡）
  unit_installation?: number // 安装（万元/㎡）
  unit_decoration?: number  // 装修（万元/㎡）
  unit_measure?: number     // 措施（万元/㎡）

  // 地上/地下造价占比
  above_cost_ratio?: number // 地上造价占比（%）
  below_cost_ratio?: number // 地下造价占比（%）

  // 经济指标（直接费）
  underground_structure?: number  // 地下结构
  above_structure?: number        // 地上结构
  roof?: number                   // 屋面
  exterior_wall?: number          // 外墙
  interior_wall?: number          // 内墙
  floor?: number                  // 楼地面
  electrical?: number             // 电气
  plumbing?: number               // 给排水
  hvac?: number                   // 暖通
  elevator?: number               // 电梯
  fire?: number                   // 消防
  measures?: number               // 措施费
}

export interface CostSectionProps {
  data: CostData
  editMode: boolean
  onChange?: (field: keyof CostData, value: number | undefined) => void
}

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化数字（千分位）
 */
const formatNumber = (num?: number, decimals: number = 2): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

/**
 * 格式化万元单位
 */
const formatWan = (num?: number): string => {
  if (num === undefined || num === null) return '-'
  return (num / 10000).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

// ============================================================================
// 组件定义
// ============================================================================

const { Text } = Typography

export default function CostSection({
  data,
  editMode,
  onChange,
}: CostSectionProps) {
  /**
   * 渲染查看模式下的数值字段
   */
  const renderViewField = (
    label: string,
    value: number | undefined,
    suffix: string,
    highlight?: boolean
  ) => (
    <div className={`cost-field ${highlight ? 'highlight' : ''}`}>
      <span className="cost-label">{label}</span>
      <span className="cost-value">
        {value !== undefined && value !== null
          ? `${formatNumber(value)}${suffix}`
          : '-'}
      </span>
    </div>
  )

  /**
   * 渲染编辑模式下的数值输入
   */
  const renderEditField = (
    field: keyof CostData,
    label: string,
    placeholder: string = '0.00',
    min: number = 0,
    max?: number,
    step: number = 0.01,
    suffix?: string
  ) => (
    <Form.Item label={label} className="cost-form-item">
      <InputNumber
        value={data[field]}
        onChange={(v) => onChange?.(field, v ?? undefined)}
        min={min}
        max={max}
        step={step}
        placeholder={placeholder}
        style={{ width: '100%' }}
        prefix={suffix}
      />
    </Form.Item>
  )

  return (
    <div className="cost-section">
      {/* 主要造价指标 */}
      <div className="cost-main">
        <div className="cost-main-title">
          <DollarOutlined style={{ marginRight: 8, color: '#f5222d' }} />
          <Text strong>主要造价指标</Text>
        </div>

        <div className="cost-row two-col">
          {editMode ? (
            <>
              <Form.Item label="单方造价（元/㎡）" className="cost-form-item">
                <InputNumber
                  value={data.unit_cost}
                  onChange={(v) => onChange?.('unit_cost', v ?? undefined)}
                  min={0}
                  step={1}
                  placeholder="0"
                  style={{ width: '100%' }}
                  formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={(value) => value?.replace(/,/g, '') as unknown as number}
                />
              </Form.Item>
              <Form.Item label="总造价（万元）" className="cost-form-item">
                <InputNumber
                  value={data.total_cost}
                  onChange={(v) => onChange?.('total_cost', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('单方造价（元/㎡）', data.unit_cost, ' 元/㎡', true)}
              {renderViewField('总造价（万元）', data.total_cost, ' 万元')}
            </>
          )}
        </div>
      </div>

      <Divider style={{ margin: '16px 0' }} />

      {/* 分项单方造价 */}
      <div className="cost-breakdown">
        <div className="cost-breakdown-title">
          <Text strong>分项单方造价（万元/㎡）</Text>
        </div>

        <div className="cost-row four-col">
          {editMode ? (
            <>
              <Form.Item label="结构" className="cost-form-item">
                <InputNumber
                  value={data.unit_structure}
                  onChange={(v) => onChange?.('unit_structure', v ?? undefined)}
                  min={0}
                  step={0.001}
                  placeholder="0.000"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="安装" className="cost-form-item">
                <InputNumber
                  value={data.unit_installation}
                  onChange={(v) => onChange?.('unit_installation', v ?? undefined)}
                  min={0}
                  step={0.001}
                  placeholder="0.000"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="装修" className="cost-form-item">
                <InputNumber
                  value={data.unit_decoration}
                  onChange={(v) => onChange?.('unit_decoration', v ?? undefined)}
                  min={0}
                  step={0.001}
                  placeholder="0.000"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="措施" className="cost-form-item">
                <InputNumber
                  value={data.unit_measure}
                  onChange={(v) => onChange?.('unit_measure', v ?? undefined)}
                  min={0}
                  step={0.001}
                  placeholder="0.000"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('结构', data.unit_structure, ' 万元/㎡')}
              {renderViewField('安装', data.unit_installation, ' 万元/㎡')}
              {renderViewField('装修', data.unit_decoration, ' 万元/㎡')}
              {renderViewField('措施', data.unit_measure, ' 万元/㎡')}
            </>
          )}
        </div>

        {/* 地上/地下造价占比 */}
        <div className="cost-row two-col">
          {editMode ? (
            <>
              <Form.Item
                label={
                  <span>
                    地上造价占比（%）
                    <Tooltip title="地上部分造价占总造价的比例">
                      <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                    </Tooltip>
                  </span>
                }
                className="cost-form-item"
              >
                <InputNumber
                  value={data.above_cost_ratio}
                  onChange={(v) => onChange?.('above_cost_ratio', v ?? undefined)}
                  min={0}
                  max={100}
                  step={0.1}
                  placeholder="0.0"
                  style={{ width: '100%' }}
                  suffix="%"
                />
              </Form.Item>
              <Form.Item
                label={
                  <span>
                    地下造价占比（%）
                    <Tooltip title="地下部分造价占总造价的比例">
                      <InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} />
                    </Tooltip>
                  </span>
                }
                className="cost-form-item"
              >
                <InputNumber
                  value={data.below_cost_ratio}
                  onChange={(v) => onChange?.('below_cost_ratio', v ?? undefined)}
                  min={0}
                  max={100}
                  step={0.1}
                  placeholder="0.0"
                  style={{ width: '100%' }}
                  suffix="%"
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('地上造价占比', data.above_cost_ratio, '%')}
              {renderViewField('地下造价占比', data.below_cost_ratio, '%')}
            </>
          )}
        </div>
      </div>

      <Divider style={{ margin: '16px 0' }} />

      {/* 经济指标（直接费分项） */}
      <div className="cost-economy">
        <div className="cost-economy-title">
          <Text strong>经济指标 - 直接费分项（元/㎡）</Text>
        </div>

        <div className="cost-row three-col">
          {editMode ? (
            <>
              <Form.Item label="地下结构" className="cost-form-item">
                <InputNumber
                  value={data.underground_structure}
                  onChange={(v) => onChange?.('underground_structure', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="地上结构" className="cost-form-item">
                <InputNumber
                  value={data.above_structure}
                  onChange={(v) => onChange?.('above_structure', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="屋面" className="cost-form-item">
                <InputNumber
                  value={data.roof}
                  onChange={(v) => onChange?.('roof', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('地下结构', data.underground_structure, ' 元/㎡')}
              {renderViewField('地上结构', data.above_structure, ' 元/㎡')}
              {renderViewField('屋面', data.roof, ' 元/㎡')}
            </>
          )}
        </div>

        <div className="cost-row two-col">
          {editMode ? (
            <>
              <Form.Item label="外墙" className="cost-form-item">
                <InputNumber
                  value={data.exterior_wall}
                  onChange={(v) => onChange?.('exterior_wall', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="内墙" className="cost-form-item">
                <InputNumber
                  value={data.interior_wall}
                  onChange={(v) => onChange?.('interior_wall', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('外墙', data.exterior_wall, ' 元/㎡')}
              {renderViewField('内墙', data.interior_wall, ' 元/㎡')}
            </>
          )}
        </div>

        <div className="cost-row four-col">
          {editMode ? (
            <>
              <Form.Item label="楼地面" className="cost-form-item">
                <InputNumber
                  value={data.floor}
                  onChange={(v) => onChange?.('floor', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="电气" className="cost-form-item">
                <InputNumber
                  value={data.electrical}
                  onChange={(v) => onChange?.('electrical', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="给排水" className="cost-form-item">
                <InputNumber
                  value={data.plumbing}
                  onChange={(v) => onChange?.('plumbing', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="暖通" className="cost-form-item">
                <InputNumber
                  value={data.hvac}
                  onChange={(v) => onChange?.('hvac', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('楼地面', data.floor, ' 元/㎡')}
              {renderViewField('电气', data.electrical, ' 元/㎡')}
              {renderViewField('给排水', data.plumbing, ' 元/㎡')}
              {renderViewField('暖通', data.hvac, ' 元/㎡')}
            </>
          )}
        </div>

        <div className="cost-row three-col">
          {editMode ? (
            <>
              <Form.Item label="电梯" className="cost-form-item">
                <InputNumber
                  value={data.elevator}
                  onChange={(v) => onChange?.('elevator', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="消防" className="cost-form-item">
                <InputNumber
                  value={data.fire}
                  onChange={(v) => onChange?.('fire', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
              <Form.Item label="措施费" className="cost-form-item">
                <InputNumber
                  value={data.measures}
                  onChange={(v) => onChange?.('measures', v ?? undefined)}
                  min={0}
                  step={0.01}
                  placeholder="0.00"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </>
          ) : (
            <>
              {renderViewField('电梯', data.elevator, ' 元/㎡')}
              {renderViewField('消防', data.fire, ' 元/㎡')}
              {renderViewField('措施费', data.measures, ' 元/㎡')}
            </>
          )}
        </div>
      </div>
    </div>
  )
}