/**
 * 基础信息Section组件
 * 展示和编辑项目的基础信息（名称、业态、地区、结构、日期、层数、面积）
 */
import React from 'react'
import { Form, Input, InputNumber, Select, Space, Typography } from 'antd'
import { HomeOutlined, EnvironmentOutlined, CalendarOutlined, BuildOutlined } from '@ant-design/icons'
import './BasicInfoSection.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 基础信息数据 */
export interface BasicInfoData {
  // 基本信息
  name?: string
  category?: string
  location?: string
  structure?: string
  delivery_type?: string
  // 日期
  start_date?: string
  end_date?: string
  // 层数和高度
  floor_above?: number
  floor_below?: number
  height?: number
  // 面积
  area_total?: number
  area_above?: number
  area_below?: number
  // 来源信息
  source?: string
  source_file?: string
  remarks?: string
}

export interface BasicInfoSectionProps {
  data: BasicInfoData
  editMode: boolean
  onChange?: (field: keyof BasicInfoData, value: string | number | undefined) => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** 业态类型选项 */
const CATEGORY_OPTIONS = [
  { value: '住宅', label: '住宅' },
  { value: '商业', label: '商业' },
  { value: '办公', label: '办公' },
  { value: '工业', label: '工业' },
  { value: '教育', label: '教育' },
  { value: '医疗', label: '医疗' },
  { value: '文体', label: '文体' },
  { value: '其他', label: '其他' },
]

/** 地区选项 */
const LOCATION_OPTIONS = [
  { value: '一线城市', label: '一线城市' },
  { value: '二线城市', label: '二线城市' },
  { value: '三线城市', label: '三线城市' },
  { value: '四线城市', label: '四线城市' },
  { value: '县级市', label: '县级市' },
  { value: '县城', label: '县城' },
  { value: '乡镇', label: '乡镇' },
  { value: '其他', label: '其他' },
]

/** 结构类型选项 */
const STRUCTURE_OPTIONS = [
  { value: '框架结构', label: '框架结构' },
  { value: '框架-剪力墙结构', label: '框架-剪力墙结构' },
  { value: '剪力墙结构', label: '剪力墙结构' },
  { value: '框架-核心筒结构', label: '框架-核心筒结构' },
  { value: '钢结构', label: '钢结构' },
  { value: '砖混结构', label: '砖混结构' },
  { value: '木结构', label: '木结构' },
  { value: '其他', label: '其他' },
]

/** 交付类型选项 */
const DELIVERY_TYPE_OPTIONS = [
  { value: '毛坯交付', label: '毛坯交付' },
  { value: '精装修', label: '精装修' },
  { value: '带装修', label: '带装修' },
  { value: '其他', label: '其他' },
]

/** 生成月份选择选项（近10年） */
const generateMonthOptions = (): { value: string; label: string }[] => {
  const options: { value: string; label: string }[] = []
  const now = new Date()
  const currentYear = now.getFullYear()

  for (let year = currentYear; year >= currentYear - 10; year--) {
    for (let month = 12; month >= 1; month--) {
      const monthStr = month.toString().padStart(2, '0')
      const value = `${year}-${monthStr}`
      options.push({ value, label: value })
    }
  }

  return options
}

const MONTH_OPTIONS = generateMonthOptions()

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化数字（千分位）
 */
const formatNumber = (num?: number): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString('zh-CN')
}

// ============================================================================
// 组件定义
// ============================================================================

const { Text } = Typography

export default function BasicInfoSection({
  data,
  editMode,
  onChange,
}: BasicInfoSectionProps) {
  /**
   * 渲染查看模式下的字段
   */
  const renderViewField = (
    label: string,
    value: string | number | undefined,
    suffix?: string,
    icon?: React.ReactNode
  ) => (
    <div className="basic-info-field">
      <span className="basic-info-label">{icon}{label}</span>
      <span className="basic-info-value">
        {value !== undefined && value !== null && value !== ''
          ? `${formatNumber(value as number)}${suffix || ''}`
          : '-'}
      </span>
    </div>
  )

  /**
   * 处理输入变更
   */
  const handleChange = (field: keyof BasicInfoData) => (
    e: React.ChangeEvent<HTMLInputElement> | string | number | undefined
  ) => {
    if (!onChange) return
    let value: string | number | undefined

    if (typeof e === 'object' && 'target' in (e as any)) {
      value = (e as React.ChangeEvent<HTMLInputElement>).target.value
    } else if (typeof e === 'string' || typeof e === 'number') {
      value = e
    } else {
      value = undefined
    }

    onChange(field, value)
  }

  return (
    <div className="basic-info-section">
      {/* 基本信息区域 */}
      <div className="basic-info-row">
        {editMode ? (
          <>
            <Form.Item
              label="项目名称"
              className="basic-info-form-item full-width"
            >
              <Input
                value={data.name}
                onChange={(e) => onChange?.('name', e.target.value)}
                placeholder="请输入项目名称"
              />
            </Form.Item>
          </>
        ) : (
          <div className="basic-info-title-row">
            <HomeOutlined style={{ fontSize: 20, color: '#1890ff', marginRight: 8 }} />
            <Text strong style={{ fontSize: 16 }}>{data.name || '-'}</Text>
          </div>
        )}
      </div>

      {/* 第二行：业态、地区、结构 */}
      <div className="basic-info-row three-col">
        {editMode ? (
          <>
            <Form.Item label="业态" className="basic-info-form-item">
              <Select
                value={data.category}
                onChange={(v) => onChange?.('category', v)}
                options={CATEGORY_OPTIONS}
                placeholder="请选择业态"
                allowClear
              />
            </Form.Item>
            <Form.Item label="地区" className="basic-info-form-item">
              <Select
                value={data.location}
                onChange={(v) => onChange?.('location', v)}
                options={LOCATION_OPTIONS}
                placeholder="请选择地区"
                allowClear
              />
            </Form.Item>
            <Form.Item label="结构类型" className="basic-info-form-item">
              <Select
                value={data.structure}
                onChange={(v) => onChange?.('structure', v)}
                options={STRUCTURE_OPTIONS}
                placeholder="请选择结构类型"
                allowClear
              />
            </Form.Item>
          </>
        ) : (
          <>
            {renderViewField('业态', data.category)}
            {renderViewField('地区', data.location)}
            {renderViewField('结构', data.structure)}
          </>
        )}
      </div>

      {/* 第三行：交付类型、开工日期、竣工日期 */}
      <div className="basic-info-row three-col">
        {editMode ? (
          <>
            <Form.Item label="交付类型" className="basic-info-form-item">
              <Select
                value={data.delivery_type}
                onChange={(v) => onChange?.('delivery_type', v)}
                options={DELIVERY_TYPE_OPTIONS}
                placeholder="请选择交付类型"
                allowClear
              />
            </Form.Item>
            <Form.Item label="开工日期" className="basic-info-form-item">
              <Select
                value={data.start_date}
                onChange={(v) => onChange?.('start_date', v)}
                options={MONTH_OPTIONS}
                placeholder="YYYY-MM"
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>
            <Form.Item label="竣工日期" className="basic-info-form-item">
              <Select
                value={data.end_date}
                onChange={(v) => onChange?.('end_date', v)}
                options={MONTH_OPTIONS}
                placeholder="YYYY-MM"
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
            </Form.Item>
          </>
        ) : (
          <>
            {renderViewField('交付类型', data.delivery_type)}
            {renderViewField('开工日期', data.start_date)}
            {renderViewField('竣工日期', data.end_date)}
          </>
        )}
      </div>

      {/* 第四行：地上层数、地下层数、檐高 */}
      <div className="basic-info-row three-col">
        {editMode ? (
          <>
            <Form.Item label="地上层数" className="basic-info-form-item">
              <InputNumber
                value={data.floor_above}
                onChange={(v) => onChange?.('floor_above', v ?? undefined)}
                min={0}
                max={200}
                placeholder="层"
                style={{ width: '100%' }}
              />
            </Form.Item>
            <Form.Item label="地下层数" className="basic-info-form-item">
              <InputNumber
                value={data.floor_below}
                onChange={(v) => onChange?.('floor_below', v ?? undefined)}
                min={0}
                max={20}
                placeholder="层"
                style={{ width: '100%' }}
              />
            </Form.Item>
            <Form.Item label="檐高(m)" className="basic-info-form-item">
              <InputNumber
                value={data.height}
                onChange={(v) => onChange?.('height', v ?? undefined)}
                min={0}
                max={1000}
                step={0.1}
                placeholder="m"
                style={{ width: '100%' }}
              />
            </Form.Item>
          </>
        ) : (
          <>
            {renderViewField('地上层数', data.floor_above, '层')}
            {renderViewField('地下层数', data.floor_below, '层')}
            {renderViewField('檐高', data.height, 'm')}
          </>
        )}
      </div>

      {/* 第五行：总建筑面积、地上面积、地下面积 */}
      <div className="basic-info-row three-col">
        {editMode ? (
          <>
            <Form.Item label="总建筑面积" className="basic-info-form-item">
              <InputNumber
                value={data.area_total}
                onChange={(v) => onChange?.('area_total', v ?? undefined)}
                min={0}
                step={1}
                placeholder="㎡"
                style={{ width: '100%' }}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value?.replace(/,/g, '') as unknown as number}
              />
            </Form.Item>
            <Form.Item label="地上面积" className="basic-info-form-item">
              <InputNumber
                value={data.area_above}
                onChange={(v) => onChange?.('area_above', v ?? undefined)}
                min={0}
                step={1}
                placeholder="㎡"
                style={{ width: '100%' }}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value?.replace(/,/g, '') as unknown as number}
              />
            </Form.Item>
            <Form.Item label="地下面积" className="basic-info-form-item">
              <InputNumber
                value={data.area_below}
                onChange={(v) => onChange?.('area_below', v ?? undefined)}
                min={0}
                step={1}
                placeholder="㎡"
                style={{ width: '100%' }}
                formatter={(value) => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                parser={(value) => value?.replace(/,/g, '') as unknown as number}
              />
            </Form.Item>
          </>
        ) : (
          <>
            {renderViewField('总建筑面积', data.area_total, '㎡')}
            {renderViewField('地上面积', data.area_above, '㎡')}
            {renderViewField('地下面积', data.area_below, '㎡')}
          </>
        )}
      </div>

      {/* 来源信息（仅查看模式） */}
      {!editMode && (data.source || data.source_file) && (
        <div className="basic-info-source">
          {data.source && (
            <Text type="secondary" className="basic-info-source-text">
              来源: {data.source}
              {data.source_file && ` (${data.source_file})`}
            </Text>
          )}
        </div>
      )}

      {/* 编辑模式下的备注 */}
      {editMode && (
        <div className="basic-info-row">
          <Form.Item label="备注" className="basic-info-form-item full-width">
            <Input.TextArea
              value={data.remarks}
              onChange={(e) => onChange?.('remarks', e.target.value)}
              placeholder="请输入备注信息"
              rows={2}
            />
          </Form.Item>
        </div>
      )}
    </div>
  )
}