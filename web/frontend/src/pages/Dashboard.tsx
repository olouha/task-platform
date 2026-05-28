import { Row, Col, Card, Statistic, Table, Tag, Space, Alert, Button, Select, Tooltip } from 'antd'
import {
  ProjectOutlined,
  DollarOutlined,
  SyncOutlined,
  DownloadOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons'
import { Column } from '@ant-design/charts'
import { useEffect, useState } from 'react'
import { statsApi, config } from '../services/api'
import * as XLSX from 'xlsx'

// 科技数据卡片组件 - 轻奢高科技风格
const TechStatCard = ({
  title,
  value,
  suffix,
  icon,
  color,
  trend,
  trendValue
}: {
  title: string
  value: number | string
  suffix?: string
  icon: React.ReactNode
  color: string
  trend?: 'up' | 'down'
  trendValue?: string
}) => (
  <div className="tech-card">
    <div className="card-accent-line" />
    <div className="tech-card-header">
      <span className="tech-card-title">{title}</span>
      <div className="tech-card-icon" style={{ color }}>{icon}</div>
    </div>
    <div className="tech-card-value" style={{ background: `linear-gradient(135deg, ${color} 0%, ${color}88 100%)`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
      {typeof value === 'number' ? value.toLocaleString() : value}
    </div>
    {suffix && <div className="tech-card-sub" style={{ fontSize: 13 }}>{suffix}</div>}
    {trend && trendValue && (
      <div className={`tech-card-trend ${trend}`}>
        {trend === 'up' ? <RiseOutlined /> : <FallOutlined />}
        <span>{trendValue}</span>
      </div>
    )}
  </div>
)

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
      const response = await fetch(`${config.apiUrl}/api/price-sources/sheets`)
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
      const response = await fetch(`${config.apiUrl}/api/yantai-prices/latest?date=${date}`)
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
      const response = await fetch(`${config.apiUrl}/api/yantai-prices/latest?date=${comparisonDate}`)
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
    color: '#16325C',
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
    {
      title: '涨跌额',
      dataIndex: 'change',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#EF4444' : v < 0 ? '#10B981' : '#999'
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v}</span>
      }
    },
    {
      title: '涨跌幅',
      dataIndex: 'changeRate',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#EF4444' : v < 0 ? '#10B981' : '#999'
        return <span style={{ color, fontWeight: 600 }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
      }
    }
  ]

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <div className="page-header">
        <h2 className="page-title">数据仪表盘</h2>
        <p className="page-subtitle">工程项目材料调差数据总览，实时监控价格动态</p>
      </div>

      {/* 科技统计卡片 */}
      <div className="stats-grid">
        <TechStatCard
          title="项目总数"
          value={stats.projects}
          icon={<ProjectOutlined />}
          color="#16325C"
          suffix="个工程项目"
        />
        <TechStatCard
          title="材料种类"
          value={stats.materials}
          icon={<DollarOutlined />}
          color="#722ed1"
          suffix="种材料类型"
        />
        <TechStatCard
          title="价格记录"
          value={latestPrices.length}
          icon={<SyncOutlined />}
          color="#4A86C8"
          suffix="条实时数据"
        />
        <TechStatCard
          title="市场均价"
          value={priceStats.avgPrice}
          icon={<BarChartOutlined />}
          color="#10B981"
          suffix="元/吨"
        />
      </div>

      {/* 价格监控区块 */}
      <div className="data-section" style={{ marginTop: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <LineChartOutlined />
            <span>山东烟台钢筋价格监控</span>
            {selectedDate && <Tag color="#4A86C8" style={{ marginLeft: 8 }}>{selectedDate}</Tag>}
          </div>
          <Space>
            <Select
              placeholder="对比日期"
              style={{ width: 140 }}
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
              style={{ width: 140 }}
              options={availableDates.map(d => ({
                label: d,
                value: d
              }))}
            />
            <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={latestPrices.length === 0}>
              导出数据
            </Button>
          </Space>
        </div>

        <div className="data-section-body">
          {priceLoading ? (
            <div style={{ textAlign: 'center', padding: 60 }}>数据加载中...</div>
          ) : latestPrices.length > 0 ? (
            <>
              {/* 统计卡片行 */}
              <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                <Col span={6}>
                  <div className="tech-card" style={{ padding: 16 }}>
                    <div className="card-accent-line" />
                    <div className="tech-card-title">最高价</div>
                    <div className="tech-card-value digital-value" style={{ fontSize: 28, background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {priceStats.maxPrice.toLocaleString()}
                    </div>
                    <div className="tech-card-sub">元/吨</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="tech-card" style={{ padding: 16 }}>
                    <div className="card-accent-line" />
                    <div className="tech-card-title">最低价</div>
                    <div className="tech-card-value digital-value" style={{ fontSize: 28, background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {priceStats.minPrice.toLocaleString()}
                    </div>
                    <div className="tech-card-sub">元/吨</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="tech-card highlight" style={{ padding: 16 }}>
                    <div className="card-accent-line" />
                    <div className="tech-card-title">市场均价</div>
                    <div className="tech-card-value highlight-number" style={{ fontSize: 28 }}>
                      {priceStats.avgPrice}
                    </div>
                    <div className="tech-card-sub">元/吨</div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="tech-card" style={{ padding: 16 }}>
                    <div className="card-accent-line" />
                    <div className="tech-card-title">数据记录</div>
                    <div className="tech-card-value" style={{ fontSize: 28, background: 'linear-gradient(135deg, #4A86C8 0%, #1a4080 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {latestPrices.length}
                    </div>
                    <div className="tech-card-sub">条价格记录</div>
                  </div>
                </Col>
              </Row>

              {/* 价格趋势图 */}
              {trendData.length > 0 && (
                <div className="chart-container" style={{ marginBottom: 24 }}>
                  <div className="chart-title">
                    <BarChartOutlined />
                    <span>按品名均价走势</span>
                  </div>
                  <Column {...trendConfig} height={250} />
                </div>
              )}

              {/* 涨幅分析 */}
              {priceChanges.length > 0 && comparisonDate && (
                <div className="data-section" style={{ marginBottom: 24 }}>
                  <div className="data-section-header">
                    <div className="data-section-title">
                      {priceChanges[0]?.change > 0 ? <RiseOutlined style={{ color: '#EF4444' }} /> : <FallOutlined style={{ color: '#10B981' }} />}
                      <span>价格涨幅分析</span>
                      <Tag color="#4A86C8">{selectedDate}</Tag>
                      <span style={{ color: '#999' }}>对比</span>
                      <Tag color="blue">{comparisonDate}</Tag>
                    </div>
                  </div>
                  <div className="data-section-body">
                    <Table
                      dataSource={priceChanges.map((c, i) => ({ ...c, key: i }))}
                      rowKey="key"
                      pagination={false}
                      size="small"
                      columns={changeColumns}
                    />
                  </div>
                </div>
              )}

              {/* 最新价格表格 */}
              <div className="data-section">
                <div className="data-section-header">
                  <div className="data-section-title">
                    <DatabaseOutlined />
                    <span>价格明细列表</span>
                  </div>
                </div>
                <div className="data-section-body">
                  <Table
                    dataSource={latestPrices.map((p, i) => ({ ...p, key: i }))}
                    rowKey="key"
                    pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total: number) => `共 ${total} 条` }}
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
                        width: 120,
                        render: (v: number) => <strong style={{ color: '#16325C', fontWeight: 600 }}>{v.toLocaleString()}</strong>
                      },
                    ]}
                  />
                </div>
              </div>
            </>
          ) : (
            <Alert
              message="暂无钢筋价格数据"
              description="请确保后端服务已启动并已抓取价格数据"
              type="warning"
              showIcon
            />
          )}
        </div>
      </div>
    </div>
  )
}