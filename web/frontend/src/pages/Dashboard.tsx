import { Row, Col, Card, Statistic, Table, Tag, Typography, Space, Alert, Button, Select, Tooltip } from 'antd'
import {
  ProjectOutlined,
  DollarOutlined,
  SyncOutlined,
  CalendarOutlined,
  DownloadOutlined,
} from '@ant-design/icons'
import { Column } from '@ant-design/charts'
import { useEffect, useState } from 'react'
import { statsApi } from '../services/api'
import * as XLSX from 'xlsx'

const { Title } = Typography
const LOCAL_API = 'http://localhost:8000'

interface Stats {
  projects: number;
  materials: number;
  priceHistory: number;
  timestamp: string;
}

interface PriceItem {
  date: string;
  time: string;
  material_name: string;
  spec: string;
  material_type: string;
  brand: string;
  price: number;
  price_max: number;
  price_change: string;
  remark: string;
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats>({ projects: 0, materials: 0, priceHistory: 0, timestamp: '' })
  const [latestPrices, setLatestPrices] = useState<PriceItem[]>([])
  const [allPrices, setAllPrices] = useState<{ [date: string]: PriceItem[] }>({})
  const [priceLoading, setPriceLoading] = useState(true)
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [comparisonDate, setComparisonDate] = useState<string | null>(null)

  useEffect(() => {
    statsApi.get().then(data => {
      setStats(data)
    }).catch(console.error)

    fetchAvailableDates()
  }, [])

  useEffect(() => {
    if (selectedDate) {
      fetchPricesByDate(selectedDate)
    }
  }, [selectedDate])

  useEffect(() => {
    if (comparisonDate && selectedDate) {
      fetchComparisonPrices()
    }
  }, [comparisonDate])

  const fetchAvailableDates = async () => {
    try {
      const response = await fetch(`${LOCAL_API}/api/price-sources/sheets`)
      const data = await response.json()
      if (data.success && data.sheets) {
        const dateSheets = data.sheets.filter((s: string) => /^\d{4}-\d{2}-\d{2}$/.test(s))
        dateSheets.sort().reverse()
        setAvailableDates(dateSheets)
        if (dateSheets.length > 0 && !selectedDate) {
          setSelectedDate(dateSheets[0])
          if (dateSheets.length > 1) {
            setComparisonDate(dateSheets[1])
          }
        }
      }
    } catch (error) {
      console.error('获取日期列表失败:', error)
    }
  }

  const fetchPricesByDate = async (date: string) => {
    setPriceLoading(true)
    try {
      const response = await fetch(`${LOCAL_API}/api/yantai-prices/latest?date=${date}`)
      const data = await response.json()

      if (data.success && data.prices) {
        setLatestPrices(data.prices)
        setAllPrices(prev => ({ ...prev, [date]: data.prices }))
      } else if (data.prices) {
        setLatestPrices(data.prices)
        setAllPrices(prev => ({ ...prev, [date]: data.prices }))
      }
    } catch (error) {
      console.error('获取价格失败:', error)
    }
    setPriceLoading(false)
  }

  const fetchComparisonPrices = async () => {
    if (!comparisonDate || allPrices[comparisonDate]) return

    try {
      const response = await fetch(`${LOCAL_API}/api/yantai-prices/latest?date=${comparisonDate}`)
      const data = await response.json()
      if (data.prices) {
        setAllPrices(prev => ({ ...prev, [comparisonDate]: data.prices }))
      }
    } catch (error) {
      console.error('获取对比价格失败:', error)
    }
  }

  // 计算涨幅分析
  const calculatePriceChange = () => {
    if (!selectedDate || !comparisonDate || !allPrices[selectedDate] || !allPrices[comparisonDate]) {
      return []
    }

    const currentPrices = allPrices[selectedDate]
    const previousPrices = allPrices[comparisonDate]

    const changes: { brand: string; spec: string; prev: number; curr: number; change: number; changeRate: number }[] = []

    currentPrices.forEach(curr => {
      const prev = previousPrices.find(p => p.brand === curr.brand && p.spec === curr.spec)
      if (prev) {
        const change = curr.price - prev.price
        const changeRate = prev.price > 0 ? (change / prev.price * 100) : 0
        changes.push({
          brand: curr.brand,
          spec: curr.spec,
          prev: prev.price,
          curr: curr.price,
          change,
          changeRate
        })
      }
    })

    return changes.sort((a, b) => b.changeRate - a.changeRate)
  }

  const priceChanges = calculatePriceChange()

  // 统计数据
  const priceStats = {
    avgPrice: latestPrices.length > 0
      ? (latestPrices.reduce((sum, p) => sum + (p.price || 0), 0) / latestPrices.length).toFixed(0)
      : 0,
    minPrice: latestPrices.length > 0
      ? Math.min(...latestPrices.map(p => p.price || 0))
      : 0,
    maxPrice: latestPrices.length > 0
      ? Math.max(...latestPrices.map(p => p.price || 0))
      : 0
  }

  // 按品名分组统计
  const priceByType = latestPrices.reduce((acc, p) => {
    const type = p.material_name || '未知'
    if (!acc[type]) acc[type] = { total: 0, count: 0, avgPrice: 0 }
    acc[type].total += p.price || 0
    acc[type].count += 1
    acc[type].avgPrice = acc[type].total / acc[type].count
    return acc
  }, {} as Record<string, { total: number; count: number; avgPrice: number }>)

  const trendData = Object.entries(priceByType).map(([type, data]) => ({
    type,
    avgPrice: Math.round(data.avgPrice)
  }))

  const trendConfig = {
    data: trendData,
    xField: 'type',
    yField: 'avgPrice',
    label: { position: 'top' as const },
    color: '#1890ff',
  }

  // 导出数据
  const handleExport = () => {
    if (latestPrices.length === 0) return

    const exportData = latestPrices.map(p => ({
      '日期': p.date || selectedDate,
      '时间': p.time || '',
      '品名': p.material_name || '',
      '规格': p.spec || '',
      '材质': p.material_type || '',
      '品牌': p.brand || '',
      '单价(元/吨)': p.price || 0,
      '涨跌': p.price_change || '',
      '备注': p.remark || ''
    }))

    const ws = XLSX.utils.json_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '钢筋价格')

    // 添加涨幅分析sheet
    if (priceChanges.length > 0) {
      const changeData = priceChanges.map(c => ({
        '品牌': c.brand,
        '规格': c.spec,
        '上期价格': c.prev,
        '本期价格': c.curr,
        '涨跌额': c.change,
        '涨跌幅(%)': c.changeRate.toFixed(2)
      }))
      const wsChange = XLSX.utils.json_to_sheet(changeData)
      XLSX.utils.book_append_sheet(wb, wsChange, '涨幅分析')
    }

    XLSX.writeFile(wb, `钢筋价格_${selectedDate}.xlsx`)
  }

  // 涨幅表格列
  const changeColumns = [
    { title: '品牌', dataIndex: 'brand', width: 120 },
    { title: '规格', dataIndex: 'spec', width: 80 },
    { title: '上期价格', dataIndex: 'prev', width: 100, render: (v: number) => v.toLocaleString() },
    { title: '本期价格', dataIndex: 'curr', width: 100, render: (v: number) => v.toLocaleString() },
    { title: '涨跌额', dataIndex: 'change', width: 100, render: (v: number) => v > 0 ? `+${v}` : v.toString() },
    {
      title: '涨跌幅',
      dataIndex: 'changeRate',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#f5222d' : v < 0 ? '#52c41a' : '#999'
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
      }
    }
  ]

  return (
    <div>
      <Title level={4}>仪表盘</Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="项目总数"
              value={stats.projects}
              prefix={<ProjectOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="材料种类"
              value={stats.materials}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="价格记录"
              value={latestPrices.length}
              prefix={<SyncOutlined />}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最新均价"
              value={priceStats.avgPrice}
              suffix="元/吨"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 钢筋价格快捷查看 */}
      <Card
        title={
          <Space>
            <CalendarOutlined />
            <span>山东烟台钢筋价格</span>
            {selectedDate && <Tag color="blue">{selectedDate}</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Select
              placeholder="对比日期"
              style={{ width: 150 }}
              allowClear
              value={comparisonDate}
              onChange={(v) => setComparisonDate(v)}
              options={availableDates.filter(d => d !== selectedDate).map(d => ({
                label: d,
                value: d
              }))}
            />
            <Select
              value={selectedDate || ''}
              onChange={(v) => setSelectedDate(v)}
              style={{ width: 150 }}
              options={availableDates.map(d => ({
                label: d,
                value: d
              }))}
            />
            <Tooltip title="导出Excel">
              <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={latestPrices.length === 0}>
                导出
              </Button>
            </Tooltip>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {priceLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : latestPrices.length > 0 ? (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="最高价" value={priceStats.maxPrice} suffix="元/吨" valueStyle={{ color: '#f5222d' }} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="最低价" value={priceStats.minPrice} suffix="元/吨" valueStyle={{ color: '#52c41a' }} />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="均价" value={priceStats.avgPrice} suffix="元/吨" />
                </Card>
              </Col>
              <Col span={6}>
                <Card size="small">
                  <Statistic title="记录数" value={latestPrices.length} suffix="条" />
                </Card>
              </Col>
            </Row>

            {/* 价格趋势图 */}
            {trendData.length > 0 && (
              <Card title="按品名均价" size="small" style={{ marginBottom: 16 }}>
                <Column {...trendConfig} height={200} />
              </Card>
            )}

            {/* 涨幅分析 */}
            {priceChanges.length > 0 && comparisonDate && (
              <Card
                title={
                  <Space>
                    <span>涨幅分析</span>
                    <Tag color="blue">{selectedDate} vs {comparisonDate}</Tag>
                  </Space>
                }
                size="small"
                style={{ marginBottom: 16 }}
              >
                <Table
                  dataSource={priceChanges.map((c, i) => ({ ...c, key: i }))}
                  rowKey="key"
                  pagination={false}
                  size="small"
                  columns={changeColumns}
                />
              </Card>
            )}

            {/* 最新价格表格 */}
            <Table
              dataSource={latestPrices.map((p, i) => ({ ...p, key: i }))}
              rowKey="key"
              pagination={{ pageSize: 10, showSizeChanger: true }}
              size="small"
              scroll={{ x: 900 }}
              columns={[
                { title: '日期', dataIndex: 'date', width: 100, render: (v: string) => v || selectedDate },
                { title: '时间', dataIndex: 'time', width: 80 },
                { title: '品名', dataIndex: 'material_name', width: 80 },
                { title: '规格', dataIndex: 'spec', width: 80 },
                { title: '品牌', dataIndex: 'brand', width: 100 },
                {
                  title: '单价(元/吨)',
                  dataIndex: 'price',
                  render: (v: number) => <strong style={{ color: '#1890ff' }}>{v.toLocaleString()}</strong>
                },
              ]}
            />
          </>
        ) : (
          <Alert message="暂无钢筋价格数据，请先运行后端服务并抓取数据" type="warning" showIcon />
        )}
      </Card>
    </div>
  )
}