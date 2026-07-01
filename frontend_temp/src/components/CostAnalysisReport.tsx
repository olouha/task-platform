/**
 * 造价参考价分析报告组件
 * 生成造价参考数据的分析报告
 */

import { Card, Button, Row, Col, Statistic, Table, Tag, Space, Divider, Alert, Select, Spin, Empty } from 'antd'
import {
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  DownloadOutlined,
  DollarOutlined,
  AreaChartOutlined,
  BuildOutlined,
  CalendarOutlined
} from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
import * as XLSX from 'xlsx'
import dayjs from 'dayjs'

interface CostReferenceData {
  category: string
  name: string
  spec: string
  unit_price: number
  pump_price?: number
  non_pump_price?: number
  unit: string
  grade?: string
  period: string
}

interface CostAnalysisReportProps {
  data: CostReferenceData[]
  trendData?: any[]
  selectedPeriod?: string
}

export default function CostAnalysisReport({ data, trendData = [], selectedPeriod }: CostAnalysisReportProps) {
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [selectedView, setSelectedView] = useState<'overview' | 'category' | 'period'>('overview')

  useEffect(() => {
    generateAnalysis()
  }, [data, trendData])

  const generateAnalysis = () => {
    setLoading(true)

    if (!data || data.length === 0) {
      setAnalysisData(null)
      setLoading(false)
      return
    }

    // 获取所有分类和时期
    const categoriesSet = new Set<string>()
    const periodsSet = new Set<string>()

    data.forEach((d: CostReferenceData) => {
      categoriesSet.add(d.category || '其他')
      if (d.period) periodsSet.add(d.period)
    })

    const categories = Array.from(categoriesSet)
    const periods = Array.from(periodsSet).sort()

    // 按分类分析
    const categoryMap = new Map<string, { count: number; prices: number[] }>()
    data.forEach((d: CostReferenceData) => {
      const cat = d.category || '其他'
      if (!categoryMap.has(cat)) {
        categoryMap.set(cat, { count: 0, prices: [] })
      }
      const info = categoryMap.get(cat)!
      info.count++
      const price = d.unit_price || d.pump_price || d.non_pump_price || 0
      if (price > 0) info.prices.push(price)
    })

    const by_category = Array.from(categoryMap.entries()).map(([category, info]) => {
      const prices = info.prices.filter(p => p > 0)
      return {
        category,
        count: info.count,
        avg_price: prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0,
        min_price: prices.length > 0 ? Math.min(...prices) : 0,
        max_price: prices.length > 0 ? Math.max(...prices) : 0
      }
    })

    // 按时期分析
    const periodMap = new Map<string, { count: number; prices: number[] }>()
    data.forEach((d: CostReferenceData) => {
      const period = d.period || '未知'
      if (!periodMap.has(period)) {
        periodMap.set(period, { count: 0, prices: [] })
      }
      const info = periodMap.get(period)!
      info.count++
      const price = d.unit_price || d.pump_price || d.non_pump_price || 0
      if (price > 0) info.prices.push(price)
    })

    const by_period = Array.from(periodMap.entries())
      .map(([period, info]) => {
        const prices = info.prices.filter(p => p > 0)
        return {
          period,
          count: info.count,
          avg_price: prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0
        }
      })
      .sort((a, b) => a.period.localeCompare(b.period))

    // 分类分布
    const totalCount = data.length
    const category_distribution = categories.map(cat => {
      const count = data.filter((d: CostReferenceData) => (d.category || '其他') === cat).length
      return {
        category: cat,
        count,
        percentage: Math.round(count / totalCount * 1000) / 10
      }
    }).sort((a, b) => b.count - a.count)

    setAnalysisData({
      summary: {
        total_items: data.length,
        categories,
        periods
      },
      by_category,
      by_period,
      category_distribution,
      trend: trendData
    })

    setLoading(false)
  }

  const handleExportReport = () => {
    if (!analysisData) return

    const wb = XLSX.utils.book_new()

    // 汇总信息
    const summaryData = [
      ['指标', '数值'],
      ['总项目数', analysisData.summary.total_items],
      ['分类数量', analysisData.summary.categories.length],
      ['时期数量', analysisData.summary.periods.length]
    ]
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryData)
    XLSX.utils.book_append_sheet(wb, wsSummary, '汇总信息')

    // 分类分析
    const categoryData = analysisData.by_category.map((c: any) => ({
      '分类': c.category,
      '项目数': c.count,
      '平均价格': `¥${c.avg_price}`,
      '最低价格': `¥${c.min_price}`,
      '最高价格': `¥${c.max_price}`
    }))
    const wsCategory = XLSX.utils.json_to_sheet(categoryData)
    XLSX.utils.book_append_sheet(wb, wsCategory, '分类分析')

    XLSX.writeFile(wb, `造价分析报告_${dayjs().format('YYYY-MM-DD')}.xlsx`)
  }

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>生成分析报告中...</div>
        </div>
      </Card>
    )
  }

  if (!analysisData || data.length === 0) {
    return (
      <Card>
        <Empty description="暂无数据可分析" />
      </Card>
    )
  }

  const categoryColumns: any[] = [
    { title: '分类', dataIndex: 'category', key: 'category' },
    { title: '项目数', dataIndex: 'count', key: 'count', align: 'center' as const },
    { title: '平均价格', dataIndex: 'avg_price', key: 'avg_price', render: (v: number) => `¥${v}`, align: 'right' as const },
    { title: '价格区间', key: 'range', render: (_: any, r: any) => `¥${r.min_price} - ¥${r.max_price}`, align: 'right' as const }
  ]

  const periodColumns: any[] = [
    { title: '时期', dataIndex: 'period', key: 'period' },
    { title: '项目数', dataIndex: 'count', key: 'count', align: 'center' as const },
    { title: '平均价格', dataIndex: 'avg_price', key: 'avg_price', render: (v: number) => `¥${v}`, align: 'right' as const }
  ]

  return (
    <div>
      {/* 报告标题和操作栏 */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>造价参考价分析报告</span>
            {selectedPeriod && <Tag color="blue">{selectedPeriod}</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Select
              value={selectedView}
              onChange={setSelectedView}
              style={{ width: 120 }}
            >
              <Select.Option value="overview">总览</Select.Option>
              <Select.Option value="category">分类分析</Select.Option>
              <Select.Option value="period">时期分析</Select.Option>
            </Select>
            <Button icon={<DownloadOutlined />} onClick={handleExportReport}>
              导出报告
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {/* 总览视图 */}
        {selectedView === 'overview' && (
          <>
            {/* 汇总统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic title="总项目数" value={analysisData.summary.total_items} suffix="项" />
              </Col>
              <Col span={6}>
                <Statistic title="分类数量" value={analysisData.summary.categories.length} suffix="个" />
              </Col>
              <Col span={6}>
                <Statistic title="时期数量" value={analysisData.summary.periods.length} suffix="个" />
              </Col>
              <Col span={6}>
                <Statistic
                  title="当前时期"
                  value={analysisData.summary.periods[analysisData.summary.periods.length - 1] || '-'}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
            </Row>

            <Divider />

            {/* 分类分布 */}
            <div style={{ marginBottom: 24 }}>
              <h4><BuildOutlined /> 分类分布</h4>
              <Table
                dataSource={analysisData.category_distribution.map((d: any, i: number) => ({ ...d, key: i }))}
                columns={[
                  { title: '分类', dataIndex: 'category', key: 'category' },
                  { title: '项目数', dataIndex: 'count', key: 'count', align: 'center' as const },
                  { title: '占比', dataIndex: 'percentage', key: 'percentage', render: (v: number) => `${v}%`, align: 'center' as const }
                ]}
                pagination={false}
                size="small"
              />
            </div>

            <Divider />

            {/* 分类价格概览 */}
            <div>
              <h4><BarChartOutlined /> 分类价格概览</h4>
              <Table
                dataSource={analysisData.by_category.map((c: any, i: number) => ({ ...c, key: i }))}
                columns={categoryColumns}
                pagination={false}
                size="small"
              />
            </div>
          </>
        )}

        {/* 分类分析视图 */}
        {selectedView === 'category' && (
          <>
            <h4><BuildOutlined /> 分类详细分析</h4>
            <Table
              dataSource={analysisData.by_category.map((c: any, i: number) => ({ ...c, key: i }))}
              columns={categoryColumns}
              pagination={false}
              size="small"
            />
          </>
        )}

        {/* 时期分析视图 */}
        {selectedView === 'period' && (
          <>
            <h4><CalendarOutlined /> 时期价格趋势</h4>
            {analysisData.trend && analysisData.trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={analysisData.trend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="avg_price" stroke="#4A86C8" strokeWidth={2} name="平均价格" />
                </LineChart>
              </ResponsiveContainer>
            ) : analysisData.by_period.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={analysisData.by_period}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="avg_price" fill="#4A86C8" name="平均价格" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Alert message="暂无趋势数据" type="info" showIcon />
            )}

            <Divider />

            <h4>时期明细</h4>
            <Table
              dataSource={analysisData.by_period.map((p: any, i: number) => ({ ...p, key: i }))}
              columns={periodColumns}
              pagination={false}
              size="small"
            />
          </>
        )}
      </Card>
    </div>
  )
}
