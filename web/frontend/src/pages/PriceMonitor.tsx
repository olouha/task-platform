import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Select, message, Spin, Alert } from 'antd'
import { SyncOutlined, ReloadOutlined, FilterOutlined, CalendarOutlined, DownloadOutlined } from '@ant-design/icons'
import { useState, useEffect, useRef } from 'react'
import { YantaiPrice } from '../services/api'
import * as XLSX from 'xlsx'

// API地址 - 从环境变量读取
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function PriceMonitor() {
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [latestPrices, setLatestPrices] = useState<YantaiPrice[]>([])
  const [allPrices, setAllPrices] = useState<{ [date: string]: YantaiPrice[] }>({})
  const [summary, setSummary] = useState<any>({
    total_count: 0,
    brands: [],
    material_types: {},
    brands_detail: {}
  })

  // WebSocket连接
  const wsRef = useRef<WebSocket | null>(null)

  // 日期筛选
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [comparisonDate, setComparisonDate] = useState<string | null>(null)

  // 筛选条件
  const [filterBrand, setFilterBrand] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string | null>(null)
  const [filterSpec, setFilterSpec] = useState<string | null>(null)

  // 所有品牌和规格
  const [allBrands, setAllBrands] = useState<string[]>([])
  const [allTypes, setAllTypes] = useState<string[]>([])
  const [allSpecs, setAllSpecs] = useState<string[]>([])

  // WebSocket连接
  useEffect(() => {
    connectWebSocket()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(`ws://localhost:8000/ws`)

      ws.onopen = () => {
        console.log('WebSocket已连接')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('收到推送:', data)

          // 处理推送消息
          if (data.type === 'fetch_success') {
            message.success(data.data.message)
            // 自动刷新数据
            fetchAvailableDates()
            if (selectedDate) {
              fetchPricesByDate(selectedDate)
            }
          } else if (data.type === 'fetch_failed') {
            message.error(data.data.message)
          } else if (data.type === 'fetch_started') {
            message.info(data.data.message)
          }
        } catch (e) {
          console.error('解析推送消息失败:', e)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket已断开，5秒后重连...')
        setTimeout(connectWebSocket, 5000)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('连接WebSocket失败:', error)
    }
  }

  // 初始化：获取所有可用的日期
  useEffect(() => {
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

  // 获取所有可用的日期
  const fetchAvailableDates = async () => {
    try {
      const response = await fetch(`${API_URL}/api/price-sources/sheets`)
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
    setInitialLoading(true)
    try {
      const url = `${API_URL}/api/yantai-prices/latest?date=${date}`
      const response = await fetch(url)
      const data = await response.json()

      let prices = []
      if (data.success && data.prices) {
        prices = data.prices
      } else if (data.prices) {
        prices = data.prices
      }

      setLatestPrices(prices)
      setAllPrices(prev => ({ ...prev, [date]: prices }))

      // 提取所有规格和品牌
      const specs = [...new Set<string>(prices.map((p: YantaiPrice) => p.spec).filter(Boolean))].sort()
      const brands = [...new Set<string>(prices.map((p: YantaiPrice) => p.brand).filter(Boolean))].sort()
      const types = [...new Set<string>(prices.map((p: YantaiPrice) => p.material_name).filter(Boolean))].sort()

      setAllSpecs(specs)
      setAllBrands(brands)
      setAllTypes(types)

      // 更新汇总
      const brandCount: Record<string, number> = {}
      brands.forEach(b => {
        brandCount[b] = prices.filter((p: YantaiPrice) => p.brand === b).length
      })

      setSummary({
        total_count: prices.length,
        brands,
        material_types: types.reduce((acc: Record<string, number>, t: string) => {
          acc[t] = prices.filter((p: YantaiPrice) => p.material_name === t).length
          return acc
        }, {}),
        brands_detail: brandCount
      })

    } catch (error) {
      console.error('获取价格失败:', error)
      setLatestPrices([])
    }
    setInitialLoading(false)
  }

  const fetchComparisonPrices = async () => {
    if (!comparisonDate || allPrices[comparisonDate]) return

    try {
      const response = await fetch(`${API_URL}/api/yantai-prices/latest?date=${comparisonDate}`)
      const data = await response.json()
      if (data.prices) {
        setAllPrices(prev => ({ ...prev, [comparisonDate]: data.prices }))
      }
    } catch (error) {
      console.error('获取对比价格失败:', error)
    }
  }

  // 按品牌筛选
  const handleBrandFilter = (brand: string | null) => {
    setFilterBrand(brand)
    setFilterType(null)
    setFilterSpec(null)
  }

  // 按品名筛选
  const handleTypeFilter = (type: string | null) => {
    setFilterType(type)
    setFilterBrand(null)
    setFilterSpec(null)
  }

  // 清除筛选
  const clearFilter = () => {
    setFilterBrand(null)
    setFilterType(null)
    setFilterSpec(null)
  }

  // 触发抓取
  const handleFetch = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/yantai-prices/fetch`, { method: 'POST' })
      const data = await response.json()

      if (data.success) {
        message.success(`抓取成功！共${data.prices?.length || 0}条数据`)
        fetchAvailableDates()
        if (selectedDate) {
          fetchPricesByDate(selectedDate)
        }
      } else {
        message.info(data.error_message || '抓取失败')
      }
    } catch (error) {
      console.error('抓取失败:', error)
      message.error('抓取失败，请检查后端服务')
    }
    setLoading(false)
  }

  // 导出数据
  const handleExport = () => {
    if (filteredPrices.length === 0) return

    const exportData = filteredPrices.map(p => ({
      '日期': p.date || selectedDate,
      '时间': p.time || '',
      '品名': p.material_name || '',
      '规格': p.spec || '',
      '材质': p.material_type || '',
      '品牌/钢厂': p.brand || '',
      '单价(元/吨)': p.price || 0,
      '涨跌': p.price_change || '',
      '备注': p.remark || '',
      '地区': p.region || '山东烟台'
    }))

    const ws = XLSX.utils.json_to_sheet(exportData)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, '钢筋价格')

    XLSX.writeFile(wb, `钢筋价格_${selectedDate}_导出.xlsx`)
    message.success('导出成功！')
  }

  // 计算涨幅分析
  const calculatePriceChange = () => {
    if (!selectedDate || !comparisonDate || !allPrices[selectedDate] || !allPrices[comparisonDate]) {
      return []
    }

    const currentPrices = allPrices[selectedDate]
    const previousPrices = allPrices[comparisonDate]

    const changes: { key: number; brand: string; spec: string; material_name: string; prev: number; curr: number; change: number; changeRate: number }[] = []

    currentPrices.forEach(curr => {
      const prev = previousPrices.find(p => p.brand === curr.brand && p.spec === curr.spec && p.material_name === curr.material_name)
      if (prev) {
        const change = curr.price - prev.price
        const changeRate = prev.price > 0 ? (change / prev.price * 100) : 0
        changes.push({
          key: changes.length,
          brand: curr.brand,
          spec: curr.spec,
          material_name: curr.material_name,
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

  // 筛选后的数据
  const filteredPrices = latestPrices.filter(p => {
    if (filterSpec && p.spec !== filterSpec) return false
    if (filterBrand && p.brand !== filterBrand) return false
    if (filterType && p.material_name !== filterType) return false
    return true
  })

  // 统计
  const stats = {
    total: filteredPrices.length,
    avgPrice: filteredPrices.length > 0
      ? (filteredPrices.reduce((sum, p) => sum + (p.price || 0), 0) / filteredPrices.length).toFixed(0)
      : 0,
    minPrice: filteredPrices.length > 0
      ? Math.min(...filteredPrices.map(p => p.price || 0))
      : 0,
    maxPrice: filteredPrices.length > 0
      ? Math.max(...filteredPrices.map(p => p.price || 0))
      : 0
  }

  const columns = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100, render: (v: string) => v || '-' },
    { title: '时间', dataIndex: 'time', key: 'time', width: 80, render: (v: string) => v || '-' },
    { title: '品名', dataIndex: 'material_name', key: 'material_name', width: 100 },
    { title: '规格', dataIndex: 'spec', key: 'spec', width: 80 },
    { title: '材质', dataIndex: 'material_type', key: 'material_type', width: 100 },
    { title: '品牌/钢厂', dataIndex: 'brand', key: 'brand', width: 120 },
    {
      title: '单价(元/吨)',
      dataIndex: 'price',
      key: 'price',
      width: 120,
      render: (v: number) => v > 0 ? <strong style={{ color: '#1890ff' }}>{v.toLocaleString()}</strong> : '-'
    },
    { title: '涨跌', dataIndex: 'price_change', key: 'price_change', width: 80 },
    { title: '备注', dataIndex: 'remark', key: 'remark', width: 150 },
  ]

  const changeColumns = [
    { title: '品名', dataIndex: 'material_name', width: 100 },
    { title: '品牌', dataIndex: 'brand', width: 100 },
    { title: '规格', dataIndex: 'spec', width: 80 },
    { title: '上期价格', dataIndex: 'prev', width: 100, render: (v: number) => v.toLocaleString() },
    { title: '本期价格', dataIndex: 'curr', width: 100, render: (v: number) => v.toLocaleString() },
    {
      title: '涨跌额',
      dataIndex: 'change',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#f5222d' : v < 0 ? '#52c41a' : '#999'
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v}</span>
      }
    },
    {
      title: '涨跌幅(%)',
      dataIndex: 'changeRate',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#f5222d' : v < 0 ? '#52c41a' : '#999'
        return <span style={{ color, fontWeight: 'bold' }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
      }
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <h2>山东烟台钢筋价格监控</h2>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="数据总数" value={summary.total_count || 0} suffix="条" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="当前筛选"
              value={filteredPrices.length}
              suffix="条"
              valueStyle={{ color: filteredPrices.length < (summary.total_count || 0) ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="均价" value={stats.avgPrice} suffix="元/吨" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="价格区间"
              value={`${stats.minPrice} - ${stats.maxPrice}`}
              suffix="元/吨"
            />
          </Card>
        </Col>
      </Row>

      {/* 日期筛选和筛选条件 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <span><CalendarOutlined /> 日期选择：</span>

          <Select
            placeholder="选择日期"
            style={{ width: 150 }}
            value={selectedDate}
            onChange={(v) => setSelectedDate(v)}
            options={availableDates.map(d => ({
              label: d,
              value: d
            }))}
          />

          <Select
            placeholder="对比日期(涨幅分析)"
            style={{ width: 180 }}
            allowClear
            value={comparisonDate}
            onChange={(v) => setComparisonDate(v)}
            options={availableDates.filter(d => d !== selectedDate).map(d => ({
              label: `对比 ${d}`,
              value: d
            }))}
          />

          {selectedDate && (
            <Tag color="blue" closable onClose={() => setSelectedDate(null)}>
              {selectedDate}
            </Tag>
          )}
        </Space>

        <div style={{ marginBottom: 16 }}>
          <Space wrap style={{ marginBottom: 8 }}>
            <span><FilterOutlined /> 筛选条件：</span>

            <Select
              placeholder="按品牌筛选"
              style={{ width: 150 }}
              allowClear
              value={filterBrand}
              onChange={(v) => handleBrandFilter(v)}
              options={allBrands.map(b => ({ label: b, value: b }))}
            />

            <Select
              placeholder="按品名筛选"
              style={{ width: 120 }}
              allowClear
              value={filterType}
              onChange={(v) => handleTypeFilter(v)}
              options={allTypes.map(t => ({ label: t, value: t }))}
            />

            <Select
              placeholder="按规格筛选"
              style={{ width: 120 }}
              allowClear
              value={filterSpec}
              onChange={(v) => {
                setFilterSpec(v)
                setFilterBrand(null)
                setFilterType(null)
              }}
              options={allSpecs.map(s => ({ label: s, value: s }))}
            />

            <Button onClick={clearFilter}>清除筛选</Button>
          </Space>
        </div>

        <Space wrap>
          <span>品牌统计：</span>
          {allBrands.map(brand => (
            <Tag
              key={brand}
              color={filterBrand === brand ? 'blue' : 'default'}
              style={{ cursor: 'pointer' }}
              onClick={() => handleBrandFilter(filterBrand === brand ? null : brand)}
            >
              {brand} ({summary.brands_detail?.[brand] || 0})
            </Tag>
          ))}
        </Space>

        <div style={{ marginTop: 8 }}>
          <Space wrap>
            <span>品名统计：</span>
            {allTypes.map(type => (
              <Tag
                key={type}
                color={filterType === type ? 'green' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => handleTypeFilter(filterType === type ? null : type)}
              >
                {type} ({summary.material_types?.[type] || 0})
              </Tag>
            ))}
          </Space>
        </div>
      </Card>

      {/* 涨幅分析卡片 */}
      {priceChanges.length > 0 && comparisonDate && (
        <Card
          title={
            <Space>
              <span>涨幅分析</span>
              <Tag color="red">{selectedDate}</Tag>
              <span>vs</span>
              <Tag color="green">{comparisonDate}</Tag>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <Table
            dataSource={priceChanges}
            rowKey="key"
            pagination={{ pageSize: 10 }}
            size="small"
            columns={changeColumns}
          />
        </Card>
      )}

      {/* 价格表格 */}
      <Card
        title={
          <Space>
            <span>价格明细</span>
            {selectedDate && <Tag color="blue">{selectedDate}</Tag>}
            {filterBrand && <Tag color="cyan">{filterBrand}</Tag>}
            {filterType && <Tag color="purple">{filterType}</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => selectedDate && fetchPricesByDate(selectedDate)}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={filteredPrices.length === 0}>
              导出Excel
            </Button>
            <Button type="primary" icon={<SyncOutlined />} onClick={handleFetch} loading={loading}>
              抓取最新
            </Button>
          </Space>
        }
      >
        {initialLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="加载中..." />
          </div>
        ) : filteredPrices.length > 0 ? (
          <Table
            dataSource={filteredPrices.map((p, i) => ({ ...p, key: i }))}
            rowKey="key"
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total: number) => `共 ${total} 条` }}
            columns={columns}
            size="small"
            scroll={{ x: 1200 }}
          />
        ) : (
          <Alert message="暂无数据，请点击「抓取最新」按钮获取数据" type="info" showIcon />
        )}
      </Card>

      {/* 品牌详情 */}
      <Card title="品牌明细统计" style={{ marginTop: 16 }}>
        <Row gutter={16}>
          {Object.entries(summary.brands_detail || {}).map(([brand, count]: [string, any]) => (
            <Col span={4} key={brand}>
              <Card size="small" title={brand}>
                <Statistic value={count as number} suffix="条" valueStyle={{ fontSize: 20 }} />
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  )
}