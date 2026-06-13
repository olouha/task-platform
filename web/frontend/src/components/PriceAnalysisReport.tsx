/**
 * 价格监控分析报告组件
 * 生成价格数据的分析报告
 * 基于AI生成行业报告方法论优化
 */

import { Card, Button, Row, Col, Statistic, Table, Tag, Space, Divider, Alert, Select, Spin, Empty, Typography, Tooltip as AntdTooltip } from 'antd'
import {
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
  BarChartOutlined,
  DownloadOutlined,
  CalendarOutlined,
  DollarOutlined,
  AreaChartOutlined,
  ThunderboltOutlined,
  ProfileOutlined,
  TrophyOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  LineOutlined,
  SwapOutlined
} from '@ant-design/icons'
import { useState, useEffect, useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, LineChart, Line, ComposedChart } from 'recharts'
import * as XLSX from 'xlsx'
import dayjs from 'dayjs'

const { Text, Paragraph } = Typography

interface PriceData {
  date?: string
  time?: string
  material_name?: string
  spec?: string
  material_type?: string
  brand?: string
  price?: number
  price_change?: string
  region?: string
}

interface TrendData {
  date: string
  avg_price: number
  min_price: number
  max_price: number
  count: number
  by_type?: Record<string, { avg: number; min: number; max: number; count: number }>
}

interface PriceAnalysisReportProps {
  data: PriceData[]
  trendData?: TrendData[]
  dateRange?: [string, string]
  comparisonData?: PriceData[]  // 对比期数据
}

const COLORS = ['#16325C', '#4A86C8', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
const COLOR_UP = '#EF4444'
const COLOR_DOWN = '#10B981'

// 生成摘要文本
const generateSummaryText = (summary: any, materialStats: any[], trendData: TrendData[], comparisonSummary?: any): string => {
  if (!summary || !trendData || trendData.length < 2) return ''

  const latestTrend = trendData[trendData.length - 1]
  const previousTrend = trendData[trendData.length - 2]

  // 计算环比变化
  const momChange = latestTrend.avg_price - previousTrend.avg_price
  const momChangeRate = previousTrend.avg_price > 0 ? (momChange / previousTrend.avg_price * 100) : 0
  const trendDirection = momChange > 0 ? '上涨' : momChange < 0 ? '下跌' : '平稳'

  // 获取主要品名
  const mainMaterial = materialStats.length > 0 ? materialStats[0] : null

  // 生成摘要
  let summaryText = `${dayjs().format('YYYY年M月')}，烟台钢筋市场整体呈现${trendDirection}态势。`
  summaryText += `本期均价${latestTrend.avg_price.toLocaleString()}元/吨，环比${momChange > 0 ? '上涨' : '下跌'}${Math.abs(momChange).toFixed(0)}元（${momChangeRate > 0 ? '+' : ''}${momChangeRate.toFixed(2)}%）。`

  if (mainMaterial) {
    summaryText += `主流品名${mainMaterial.name}均价${mainMaterial.avg_price}元/吨，`
    summaryText += `价格区间${mainMaterial.min_price}-${mainMaterial.max_price}元/吨。`
  }

  // 供应需求简评（基于价格波动判断）
  const volatility = latestTrend.max_price - latestTrend.min_price
  const volatilityRate = volatility / latestTrend.avg_price * 100
  if (volatilityRate > 5) {
    summaryText += `市场波动较大（振幅${volatilityRate.toFixed(1)}%），价格分化明显。`
  } else {
    summaryText += `市场波动较小，行情相对稳定。`
  }

  // 后市研判（简单规则）
  const last7Days = trendData.slice(-7)
  if (last7Days.length >= 3) {
    const trendSlope = (last7Days[last7Days.length - 1].avg_price - last7Days[0].avg_price) / last7Days.length
    if (trendSlope > 10) {
      summaryText += `近期价格呈上涨趋势，预计短期内仍有支撑。`
    } else if (trendSlope < -10) {
      summaryText += `近期价格呈下跌趋势，需关注需求变化。`
    }
  }

  return summaryText
}

// 计算品牌排名
const calculateBrandRanking = (data: PriceData[]): any[] => {
  const brandMap = new Map<string, { count: number; total: number; prices: number[] }>()
  data.forEach(d => {
    const brand = d.brand || '未知'
    if (!brandMap.has(brand)) {
      brandMap.set(brand, { count: 0, total: 0, prices: [] })
    }
    const info = brandMap.get(brand)!
    info.count++
    if (d.price && d.price > 0) {
      info.total += d.price
      info.prices.push(d.price)
    }
  })

  return Array.from(brandMap.entries())
    .map(([name, info]) => ({
      name,
      count: info.count,
      avg_price: info.prices.length > 0 ? Math.round(info.total / info.prices.length) : 0,
      min_price: info.prices.length > 0 ? Math.min(...info.prices) : 0,
      max_price: info.prices.length > 0 ? Math.max(...info.prices) : 0
    }))
    .sort((a, b) => b.avg_price - a.avg_price)
}

// 计算规格价格对比
const calculateSpecComparison = (data: PriceData[]): any[] => {
  const specMap = new Map<string, { count: number; total: number; prices: number[] }>()
  data.forEach(d => {
    const spec = d.spec || '未知'
    if (!specMap.has(spec)) {
      specMap.set(spec, { count: 0, total: 0, prices: [] })
    }
    const info = specMap.get(spec)!
    info.count++
    if (d.price && d.price > 0) {
      info.total += d.price
      info.prices.push(d.price)
    }
  })

  return Array.from(specMap.entries())
    .map(([spec, info]) => ({
      spec,
      count: info.count,
      avg_price: info.prices.length > 0 ? Math.round(info.total / info.prices.length) : 0,
      min_price: info.prices.length > 0 ? Math.min(...info.prices) : 0,
      max_price: info.prices.length > 0 ? Math.max(...info.prices) : 0
    }))
    .sort((a, b) => {
      // 按规格数字排序
      const numA = parseInt(a.spec.replace(/[^0-9]/g, '')) || 0
      const numB = parseInt(b.spec.replace(/[^0-9]/g, '')) || 0
      return numA - numB
    })
}

export default function PriceAnalysisReport({ data, trendData = [], comparisonData }: PriceAnalysisReportProps) {
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [selectedView, setSelectedView] = useState<'summary' | 'overview' | 'trend' | 'distribution' | 'brand' | 'spec'>('summary')

  // 计算对比数据
  const comparisonSummary = useMemo(() => {
    if (!comparisonData || comparisonData.length === 0) return null
    const prices = comparisonData.map(d => d.price || 0).filter(p => p > 0)
    return {
      total_records: comparisonData.length,
      avg_price: prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0,
      min_price: prices.length > 0 ? Math.min(...prices) : 0,
      max_price: prices.length > 0 ? Math.max(...prices) : 0
    }
  }, [comparisonData])

  useEffect(() => {
    generateAnalysis()
  }, [data, trendData, comparisonData])

  const generateAnalysis = () => {
    setLoading(true)

    if (!data || data.length === 0) {
      setAnalysisData(null)
      setLoading(false)
      return
    }

    // 计算汇总数据
    const prices = data.map(d => d.price || 0).filter(p => p > 0)
    const total_records = data.length
    const avg_price = prices.length > 0 ? prices.reduce((a, b) => a + b, 0) / prices.length : 0
    const min_price = prices.length > 0 ? Math.min(...prices) : 0
    const max_price = prices.length > 0 ? Math.max(...prices) : 0
    const price_range = max_price - min_price

    // 计算标准差
    const variance = prices.length > 0 ? prices.reduce((sum, price) => sum + Math.pow(price - avg_price, 2), 0) / prices.length : 0
    const std_deviation = Math.sqrt(variance)

    // 按材料名称分组
    const materialMap = new Map<string, { count: number; total: number; prices: number[] }>()
    data.forEach(d => {
      const name = d.material_name || '未知'
      if (!materialMap.has(name)) {
        materialMap.set(name, { count: 0, total: 0, prices: [] })
      }
      const info = materialMap.get(name)!
      info.count++
      if (d.price && d.price > 0) {
        info.total += d.price
        info.prices.push(d.price)
      }
    })

    const by_material = Array.from(materialMap.entries()).map(([name, info]) => ({
      name,
      count: info.count,
      avg_price: info.prices.length > 0 ? Math.round(info.total / info.prices.length) : 0,
      min_price: info.prices.length > 0 ? Math.min(...info.prices) : 0,
      max_price: info.prices.length > 0 ? Math.max(...info.prices) : 0
    })).sort((a, b) => b.count - a.count)

    // 品牌排名
    const by_brand = calculateBrandRanking(data)

    // 规格对比
    const by_spec = calculateSpecComparison(data)

    // 价格分布
    const priceRanges = [
      { range: '<3000', min: 0, max: 3000 },
      { range: '3000-3500', min: 3000, max: 3500 },
      { range: '3500-4000', min: 3500, max: 4000 },
      { range: '4000-4500', min: 4000, max: 4500 },
      { range: '4500-5000', min: 4500, max: 5000 },
      { range: '>5000', min: 5000, max: Infinity }
    ]

    const price_distribution = priceRanges.map(range => {
      const count = prices.filter(p => p >= range.min && p < range.max).length
      return {
        range: range.range,
        count,
        percentage: prices.length > 0 ? Math.round(count / total_records * 1000) / 10 : 0
      }
    }).filter(d => d.count > 0)

    // 计算环比变化（如果有对比数据）
    let momChange = null
    let momChangeRate = null
    if (comparisonSummary) {
      momChange = avg_price - comparisonSummary.avg_price
      momChangeRate = comparisonSummary.avg_price > 0 ? (momChange / comparisonSummary.avg_price * 100) : 0
    }

    setAnalysisData({
      summary: { total_records, avg_price: Math.round(avg_price), min_price, max_price, price_range, std_deviation: Math.round(std_deviation) },
      by_material,
      by_brand,
      by_spec,
      trend: trendData,
      price_distribution,
      momChange,
      momChangeRate,
      generatedSummary: generateSummaryText({ avg_price: Math.round(avg_price) }, by_material, trendData, comparisonSummary)
    })

    setLoading(false)
  }

  const handleExportReport = () => {
    if (!analysisData) return

    const wb = XLSX.utils.book_new()

    // 汇总信息
    const summaryData = [
      ['指标', '数值'],
      ['数据记录数', analysisData.summary.total_records],
      ['平均价格', `¥${analysisData.summary.avg_price}/吨`],
      ['最低价格', `¥${analysisData.summary.min_price}/吨`],
      ['最高价格', `¥${analysisData.summary.max_price}/吨`],
      ['价格范围', `¥${analysisData.summary.price_range}`],
      ['标准差', `¥${analysisData.summary.std_deviation}`]
    ]
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryData)
    XLSX.utils.book_append_sheet(wb, wsSummary, '汇总信息')

    // 材料分析
    const materialData = analysisData.by_material.map((m: any) => ({
      '材料名称': m.name,
      '数据量': m.count,
      '平均价格': `¥${m.avg_price}/吨`,
      '最低价格': `¥${m.min_price}/吨`,
      '最高价格': `¥${m.max_price}/吨`
    }))
    const wsMaterial = XLSX.utils.json_to_sheet(materialData)
    XLSX.utils.book_append_sheet(wb, wsMaterial, '材料分析')

    // 品牌分析
    const brandData = analysisData.by_brand.map((b: any) => ({
      '品牌': b.name,
      '数据量': b.count,
      '平均价格': `¥${b.avg_price}/吨`
    }))
    const wsBrand = XLSX.utils.json_to_sheet(brandData)
    XLSX.utils.book_append_sheet(wb, wsBrand, '品牌分析')

    XLSX.writeFile(wb, `价格分析报告_${dayjs().format('YYYY-MM-DD')}.xlsx`)
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

  const materialColumns: any[] = [
    { title: '品名', dataIndex: 'name', key: 'name', width: 120 },
    { title: '数据量', dataIndex: 'count', key: 'count', align: 'center' as const, width: 80 },
    { title: '平均价格', dataIndex: 'avg_price', key: 'avg_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 },
    { title: '最低价', dataIndex: 'min_price', key: 'min_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 },
    { title: '最高价', dataIndex: 'max_price', key: 'max_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 }
  ]

  const brandColumns: any[] = [
    { title: '排名', key: 'rank', align: 'center' as const, width: 60, render: (_: any, __: any, idx: number) => idx + 1 },
    { title: '品牌/钢厂', dataIndex: 'name', key: 'name', width: 150 },
    { title: '数据量', dataIndex: 'count', key: 'count', align: 'center' as const, width: 80 },
    { title: '平均价格', dataIndex: 'avg_price', key: 'avg_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 },
    { title: '价格区间', key: 'range', render: (_: any, r: any) => `${r.min_price}-${r.max_price}`, align: 'center' as const, width: 120 }
  ]

  const specColumns: any[] = [
    { title: '规格', dataIndex: 'spec', key: 'spec', width: 100 },
    { title: '数据量', dataIndex: 'count', key: 'count', align: 'center' as const, width: 80 },
    { title: '平均价格', dataIndex: 'avg_price', key: 'avg_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 },
    { title: '最低价', dataIndex: 'min_price', key: 'min_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 },
    { title: '最高价', dataIndex: 'max_price', key: 'max_price', render: (v: number) => `¥${v.toLocaleString()}`, align: 'right' as const, width: 100 }
  ]

  // 计算趋势方向图标
  const getTrendIcon = (change: number | null) => {
    if (change === null) return null
    return change > 0 ? <ArrowUpOutlined style={{ color: COLOR_UP }} /> : change < 0 ? <ArrowDownOutlined style={{ color: COLOR_DOWN }} /> : <SwapOutlined style={{ color: '#999' }} />
  }

  return (
    <div>
      {/* 报告标题和操作栏 */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>价格监控分析报告</span>
          </Space>
        }
        extra={
          <Space>
            <Select
              value={selectedView}
              onChange={setSelectedView}
              style={{ width: 140 }}
            >
              <Select.Option value="summary"><ProfileOutlined /> 摘要总览</Select.Option>
              <Select.Option value="overview"><BarChartOutlined /> 详细数据</Select.Option>
              <Select.Option value="trend"><LineOutlined /> 趋势分析</Select.Option>
              <Select.Option value="brand"><TrophyOutlined /> 品牌排名</Select.Option>
              <Select.Option value="spec"><ThunderboltOutlined /> 规格对比</Select.Option>
              <Select.Option value="distribution"><AreaChartOutlined /> 价格分布</Select.Option>
            </Select>
            <Button icon={<DownloadOutlined />} onClick={handleExportReport}>
              导出报告
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        {/* 摘要视图 */}
        {selectedView === 'summary' && (
          <>
            {/* 自动生成的摘要 */}
            {analysisData.generatedSummary && (
              <div style={{
                background: 'linear-gradient(135deg, rgba(74, 134, 200, 0.08) 0%, rgba(74, 134, 200, 0.03) 100%)',
                border: '1px solid rgba(74, 134, 200, 0.2)',
                borderRadius: 8,
                padding: '16px 20px',
                marginBottom: 24
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                  <FileTextOutlined style={{ color: '#4A86C8', marginRight: 8 }} />
                  <Text strong style={{ color: '#16325C' }}>市场简评</Text>
                  <Tag color="#4A86C8" style={{ marginLeft: 8 }}>AI 生成</Tag>
                </div>
                <Paragraph style={{ marginBottom: 0, fontSize: 15, lineHeight: 1.8, color: '#333' }}>
                  {analysisData.generatedSummary}
                </Paragraph>
              </div>
            )}

            {/* 核心指标卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
              <Col span={6}>
                <Card size="small" style={{ background: '#F8FAFC', border: '1px solid #E8EBF0' }}>
                  <Statistic
                    title={<span style={{ fontSize: 12, color: '#666' }}>本期均价</span>}
                    value={analysisData.summary.avg_price}
                    prefix={<DollarOutlined style={{ color: '#4A86C8' }} />}
                    suffix="元/吨"
                    valueStyle={{ color: '#16325C', fontSize: 20, fontWeight: 600 }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ background: '#F8FAFC', border: '1px solid #E8EBF0' }}>
                  <Statistic
                    title={<span style={{ fontSize: 12, color: '#666' }}>环比变化</span>}
                    value={analysisData.momChange !== null ? Math.abs(analysisData.momChange).toFixed(0) : '-'}
                    prefix={analysisData.momChange !== null ? getTrendIcon(analysisData.momChange) : null}
                    suffix={analysisData.momChangeRate !== null ? `${analysisData.momChangeRate > 0 ? '+' : ''}${analysisData.momChangeRate.toFixed(2)}%` : ''}
                    valueStyle={{
                      color: analysisData.momChange !== null ? (analysisData.momChange > 0 ? COLOR_UP : analysisData.momChange < 0 ? COLOR_DOWN : '#999') : '#999',
                      fontSize: 20,
                      fontWeight: 600
                    }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ background: '#F8FAFC', border: '1px solid #E8EBF0' }}>
                  <Statistic
                    title={<span style={{ fontSize: 12, color: '#666' }}>价格区间</span>}
                    value={`${analysisData.summary.min_price}-${analysisData.summary.max_price}`}
                    suffix="元/吨"
                    valueStyle={{ color: '#16325C', fontSize: 16, fontWeight: 600 }}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small" style={{ background: '#F8FAFC', border: '1px solid #E8EBF0' }}>
                  <Statistic
                    title={<span style={{ fontSize: 12, color: '#666' }}>波动系数</span>}
                    value={analysisData.summary.std_deviation}
                    prefix="±"
                    suffix="元"
                    valueStyle={{ color: '#F59E0B', fontSize: 20, fontWeight: 600 }}
                  />
                </Card>
              </Col>
            </Row>

            <Divider />

            {/* 品名价格对比 */}
            <div style={{ marginBottom: 24 }}>
              <h4 style={{ color: '#16325C', marginBottom: 16 }}>
                <BarChartOutlined /> 分品名价格对比
              </h4>
              <Table
                dataSource={analysisData.by_material.map((m: any, i: number) => ({ ...m, key: i }))}
                columns={materialColumns}
                pagination={false}
                size="small"
                style={{ background: '#fff' }}
              />
            </div>

            <Divider />

            {/* 品牌TOP5 */}
            <div>
              <h4 style={{ color: '#16325C', marginBottom: 16 }}>
                <TrophyOutlined /> 品牌价格TOP5
              </h4>
              <Row gutter={16}>
                {analysisData.by_brand.slice(0, 5).map((brand: any, idx: number) => (
                  <Col span={4} key={brand.name}>
                    <Card size="small" style={{
                      textAlign: 'center',
                      border: idx === 0 ? '2px solid #FFD700' : '1px solid #E8EBF0',
                      background: idx === 0 ? 'linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, rgba(255, 215, 0, 0.05) 100%)' : '#FAFAFA'
                    }}>
                      <div style={{ fontSize: 24, fontWeight: 700, color: idx === 0 ? '#FFD700' : idx === 1 ? '#C0C0C0' : idx === 2 ? '#CD7F32' : '#999' }}>
                        #{idx + 1}
                      </div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#16325C', marginTop: 4 }}>{brand.name}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#4A86C8', marginTop: 4 }}>
                        ¥{brand.avg_price.toLocaleString()}
                      </div>
                      <div style={{ fontSize: 11, color: '#999' }}>{brand.count}条数据</div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </div>
          </>
        )}

        {/* 总览视图 */}
        {selectedView === 'overview' && (
          <>
            {/* 汇总统计卡片 */}
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic title="数据记录" value={analysisData.summary.total_records} suffix="条" />
              </Col>
              <Col span={6}>
                <Statistic
                  title="平均价格"
                  value={analysisData.summary.avg_price}
                  prefix="¥"
                  suffix="/吨"
                  valueStyle={{ color: '#4A86C8' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="价格区间"
                  value={`${analysisData.summary.min_price} - ${analysisData.summary.max_price}`}
                  valueStyle={{ fontSize: 14 }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="标准差"
                  value={analysisData.summary.std_deviation}
                  prefix="¥"
                  valueStyle={{ color: '#F59E0B' }}
                />
              </Col>
            </Row>

            <Divider />

            {/* 按材料分析 */}
            <div style={{ marginBottom: 24 }}>
              <h4><BarChartOutlined /> 按品名分析</h4>
              <Table
                dataSource={analysisData.by_material.map((m: any, i: number) => ({ ...m, key: i }))}
                columns={materialColumns}
                pagination={false}
                size="small"
              />
            </div>

            <Divider />

            {/* 价格分布 */}
            <div>
              <h4><AreaChartOutlined /> 价格分布</h4>
              <Table
                dataSource={analysisData.price_distribution.map((d: any, i: number) => ({ ...d, key: i }))}
                columns={[
                  { title: '价格区间', dataIndex: 'range', key: 'range' },
                  { title: '数量', dataIndex: 'count', key: 'count', align: 'center' as const },
                  { title: '占比', dataIndex: 'percentage', key: 'percentage', render: (v: number) => `${v}%`, align: 'center' as const }
                ]}
                pagination={false}
                size="small"
              />
            </div>
          </>
        )}

        {/* 趋势分析视图 */}
        {selectedView === 'trend' && (
          <>
            <h4><AreaChartOutlined /> 价格趋势分析</h4>
            {analysisData.trend && analysisData.trend.length > 0 ? (
              <>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Statistic title="最高价" value={Math.max(...analysisData.trend.map((t: any) => t.max_price))} prefix="¥" suffix="/吨" valueStyle={{ color: COLOR_UP }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="最低价" value={Math.min(...analysisData.trend.map((t: any) => t.min_price))} prefix="¥" suffix="/吨" valueStyle={{ color: COLOR_DOWN }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="均价" value={(analysisData.trend.reduce((s: number, t: any) => s + t.avg_price, 0) / analysisData.trend.length).toFixed(0)} prefix="¥" suffix="/吨" valueStyle={{ color: '#4A86C8' }} />
                  </Col>
                  <Col span={6}>
                    <Statistic title="数据天数" value={analysisData.trend.length} suffix="天" />
                  </Col>
                </Row>
                <ResponsiveContainer width="100%" height={350}>
                  <ComposedChart data={analysisData.trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="priceAreaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4A86C8" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#4A86C8" stopOpacity={0.05}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8EBF0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString()} />
                    <Tooltip contentStyle={{ background: '#16325C', border: 'none', borderRadius: 8 }} labelStyle={{ color: '#fff' }} formatter={(value) => { const v = Number(value); return [`¥${v.toLocaleString()}元/吨`, '']; }} />
                    <Area type="monotone" dataKey="max_price" stroke="none" fill="url(#priceAreaGradient)" />
                    <Line type="monotone" dataKey="max_price" stroke={COLOR_UP} strokeWidth={1} strokeDasharray="4 2" dot={false} name="最高价" />
                    <Line type="monotone" dataKey="min_price" stroke={COLOR_DOWN} strokeWidth={1} strokeDasharray="4 2" dot={false} name="最低价" />
                    <Line type="monotone" dataKey="avg_price" stroke="#4A86C8" strokeWidth={3} dot={{ fill: '#4A86C8', strokeWidth: 2, stroke: '#fff', r: 4 }} name="均价" />
                  </ComposedChart>
                </ResponsiveContainer>
              </>
            ) : (
              <Alert message="暂无趋势数据" type="info" showIcon />
            )}
          </>
        )}

        {/* 品牌排名视图 */}
        {selectedView === 'brand' && (
          <>
            <h4><TrophyOutlined /> 品牌价格排名</h4>
            {analysisData.by_brand.length > 0 ? (
              <>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  {analysisData.by_brand.slice(0, 3).map((brand: any, idx: number) => (
                    <Col span={8} key={brand.name}>
                      <Card size="small" style={{
                        textAlign: 'center',
                        border: '2px solid',
                        borderColor: idx === 0 ? '#FFD700' : idx === 1 ? '#C0C0C0' : '#CD7F32',
                        background: idx === 0 ? 'linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(255, 215, 0, 0.05) 100%)' :
                                   idx === 1 ? 'linear-gradient(135deg, rgba(192, 192, 192, 0.15) 0%, rgba(192, 192, 192, 0.05) 100%)' :
                                   'linear-gradient(135deg, rgba(205, 127, 50, 0.15) 0%, rgba(205, 127, 50, 0.05) 100%)'
                      }}>
                        <div style={{ fontSize: 32, fontWeight: 700, color: idx === 0 ? '#FFD700' : idx === 1 ? '#C0C0C0' : '#CD7F32' }}>
                          {idx === 0 ? '🥇' : idx === 1 ? '🥈' : '🥉'}
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: '#16325C', marginTop: 8 }}>{brand.name}</div>
                        <div style={{ fontSize: 24, fontWeight: 700, color: '#4A86C8', marginTop: 4 }}>
                          ¥{brand.avg_price.toLocaleString()}/吨
                        </div>
                        <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                          {brand.count}条记录 | 区间: {brand.min_price}-{brand.max_price}
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analysisData.by_brand.slice(0, 10).map((b: any, i: number) => ({ name: b.name, price: b.avg_price, rank: i + 1 }))} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={(v: number) => `¥${v}`} />
                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => { const v = Number(value); return [`¥${v.toLocaleString()}元/吨`, '平均价格']; }} />
                    <Bar dataKey="price" fill="#4A86C8" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <Table
                  dataSource={analysisData.by_brand.map((b: any, i: number) => ({ ...b, key: i, rank: i + 1 }))}
                  columns={brandColumns}
                  pagination={{ pageSize: 10 }}
                  size="small"
                  style={{ marginTop: 16 }}
                />
              </>
            ) : (
              <Alert message="暂无品牌数据" type="info" showIcon />
            )}
          </>
        )}

        {/* 规格对比视图 */}
        {selectedView === 'spec' && (
          <>
            <h4><ThunderboltOutlined /> 规格价格对比</h4>
            {analysisData.by_spec.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analysisData.by_spec}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="spec" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={(v: number) => `¥${v}`} />
                    <Tooltip formatter={(value) => { const v = Number(value); return [`¥${v.toLocaleString()}元/吨`, '平均价格']; }} />
                    <Bar dataKey="avg_price" fill="#16325C" name="平均价格" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
                <Table
                  dataSource={analysisData.by_spec.map((s: any, i: number) => ({ ...s, key: i }))}
                  columns={specColumns}
                  pagination={false}
                  size="small"
                  style={{ marginTop: 16 }}
                />
              </>
            ) : (
              <Alert message="暂无规格数据" type="info" showIcon />
            )}
          </>
        )}

        {/* 价格分布视图 */}
        {selectedView === 'distribution' && (
          <>
            <h4><BarChartOutlined /> 价格分布柱状图</h4>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analysisData.price_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip formatter={(value, name) => { const v = Number(value); return [v, name === 'count' ? '数据量' : '占比']; }} />
                <Bar dataKey="count" fill="#4A86C8" name="数据量" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>

            <Divider />

            <h4>分布明细</h4>
            <Table
              dataSource={analysisData.price_distribution.map((d: any, i: number) => ({ ...d, key: i }))}
              columns={[
                { title: '价格区间', dataIndex: 'range', key: 'range' },
                { title: '数量', dataIndex: 'count', key: 'count', align: 'center' as const },
                { title: '占比', dataIndex: 'percentage', key: 'percentage', render: (v: number) => `${v}%`, align: 'right' as const }
              ]}
              pagination={false}
              size="small"
            />
          </>
        )}
      </Card>
    </div>
  )
}
