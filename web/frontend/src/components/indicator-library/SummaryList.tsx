/**
 * 指标库摘要列表组件
 * 展示项目列表，支持多维度筛选
 */
import { useState, useMemo, useCallback } from 'react'
import { List, Input, Select, Space, Tag, Button, Card, Typography, Tooltip } from 'antd'
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
  HomeOutlined,
  EnvironmentOutlined,
  CalendarOutlined,
  BankOutlined,
} from '@ant-design/icons'
import './SummaryList.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 指标库摘要项 */
export interface IndicatorLibrarySummary {
  id: string
  name: string
  category: string
  location: string
  delivery_type?: string
  structure?: string
  start_date?: string
  end_date?: string
  area_total?: number
  unit_cost?: number
  verified?: boolean
  created_at?: string
  updated_at?: string
}

/** 筛选条件 */
export interface SummaryListFilters {
  category?: string
  location?: string
  delivery_type?: string
  start_date_from?: string
  start_date_to?: string
  end_date_from?: string
  end_date_to?: string
  search_text?: string
}

/** 组件 Props */
export interface SummaryListProps {
  data: IndicatorLibrarySummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  filters: SummaryListFilters
  onFilterChange: (filters: SummaryListFilters) => void
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
]

/** 交付类型选项 */
const DELIVERY_TYPE_OPTIONS = [
  { value: '毛坯交付', label: '毛坯交付' },
  { value: '精装修', label: '精装修' },
  { value: '带装修', label: '带装修' },
  { value: '其他', label: '其他' },
]

/** 地区选项 */
const LOCATION_OPTIONS = [
  { value: '一线城市', label: '一线城市' },
  { value: '二线城市', label: '二线城市' },
  { value: '三线城市', label: '三线城市' },
  { value: '四线城市', label: '四线城市' },
  { value: '其他', label: '其他' },
]

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 格式化日期显示（YYYY-MM 格式）
 */
const formatDate = (dateStr?: string): string => {
  if (!dateStr) return '-'
  // 如果是完整的日期字符串，提取 YYYY-MM 部分
  if (dateStr.length >= 7) {
    return dateStr.substring(0, 7)
  }
  return dateStr
}

/**
 * 格式化数字（千分位）
 */
const formatNumber = (num?: number): string => {
  if (num === undefined || num === null) return '-'
  return num.toLocaleString('zh-CN')
}

/**
 * 生成月份选择选项（近10年）
 */
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
// 组件定义
// ============================================================================

const { Text } = Typography

export default function SummaryList({
  data,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
}: SummaryListProps) {
  // 高级筛选展开状态
  const [advancedFiltersVisible, setAdvancedFiltersVisible] = useState(false)

  // 本地搜索文本
  const [localSearchText, setLocalSearchText] = useState(filters.search_text || '')

  // -------------------------------------------------------------------------
  // 计算属性
  // -------------------------------------------------------------------------

  /** 活跃的筛选标签 */
  const activeFilterTags = useMemo(() => {
    const tags: { key: string; label: string; value: string }[] = []

    if (filters.search_text) {
      tags.push({ key: 'search_text', label: '搜索', value: filters.search_text })
    }
    if (filters.category) {
      tags.push({ key: 'category', label: '业态', value: filters.category })
    }
    if (filters.delivery_type) {
      tags.push({ key: 'delivery_type', label: '交付类型', value: filters.delivery_type })
    }
    if (filters.location) {
      tags.push({ key: 'location', label: '地区', value: filters.location })
    }
    if (filters.start_date_from) {
      tags.push({ key: 'start_date_from', label: '开工日期≥', value: formatDate(filters.start_date_from) })
    }
    if (filters.start_date_to) {
      tags.push({ key: 'start_date_to', label: '开工日期≤', value: formatDate(filters.start_date_to) })
    }
    if (filters.end_date_from) {
      tags.push({ key: 'end_date_from', label: '竣工日期≥', value: formatDate(filters.end_date_from) })
    }
    if (filters.end_date_to) {
      tags.push({ key: 'end_date_to', label: '竣工日期≤', value: formatDate(filters.end_date_to) })
    }

    return tags
  }, [filters])

  // -------------------------------------------------------------------------
  // 事件处理
  // -------------------------------------------------------------------------

  /**
   * 本地搜索防抖
   */
  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value
      setLocalSearchText(value)

      // 防抖更新父组件筛选条件
      const timer = setTimeout(() => {
        onFilterChange({ ...filters, search_text: value || undefined })
      }, 300)

      return () => clearTimeout(timer)
    },
    [filters, onFilterChange]
  )

  /**
   * 筛选条件变更
   */
  const handleFilterChange = useCallback(
    (key: keyof SummaryListFilters, value: string | undefined) => {
      onFilterChange({ ...filters, [key]: value })
    },
    [filters, onFilterChange]
  )

  /**
   * 移除单个筛选标签
   */
  const handleRemoveTag = useCallback(
    (key: string) => {
      const newFilters = { ...filters }
      delete newFilters[key as keyof SummaryListFilters]
      if (key === 'search_text') {
        setLocalSearchText('')
      }
      onFilterChange(newFilters)
    },
    [filters, onFilterChange]
  )

  /**
   * 清除所有筛选
   */
  const handleClearFilters = useCallback(() => {
    setLocalSearchText('')
    onFilterChange({})
  }, [onFilterChange])

  /**
   * 切换高级筛选展开状态
   */
  const toggleAdvancedFilters = useCallback(() => {
    setAdvancedFiltersVisible((prev) => !prev)
  }, [])

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------

  /**
   * 渲染列表项
   */
  const renderItem = (item: IndicatorLibrarySummary) => {
    const isSelected = selectedId === item.id

    return (
      <List.Item
        key={item.id}
        className={`summary-list-item ${isSelected ? 'selected' : ''}`}
        onClick={() => onSelect(item.id)}
      >
        <div className="summary-list-item-content">
          {/* 标题行 */}
          <div className="summary-list-item-header">
            <span className="summary-list-item-name">
              <HomeOutlined style={{ marginRight: 6, color: '#1890ff' }} />
              {item.name}
            </span>
            {item.verified && (
              <Tag color="green" style={{ marginLeft: 8 }}>
                已审核
              </Tag>
            )}
          </div>

          {/* 信息行 */}
          <div className="summary-list-item-info">
            <span className="summary-list-item-tag">
              <BankOutlined style={{ marginRight: 4 }} />
              {item.category}
            </span>
            <span className="summary-list-item-tag">
              <EnvironmentOutlined style={{ marginRight: 4 }} />
              {item.location}
            </span>
            {item.delivery_type && (
              <span className="summary-list-item-tag">{item.delivery_type}</span>
            )}
          </div>

          {/* 日期和面积行 */}
          <div className="summary-list-item-meta">
            {(item.start_date || item.end_date) && (
              <span className="summary-list-item-dates">
                <CalendarOutlined style={{ marginRight: 4 }} />
                {formatDate(item.start_date)} ~ {formatDate(item.end_date)}
              </span>
            )}
            {item.area_total && (
              <span className="summary-list-item-area">
                {formatNumber(item.area_total)} ㎡
              </span>
            )}
          </div>

          {/* 单方造价 */}
          {item.unit_cost !== undefined && item.unit_cost !== null && (
            <div className="summary-list-item-cost">
              <Text type="secondary">单方造价：</Text>
              <Text strong style={{ color: '#f5222d' }}>
                {formatNumber(item.unit_cost)} 元/㎡
              </Text>
            </div>
          )}
        </div>
      </List.Item>
    )
  }

  /**
   * 渲染空状态
   */
  const renderEmpty = () => (
    <div className="summary-list-empty">
      <Text type="secondary">暂无数据</Text>
      {activeFilterTags.length > 0 && (
        <Button
          type="link"
          size="small"
          onClick={handleClearFilters}
          icon={<ClearOutlined />}
        >
          清除筛选
        </Button>
      )}
    </div>
  )

  return (
    <div className="summary-list-container">
      {/* 基础筛选区域 */}
      <div className="summary-list-filters">
        <Input
          placeholder="搜索项目名称"
          prefix={<SearchOutlined />}
          value={localSearchText}
          onChange={handleSearchChange}
          allowClear
          className="summary-list-search"
        />

        <Space wrap size="small">
          <Select
            placeholder="业态"
            style={{ width: 100 }}
            allowClear
            value={filters.category}
            onChange={(v) => handleFilterChange('category', v)}
            options={CATEGORY_OPTIONS}
          />
          <Select
            placeholder="交付类型"
            style={{ width: 110 }}
            allowClear
            value={filters.delivery_type}
            onChange={(v) => handleFilterChange('delivery_type', v)}
            options={DELIVERY_TYPE_OPTIONS}
          />
          <Tooltip title="高级筛选">
            <Button
              icon={<FilterOutlined />}
              onClick={toggleAdvancedFilters}
              type={advancedFiltersVisible ? 'primary' : 'default'}
            />
          </Tooltip>
        </Space>
      </div>

      {/* 高级筛选区域 */}
      {advancedFiltersVisible && (
        <div className="summary-list-advanced-filters">
          <div className="summary-list-filter-row">
            <span className="summary-list-filter-label">地区：</span>
            <Select
              placeholder="选择地区"
              style={{ width: 120 }}
              allowClear
              value={filters.location}
              onChange={(v) => handleFilterChange('location', v)}
              options={LOCATION_OPTIONS}
            />
          </div>

          <div className="summary-list-filter-row">
            <span className="summary-list-filter-label">开工日期：</span>
            <Space size="small">
              <Select
                placeholder="起始"
                style={{ width: 110 }}
                allowClear
                value={filters.start_date_from}
                onChange={(v) => handleFilterChange('start_date_from', v)}
                options={MONTH_OPTIONS}
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
              <span>至</span>
              <Select
                placeholder="结束"
                style={{ width: 110 }}
                allowClear
                value={filters.start_date_to}
                onChange={(v) => handleFilterChange('start_date_to', v)}
                options={MONTH_OPTIONS}
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
            </Space>
          </div>

          <div className="summary-list-filter-row">
            <span className="summary-list-filter-label">竣工日期：</span>
            <Space size="small">
              <Select
                placeholder="起始"
                style={{ width: 110 }}
                allowClear
                value={filters.end_date_from}
                onChange={(v) => handleFilterChange('end_date_from', v)}
                options={MONTH_OPTIONS}
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
              <span>至</span>
              <Select
                placeholder="结束"
                style={{ width: 110 }}
                allowClear
                value={filters.end_date_to}
                onChange={(v) => handleFilterChange('end_date_to', v)}
                options={MONTH_OPTIONS}
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                }
              />
            </Space>
          </div>
        </div>
      )}

      {/* 活跃筛选标签 */}
      {activeFilterTags.length > 0 && (
        <div className="summary-list-active-filters">
          <Space wrap size="small">
            {activeFilterTags.map((tag) => (
              <Tag
                key={tag.key}
                closable
                onClose={() => handleRemoveTag(tag.key)}
                className="summary-list-filter-tag"
              >
                {tag.label}: {tag.value}
              </Tag>
            ))}
            <Button
              type="link"
              size="small"
              onClick={handleClearFilters}
              icon={<ClearOutlined />}
              className="summary-list-clear-btn"
            >
              清除全部
            </Button>
          </Space>
        </div>
      )}

      {/* 列表统计 */}
      <div className="summary-list-stat">
        <Text type="secondary">
          共 {data.length} 条记录
        </Text>
      </div>

      {/* 列表内容 */}
      <div className="summary-list-content">
        {data.length === 0 ? (
          renderEmpty()
        ) : (
          <List
            dataSource={data}
            renderItem={renderItem}
            locale={{ emptyText: renderEmpty() }}
          />
        )}
      </div>
    </div>
  )
}