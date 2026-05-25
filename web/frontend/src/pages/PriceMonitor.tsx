import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Select, message, Spin, Alert, Badge, Tooltip, DatePicker, Empty } from 'antd'
import { SyncOutlined, ReloadOutlined, FilterOutlined, CalendarOutlined, DownloadOutlined, ClockCircleOutlined, RiseOutlined, FallOutlined, LineChartOutlined, DatabaseOutlined, DollarOutlined, SafetyCertificateOutlined, ClearOutlined } from '@ant-design/icons'
import { useState, useEffect, useRef } from 'react'
import { YantaiPrice, fetchApi } from '../services/api'
import * as XLSX from 'xlsx'
import dayjs from 'dayjs'
import { Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, Area, ComposedChart, Brush } from 'recharts'

const { RangePicker } = DatePicker

// API地址 - 从环境变量读取
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// 科技数据卡片组件 - 轻奢高科技风格
const TechCard = ({
  title,
  value,
  suffix,
  icon,
  trend,
  trendValue,
  sub,
  highlight = false
}: {
  title: string
  value: string | number
  suffix?: string
  icon: React.ReactNode
  trend?: 'up' | 'down' | null
  trendValue?: string
  sub?: string
  highlight?: boolean
}) => (
  <div className={highlight ? 'tech-card highlight' : 'tech-card'}>
    <div className="card-accent-line" />
    <div className="tech-card-header">
      <span className="tech-card-title">{title}</span>
      <div className="tech-card-icon">{icon}</div>
    </div>
    <div className={`tech-card-value ${highlight ? 'highlight-number' : 'digital-value'}`}>
      {typeof value === 'number' ? value.toLocaleString() : value}
    </div>
    {suffix && <div className="tech-card-sub" style={{ fontSize: 14, color: '#666' }}>{suffix}</div>}
    {trend && trendValue && (
      <div className={`tech-card-trend ${trend}`}>
        {trend === 'up' ? <RiseOutlined /> : <FallOutlined />}
        <span>{trendValue}</span>
      </div>
    )}
    {sub && <div className="tech-card-sub">{sub}</div>}
  </div>
)

// 趋势数据类型
interface TrendDataItem {
  date: string
  avg_price: number
  min_price: number
  max_price: number
  count: number
}

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

  // 抓取状态
  const [fetchStatus, setFetchStatus] = useState<any>({ am_status: 'pending', pm_status: 'pending' })
  const [schedulerStatus, setSchedulerStatus] = useState<any[]>([])
  const [nextExecution, setNextExecution] = useState<any[]>([])
  const [lastFetchInfo, setLastFetchInfo] = useState<any>(null)

  // WebSocket连接
  const wsRef = useRef<WebSocket | null>(null)

  // 日期筛选
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedSheet, setSelectedSheet] = useState<string | null>(null)
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [dateSheetsMap, setDateSheetsMap] = useState<Record<string, string[]>>({})
  const [comparisonDate, setComparisonDate] = useState<string | null>(null)

  // 日期范围筛选
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null])
  const [isRangeMode, setIsRangeMode] = useState(false)

  // 筛选条件
  const [filterBrand, setFilterBrand] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string | null>(null)
  const [filterSpec, setFilterSpec] = useState<string | null>(null)
  const [filterMaterialType, setFilterMaterialType] = useState<string | null>(null)

  // 所有历史数据汇总
  const [allDataSummary, setAllDataSummary] = useState<any>({
    total_count: 0,
    brands: [],
    material_types: {},
    brands_detail: {}
  })

  // 所有品牌、规格和材质
  const [allBrands, setAllBrands] = useState<string[]>([])
  const [allTypes, setAllTypes] = useState<string[]>([])
  const [allSpecs, setAllSpecs] = useState<string[]>([])
  const [allMaterialTypes, setAllMaterialTypes] = useState<string[]>([])

  // 趋势图数据
  const [trendData, setTrendData] = useState<TrendDataItem[]>([])
  const [trendLoading, setTrendLoading] = useState(false)

  // 刷新触发器
  const [refreshTrigger, setRefreshTrigger] = useState(0)

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

          if (data.type === 'fetch_success') {
            message.success(data.data.message)
            fetchAvailableDates()
            setRefreshTrigger(prev => prev + 1)
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

  // 初始化：获取所有数据
  useEffect(() => {
    const init = async () => {
      try {
        const sheetsRes = await fetch(`${API_URL}/api/price-sources/sheets`)
        const sheetsData = await sheetsRes.json()

        if (sheetsData.success && sheetsData.sheets) {
          const dateSheets = sheetsData.sheets.filter((s: string) => {
            if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return true
            if (/^\d{4}-\d{2}-\d{2}_PM$/.test(s)) return true
            if (/^\d{4}-\d{2}-\d{2}_\d{6}$/.test(s)) return true
            if (/^\d{4}-\d{2}-\d{2}_(AM|PM)_\d{6}$/.test(s)) return true
            return false
          })

          const sheetsMap: Record<string, string[]> = {}
          dateSheets.forEach((sheet: string) => {
            const date = sheet.substring(0, 10)
            if (!sheetsMap[date]) sheetsMap[date] = []
            sheetsMap[date].push(sheet)
          })

          Object.keys(sheetsMap).forEach(date => {
            sheetsMap[date].sort((a, b) => {
              const getSortKey = (s: string) => {
                if (/_PM$/.test(s)) return 1000
                if (s.includes('_PM_')) return 1000
                if (s.includes('_AM_')) return 2000
                return 3000
              }
              const getTimestamp = (s: string) => {
                const match = s.match(/_(\d{6})$/)
                if (match) return parseInt(match[1])
                if (/_PM$/.test(s)) return 1500
                return 3000
              }
              const sortKeyA = getSortKey(a) + getTimestamp(a)
              const sortKeyB = getSortKey(b) + getTimestamp(b)
              return sortKeyB - sortKeyA
            })
          })

          setDateSheetsMap(sheetsMap)
          const uniqueDates = Object.keys(sheetsMap).sort().reverse()
          setAvailableDates(uniqueDates)

          // 获取所有历史数据汇总
          await fetchAllDataSummary()

          if (uniqueDates.length > 0) {
            const latestDate = uniqueDates[0]
            setSelectedDate(latestDate)
            const latestSheet = sheetsMap[latestDate]?.[0] || null
            setSelectedSheet(latestSheet)

            await fetchPricesByDate(latestDate, latestSheet)
          }

          // 获取趋势数据
          await fetchTrendData()
        }
        setInitialLoading(false)
      } catch (error) {
        console.error('初始化失败:', error)
        setInitialLoading(false)
      }
    }
    init()
  }, [])

  // 响应刷新触发器
  useEffect(() => {
    if (refreshTrigger > 0) {
      // 根据当前筛选模式刷新数据
      if (isRangeMode && dateRange[0] && dateRange[1]) {
        const startDate = dateRange[0].format('YYYY-MM-DD')
        const endDate = dateRange[1].format('YYYY-MM-DD')
        fetchPricesByDateRange(startDate, endDate)
        fetchTrendData(startDate, endDate)
      } else if (selectedDate) {
        fetchPricesByDate(selectedDate, selectedSheet)
        // 单日模式刷新趋势图（显示当前日期范围的数据）
        fetchTrendData()
      }
      fetchStatusData()
      fetchLastFetchInfo()
    }
  }, [refreshTrigger])

  // 选择日期变化时重新获取数据
  useEffect(() => {
    if (selectedDate && !isRangeMode) {
      fetchPricesByDate(selectedDate, selectedSheet)
    }
  }, [selectedDate, isRangeMode])

  // 获取所有可用的日期
  const fetchAvailableDates = async () => {
    try {
      const response = await fetch(`${API_URL}/api/price-sources/sheets`)
      const data = await response.json()
      if (data.success && data.sheets) {
        const dateSheets = data.sheets.filter((s: string) => {
          if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return true
          if (/^\d{4}-\d{2}-\d{2}_PM$/.test(s)) return true
          if (/^\d{4}-\d{2}-\d{2}_\d{6}$/.test(s)) return true
          if (/^\d{4}-\d{2}-\d{2}_(AM|PM)_\d{6}$/.test(s)) return true
          return false
        })

        const sheetsMap: Record<string, string[]> = {}
        dateSheets.forEach((sheet: string) => {
          const date = sheet.substring(0, 10)
          if (!sheetsMap[date]) {
            sheetsMap[date] = []
          }
          sheetsMap[date].push(sheet)
        })

        Object.keys(sheetsMap).forEach(date => {
          sheetsMap[date].sort((a, b) => {
            const getSortKey = (s: string) => {
              if (/_PM$/.test(s)) return 1000
              if (s.includes('_PM_')) return 1000
              if (s.includes('_AM_')) return 2000
              return 3000
            }
            const getTimestamp = (s: string) => {
              const match = s.match(/_(\d{6})$/)
              if (match) return parseInt(match[1])
              if (/_PM$/.test(s)) return 1500
              return 3000
            }
            const sortKeyA = getSortKey(a) + getTimestamp(a)
            const sortKeyB = getSortKey(b) + getTimestamp(b)
            return sortKeyB - sortKeyA
          })
        })

        setDateSheetsMap(sheetsMap)

        const uniqueDates = Object.keys(sheetsMap).sort().reverse()
        setAvailableDates(uniqueDates)

        if (uniqueDates.length > 0 && !selectedDate) {
          const latestDate = uniqueDates[0]
          setSelectedDate(latestDate)
          const latestSheet = sheetsMap[latestDate][0]
          setSelectedSheet(latestSheet)
          if (uniqueDates.length > 1) {
            setComparisonDate(uniqueDates[1])
          }
        }
      }
    } catch (error) {
      console.error('获取日期列表失败:', error)
    }
  }

  // 获取所有历史数据汇总
  const fetchAllDataSummary = async () => {
    try {
      const response = await fetch(`${API_URL}/api/yantai-prices/summary?include_all=true`)
      const data = await response.json()
      setAllDataSummary(data)
    } catch (error) {
      console.error('获取汇总失败:', error)
    }
  }

  // 获取趋势数据
  const fetchTrendData = async (startDate?: string, endDate?: string) => {
    setTrendLoading(true)
    try {
      let url = `${API_URL}/api/yantai-prices/trend?days=730`  // 默认获取2年数据
      if (startDate && endDate) {
        url = `${API_URL}/api/yantai-prices/trend?start_date=${startDate}&end_date=${endDate}`
      } else if (startDate) {
        url = `${API_URL}/api/yantai-prices/trend?start_date=${startDate}&days=730`
      }
      const response = await fetch(url)
      const data = await response.json()
      if (data.success && data.data) {
        setTrendData(data.data)
      }
    } catch (error) {
      console.error('获取趋势数据失败:', error)
    }
    setTrendLoading(false)
  }

  // 获取抓取状态
  const fetchStatusData = async () => {
    try {
      const response = await fetch(`${API_URL}/api/fetch/status`)
      const data = await response.json()
      setFetchStatus(data)
    } catch (error) {
      console.error('获取抓取状态失败:', error)
    }
  }

  // 获取调度器状态
  const fetchSchedulerStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/scheduler/status`)
      const data = await response.json()
      if (Array.isArray(data)) {
        setSchedulerStatus(data)
      }
    } catch (error) {
      console.error('获取调度器状态失败:', error)
    }
  }

  // 获取下次执行时间
  const fetchNextExecution = async () => {
    try {
      const response = await fetch(`${API_URL}/api/scheduler/next-execution`)
      const data = await response.json()
      if (data.next_executions) {
        setNextExecution(data.next_executions)
      }
    } catch (error) {
      console.error('获取下次执行时间失败:', error)
    }
  }

  // 获取上次抓取信息
  const fetchLastFetchInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/api/cron/status`)
      const data = await response.json()
      setLastFetchInfo(data)
    } catch (error) {
      console.error('获取上次抓取信息失败:', error)
    }
  }

  // 手动触发抓取
  const handleManualFetch = async () => {
    message.info('请先登录网站并导出Cookie，然后通过 POST /api/fetch/manual 接口提交')
    try {
      const guide = await fetchApi.getCookieGuide()
      console.log('Cookie导出指南:', guide)
    } catch (error) {
      console.error('获取Cookie指南失败:', error)
    }
  }

  // 自动抓取
  const handleAutoFetch = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/cron/force-fetch`, { method: 'POST' })
      const data = await response.json()

      if (data.success) {
        message.success(data.message)
        fetchAvailableDates()
        fetchLastFetchInfo()
        fetchStatusData()
        fetchAllDataSummary()
        // 根据当前筛选模式刷新数据
        if (isRangeMode && dateRange[0] && dateRange[1]) {
          const startDate = dateRange[0].format('YYYY-MM-DD')
          const endDate = dateRange[1].format('YYYY-MM-DD')
          fetchPricesByDateRange(startDate, endDate)
          fetchTrendData(startDate, endDate)
        } else if (selectedDate) {
          fetchPricesByDate(selectedDate, selectedSheet)
          fetchTrendData()
        } else {
          fetchTrendData()
        }
      } else {
        message.error(data.message || '自动抓取失败')
      }
    } catch (error) {
      console.error('自动抓取失败:', error)
      message.error('自动抓取失败，请检查后端服务')
    }
    setLoading(false)
  }

  const fetchPricesByDate = async (date: string, sheet: string | null = null) => {
    setInitialLoading(true)
    try {
      const targetSheet = sheet || (dateSheetsMap[date] ? dateSheetsMap[date][0] : null)
      if (!targetSheet) {
        setLatestPrices([])
        setInitialLoading(false)
        return
      }

      setSelectedSheet(targetSheet)

      const url = `${API_URL}/api/yantai-prices/latest?date=${date}&sheet=${targetSheet}`
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

      updateFiltersAndSummary(prices)

    } catch (error) {
      console.error('获取价格失败:', error)
      setLatestPrices([])
    }
    setInitialLoading(false)
  }

  // 按日期范围获取价格
  const fetchPricesByDateRange = async (startDate: string, endDate: string) => {
    setInitialLoading(true)
    setLoading(true)
    try {
      const url = `${API_URL}/api/yantai-prices/range?start_date=${startDate}&end_date=${endDate}`
      const response = await fetch(url)
      const data = await response.json()

      if (data.success && data.prices && data.prices.length > 0) {
        setLatestPrices(data.prices)

        // 按日期分组存储
        const pricesByDate: { [date: string]: YantaiPrice[] } = {}
        data.prices.forEach((p: YantaiPrice) => {
          const date = p.date || ''
          if (!pricesByDate[date]) {
            pricesByDate[date] = []
          }
          pricesByDate[date].push(p)
        })
        setAllPrices(pricesByDate)

        updateFiltersAndSummary(data.prices)

        // 同时获取该范围的趋势数据
        fetchTrendData(startDate, endDate)

        message.success(`已加载 ${data.dates?.length || 0} 个交易日，共 ${data.prices.length} 条记录`)
      } else {
        setLatestPrices([])
        const rangeInfo = data.date_range
        if (rangeInfo?.start && rangeInfo?.end) {
          message.warning({
            content: (
              <div>
                <div>该日期范围内暂无数据</div>
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  当前数据范围：{rangeInfo.start} 至 {rangeInfo.end}
                </div>
              </div>
            ),
            duration: 5
          })
        } else {
          message.warning('该日期范围内暂无数据，请检查数据是否已抓取')
        }
      }
    } catch (error) {
      console.error('获取价格失败:', error)
      setLatestPrices([])
      message.error('获取价格数据失败，请检查网络连接')
    }
    setInitialLoading(false)
    setLoading(false)
  }

  // 更新筛选条件和汇总数据
  const updateFiltersAndSummary = (prices: YantaiPrice[]) => {
    const specs = [...new Set<string>(prices.map((p: YantaiPrice) => p.spec).filter(Boolean) as string[])].sort()
    const brands = [...new Set<string>(prices.map((p: YantaiPrice) => p.brand).filter(Boolean) as string[])].sort()
    const types = [...new Set<string>(prices.map((p: YantaiPrice) => p.material_name).filter(Boolean) as string[])].sort()
    const materialTypes = [...new Set<string>(prices.map((p: YantaiPrice) => p.material_type).filter(Boolean) as string[])].sort()

    setAllSpecs(specs)
    setAllBrands(brands)
    setAllTypes(types)
    setAllMaterialTypes(materialTypes)

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

  // 处理日期范围变化
  const handleDateRangeChange = (dates: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    if (!dates) {
      setDateRange([null, null])
      setIsRangeMode(false)
      if (availableDates.length > 0) {
        const latestDate = availableDates[0]
        setSelectedDate(latestDate)
        fetchPricesByDate(latestDate, dateSheetsMap[latestDate]?.[0] || null)
        fetchTrendData()
      }
      return
    }

    setDateRange(dates)

    if (dates[0] && dates[1]) {
      setIsRangeMode(true)
      setSelectedDate(null)
      setSelectedSheet(null)
      const startDate = dates[0].format('YYYY-MM-DD')
      const endDate = dates[1].format('YYYY-MM-DD')
      fetchPricesByDateRange(startDate, endDate)
      // 同时获取该日期范围的趋势数据
      fetchTrendData(startDate, endDate)
    }
  }

  // 清除日期范围
  const clearDateRange = () => {
    setDateRange([null, null])
    setIsRangeMode(false)
    if (availableDates.length > 0) {
      const latestDate = availableDates[0]
      setSelectedDate(latestDate)
      fetchPricesByDate(latestDate, dateSheetsMap[latestDate]?.[0] || null)
      fetchTrendData()
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
    setFilterMaterialType(null)
  }

  // 按材质筛选
  const handleMaterialTypeFilter = (type: string | null) => {
    setFilterMaterialType(type)
    setFilterBrand(null)
    setFilterType(null)
    setFilterSpec(null)
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

    const fileName = isRangeMode && dateRange[0] && dateRange[1]
      ? `钢筋价格_${dateRange[0].format('YYYY-MM-DD')}_至_${dateRange[1].format('YYYY-MM-DD')}_导出.xlsx`
      : `钢筋价格_${selectedDate}_导出.xlsx`

    XLSX.writeFile(wb, fileName)
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
    if (filterMaterialType && p.material_type !== filterMaterialType) return false
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

  // 趋势图配置

  // 计算趋势统计
  const trendStats = {
    max: trendData.length > 0 ? Math.max(...trendData.map(d => d.max_price)) : 0,
    min: trendData.length > 0 ? Math.min(...trendData.map(d => d.min_price)) : 0,
    avg: trendData.length > 0 ? (trendData.reduce((sum, d) => sum + d.avg_price, 0) / trendData.length).toFixed(0) : 0,
    count: trendData.length
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
      render: (v: number) => v > 0 ? <strong style={{ color: '#16325C', fontWeight: 600 }}>{v.toLocaleString()}</strong> : '-'
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
        const color = v > 0 ? '#EF4444' : v < 0 ? '#10B981' : '#999'
        return <span style={{ color }}>{v > 0 ? '+' : ''}{v}</span>
      }
    },
    {
      title: '涨跌幅(%)',
      dataIndex: 'changeRate',
      width: 100,
      render: (v: number) => {
        const color = v > 0 ? '#EF4444' : v < 0 ? '#10B981' : '#999'
        return <span style={{ color, fontWeight: 'bold' }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</span>
      }
    }
  ]

  // 禁止选择未来日期
  const disabledDate = (current: dayjs.Dayjs) => {
    return current && current > dayjs().endOf('day')
  }

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <div className="page-header">
        <h2 className="page-title">山东烟台钢筋价格监控</h2>
        <p className="page-subtitle">实时监控市场价格动态，支持多维度筛选与对比分析</p>
      </div>

      {/* 抓取状态面板 */}
      <div className="data-section" style={{ marginBottom: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <SafetyCertificateOutlined />
            <span>数据采集状态</span>
          </div>
        </div>
        <div className="data-section-body">
          <Row gutter={[24, 16]} align="middle">
            <Col span={6}>
              <Space direction="vertical" size="small">
                <span style={{ fontWeight: 500, color: '#666', fontSize: 13 }}>上午场</span>
                <div className="status-badge success">
                  <span className="status-dot" />
                  <span>{fetchStatus.am_status === 'success' ? '已抓取' : fetchStatus.am_status === 'running' ? '抓取中' : fetchStatus.am_status === 'failed' ? '失败' : '待抓取'}</span>
                </div>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size="small">
                <span style={{ fontWeight: 500, color: '#666', fontSize: 13 }}>下午场</span>
                <div className="status-badge success">
                  <span className="status-dot" />
                  <span>{fetchStatus.pm_status === 'success' ? '已抓取' : fetchStatus.pm_status === 'running' ? '抓取中' : fetchStatus.pm_status === 'failed' ? '失败' : '待抓取'}</span>
                </div>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size="small">
                <span style={{ fontWeight: 500, color: '#666', fontSize: 13 }}>最近抓取</span>
                <Space>
                  <ClockCircleOutlined style={{ color: '#4A86C8' }} />
                  <span>{lastFetchInfo?.last_fetch ? lastFetchInfo.last_fetch.slice(0, 19).replace('T', ' ') : '暂无记录'}</span>
                  {lastFetchInfo?.success && lastFetchInfo?.prices_count > 0 && (
                    <Tag color="#4A86C8">{lastFetchInfo.prices_count}条</Tag>
                  )}
                </Space>
              </Space>
            </Col>
            <Col span={6}>
              <Space direction="vertical" size="small">
                <span style={{ fontWeight: 500, color: '#666', fontSize: 13 }}>下次执行</span>
                <Space>
                  <ClockCircleOutlined style={{ color: '#10B981' }} />
                  <span>{nextExecution.length > 0 ? nextExecution[0]?.next_fetch?.slice(0, 16).replace('T', ' ') : '未安排'}</span>
                </Space>
              </Space>
            </Col>
          </Row>
        </div>
      </div>

      {/* 科技统计卡片 */}
      <div className="stats-grid">
        <TechCard
          title="历史数据总量"
          value={allDataSummary.total_count || 0}
          suffix="条记录"
          icon={<DatabaseOutlined />}
          sub={`覆盖 ${availableDates.length} 个交易日`}
          highlight
        />
        <TechCard
          title="当前数据"
          value={summary.total_count || 0}
          suffix="条"
          icon={<LineChartOutlined />}
        />
        <TechCard
          title="筛选结果"
          value={filteredPrices.length}
          suffix="条"
          icon={<FilterOutlined />}
          sub={filteredPrices.length < (summary.total_count || 0) ? `已过滤 ${(summary.total_count || 0) - filteredPrices.length} 条` : '未过滤'}
        />
        <TechCard
          title="市场均价"
          value={stats.avgPrice}
          suffix="元/吨"
          icon={<DollarOutlined />}
          sub={`区间: ${stats.minPrice} - ${stats.maxPrice}`}
        />
      </div>

      {/* 可用数据范围提示 */}
      {availableDates.length > 0 && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(74, 134, 200, 0.08) 0%, rgba(74, 134, 200, 0.02) 100%)',
          border: '1px solid rgba(74, 134, 200, 0.2)',
          borderRadius: 10,
          padding: '12px 16px',
          marginBottom: 24,
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <CalendarOutlined style={{ color: '#4A86C8', fontSize: 16 }} />
          <span style={{ color: '#666', fontSize: 13 }}>
            <strong style={{ color: '#16325C' }}>可用数据范围：</strong>
            {availableDates[availableDates.length - 1]} 至 {availableDates[0]}
            <span style={{ color: '#999', marginLeft: 8 }}>(共 {availableDates.length} 个交易日)</span>
          </span>
        </div>
      )}

      {/* 价格走势图 - 新增 */}
      <div className="chart-container" style={{ marginBottom: 24 }}>
        <div className="chart-title">
          <LineChartOutlined />
          <span>价格走势分析</span>
          {isRangeMode && dateRange[0] && dateRange[1] && (
            <Tag color="#4A86C8" style={{ marginLeft: 8 }}>
              {dateRange[0].format('MM-DD')} 至 {dateRange[1].format('MM-DD')}
            </Tag>
          )}
          <Button
            type="link"
            icon={<SyncOutlined spin={trendLoading} />}
            onClick={() => {
              if (isRangeMode && dateRange[0] && dateRange[1]) {
                fetchTrendData(dateRange[0].format('YYYY-MM-DD'), dateRange[1].format('YYYY-MM-DD'))
              } else {
                fetchTrendData()
              }
            }}
            size="small"
            style={{ marginLeft: 'auto', color: '#4A86C8' }}
          >
            刷新
          </Button>
        </div>

        {/* 趋势统计 */}
        {trendData.length > 0 && (
          <Row gutter={24} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>最高价</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#EF4444' }}>{trendStats.max.toLocaleString()}</div>
                <div style={{ fontSize: 11, color: '#999' }}>元/吨</div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>最低价</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#10B981' }}>{trendStats.min.toLocaleString()}</div>
                <div style={{ fontSize: 11, color: '#999' }}>元/吨</div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>平均价</div>
                <div style={{ fontSize: 22, fontWeight: 700, background: 'linear-gradient(135deg, #16325C, #4A86C8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{trendStats.avg}</div>
                <div style={{ fontSize: 11, color: '#999' }}>元/吨</div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>交易日数</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#16325C' }}>{trendStats.count}</div>
                <div style={{ fontSize: 11, color: '#999' }}>天</div>
              </div>
            </Col>
          </Row>
        )}

        {/* 图表 - Recharts 折线图 */}
        <div style={{ height: 350, position: 'relative' }}>
          {trendLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <Spin tip="加载趋势数据..." />
            </div>
          ) : trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="priceAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4A86C8" stopOpacity={0.15}/>
                    <stop offset="95%" stopColor="#4A86C8" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8EBF0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: '#666' }}
                  tickFormatter={(v) => v.slice(5)}
                  interval="preserveStartEnd"
                />
                <YAxis
                  tick={{ fontSize: 11, fill: '#666' }}
                  tickFormatter={(v) => v.toLocaleString()}
                  domain={['auto', 'auto']}
                />
                <RechartsTooltip
                  contentStyle={{
                    background: 'linear-gradient(135deg, #16325C 0%, #1a4080 100%)',
                    border: '1px solid #4A86C8',
                    borderRadius: 8,
                    boxShadow: '0 4px 12px rgba(22, 50, 92, 0.3)',
                  }}
                  labelStyle={{ color: '#fff', fontSize: 13 }}
                  formatter={(value, name) => {
                    const numValue = Number(value)
                    const config: Record<string, { label: string; color: string }> = {
                      avg_price: { label: '均价', color: '#4A86C8' },
                      min_price: { label: '最低价', color: '#10B981' },
                      max_price: { label: '最高价', color: '#EF4444' }
                    }
                    const item = config[name as string] || { label: name as string, color: '#fff' }
                    return [
                      <span style={{ color: item.color, fontWeight: 600 }}>{numValue.toLocaleString()} 元/吨</span>,
                      item.label
                    ]
                  }}
                  labelFormatter={(v) => `日期: ${v}`}
                />
                <Legend
                  formatter={(v: string) => ({ avg_price: '均价', min_price: '最低', max_price: '最高' }[v] || v)}
                  iconType="circle"
                  iconSize={8}
                />
                {/* 价格区间渐变填充 */}
                <Area
                  type="monotone"
                  dataKey="max_price"
                  stroke="none"
                  fill="url(#priceAreaGradient)"
                />
                {/* 最高价虚线 */}
                <Line
                  type="monotone"
                  dataKey="max_price"
                  stroke="#EF4444"
                  strokeWidth={1}
                  strokeDasharray="4 2"
                  dot={false}
                  legendType="none"
                />
                {/* 最低价虚线 */}
                <Line
                  type="monotone"
                  dataKey="min_price"
                  stroke="#10B981"
                  strokeWidth={1}
                  strokeDasharray="4 2"
                  dot={false}
                  legendType="none"
                />
                {/* 均价折线 */}
                <Line
                  type="monotone"
                  dataKey="avg_price"
                  stroke="#4A86C8"
                  strokeWidth={3}
                  dot={{ fill: '#4A86C8', strokeWidth: 2, stroke: '#fff', r: 4 }}
                  activeDot={{ r: 6, fill: '#4A86C8', stroke: '#fff', strokeWidth: 2 }}
                />
                <Brush
                  dataKey="date"
                  height={30}
                  stroke="#4A86C8"
                  fill="#F8FAFC"
                  tickFormatter={(v) => v.slice(5)}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <Empty
              description="暂无趋势数据"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ padding: 60 }}
            />
          )}
        </div>

        {/* 提示 */}
        {trendData.length > 0 && (
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginTop: 12,
            paddingTop: 12,
            borderTop: '1px solid #E8EBF0',
            fontSize: 12,
            color: '#999'
          }}>
            <span>展示 {trendData.length} 个交易日价格走势</span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 2, background: '#4A86C8', borderRadius: 1 }} />
                均价
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 1, borderTop: '2px dashed #EF4444' }} />
                最高价
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 12, height: 1, borderTop: '2px dashed #10B981' }} />
                最低价
              </span>
              <span style={{ color: '#4A86C8' }}>拖动底部滑块缩放</span>
            </span>
          </div>
        )}
      </div>

      {/* 日期筛选和筛选条件 */}
      <div className="data-section" style={{ marginBottom: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <CalendarOutlined />
            <span>数据筛选</span>
            {isRangeMode && dateRange[0] && dateRange[1] && (
              <Tag color="#4A86C8" style={{ marginLeft: 8 }}>
                {dateRange[0].format('YYYY-MM-DD')} 至 {dateRange[1].format('YYYY-MM-DD')}
              </Tag>
            )}
          </div>
          <Space className="btn-group-tech">
            <Button
              icon={<SyncOutlined spin={loading} />}
              onClick={handleAutoFetch}
              loading={loading}
            >
              强制抓取
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={filteredPrices.length === 0}>
              导出数据
            </Button>
          </Space>
        </div>
        <div className="data-section-body">
          {/* 日期范围选择 */}
          <div className="filter-bar search-input-highlight" style={{ background: 'linear-gradient(135deg, #FAFBFC 0%, #F8FAFC 100%)', border: '1px solid #E8EBF0', marginBottom: 16 }}>
            <div className="filter-item">
              <span className="filter-label"><CalendarOutlined /> 时间范围</span>
              <RangePicker
                value={dateRange}
                onChange={handleDateRangeChange}
                disabledDate={disabledDate}
                style={{ width: 260 }}
                placeholder={['开始日期', '结束日期']}
              />
              {isRangeMode && (
                <Button
                  type="text"
                  icon={<ClearOutlined />}
                  size="small"
                  onClick={clearDateRange}
                  style={{ color: '#999' }}
                >
                  清除
                </Button>
              )}
            </div>

            {/* 单日期选择 - 非范围模式时显示 */}
            {!isRangeMode && (
              <>
                <div className="filter-item">
                  <span className="filter-label"><CalendarOutlined /> 单日选择</span>
                  <Select
                    placeholder="选择日期"
                    style={{ width: 160 }}
                    value={selectedDate}
                    onChange={(v) => {
                      setSelectedDate(v)
                      if (v) {
                        const latestSheet = dateSheetsMap[v] ? dateSheetsMap[v][0] : null
                        setSelectedSheet(latestSheet)
                        fetchPricesByDate(v, latestSheet)
                        // 单日模式：显示该日期往前的所有历史数据
                        fetchTrendData(undefined, v)
                      }
                    }}
                    options={availableDates.map(d => {
                      const labels = dateSheetsMap[d]?.map(s => s.includes('_PM_') ? '下午' : '上午').join('+') || ''
                      return {
                        label: `${d} (${labels})`,
                        value: d
                      }
                    })}
                  />
                </div>

                {/* AM/PM 选择器 */}
                {selectedDate && dateSheetsMap[selectedDate] && dateSheetsMap[selectedDate].length > 1 && (
                  <div className="filter-item">
                    <span className="filter-label">时段</span>
                    <Select
                      style={{ width: 120 }}
                      value={selectedSheet}
                      onChange={(v) => {
                        setSelectedSheet(v)
                        fetchPricesByDate(selectedDate!, v)
                      }}
                      options={dateSheetsMap[selectedDate].map(s => {
                        const period = s.includes('_PM_') ? '下午' : '上午'
                        const time = s.split('_').pop()
                        return {
                          label: `${period} (${time})`,
                          value: s
                        }
                      })}
                    />
                  </div>
                )}

                <div className="filter-item">
                  <span className="filter-label">对比日期</span>
                  <Select
                    style={{ width: 160 }}
                    allowClear
                    placeholder="选择对比日期"
                    value={comparisonDate}
                    onChange={(v) => setComparisonDate(v)}
                    options={availableDates.filter(d => d !== selectedDate).map(d => ({
                      label: `对比 ${d}`,
                      value: d
                    }))}
                  />
                </div>
              </>
            )}
          </div>

          {/* 筛选条件 */}
          <Space wrap size={[8, 8]} style={{ marginBottom: 16 }}>
            <span style={{ color: '#666', fontWeight: 500 }}><FilterOutlined /> 快速筛选</span>
            <Select
              placeholder="按品牌"
              style={{ width: 140 }}
              allowClear
              value={filterBrand}
              onChange={(v) => handleBrandFilter(v)}
              options={allBrands.map(b => ({ label: b, value: b }))}
            />
            <Select
              placeholder="按品名"
              style={{ width: 120 }}
              allowClear
              value={filterType}
              onChange={(v) => handleTypeFilter(v)}
              options={allTypes.map(t => ({ label: t, value: t }))}
            />
            <Select
              placeholder="按规格"
              style={{ width: 110 }}
              allowClear
              value={filterSpec}
              onChange={(v) => {
                setFilterSpec(v)
                setFilterBrand(null)
                setFilterType(null)
                setFilterMaterialType(null)
              }}
              options={allSpecs.map(s => ({ label: s, value: s }))}
            />
            <Button onClick={clearFilter} size="small">清除筛选</Button>
          </Space>

          {/* 品牌标签云 */}
          <div style={{ marginBottom: 12 }}>
            <span style={{ color: '#666', fontSize: 13, marginBottom: 8, display: 'block', fontWeight: 500 }}>品牌统计</span>
            <div className="tag-cloud">
              {allBrands?.map((brand: string) => (
                <span
                  key={brand}
                  className={`tag-cloud-item ${filterBrand === brand ? 'active' : ''}`}
                  onClick={() => handleBrandFilter(filterBrand === brand ? null : brand)}
                >
                  {brand}
                </span>
              ))}
            </div>
          </div>

          {/* 品名标签云 */}
          <div>
            <span style={{ color: '#666', fontSize: 13, marginBottom: 8, display: 'block', fontWeight: 500 }}>品名统计</span>
            <div className="tag-cloud">
              {Object.entries(summary.material_types || {}).map(([type, count]: [string, any]) => (
                <span
                  key={type}
                  className={`tag-cloud-item ${filterType === type ? 'active' : ''}`}
                  onClick={() => handleTypeFilter(filterType === type ? null : type)}
                >
                  {type} ({count})
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 涨幅分析 */}
      {!isRangeMode && priceChanges.length > 0 && comparisonDate && (
        <div className="data-section" style={{ marginBottom: 24 }}>
          <div className="data-section-header">
            <div className="data-section-title">
              {priceChanges[0]?.change > 0 ? <RiseOutlined style={{ color: '#EF4444' }} /> : <FallOutlined style={{ color: '#10B981' }} />}
              <span>价格涨幅分析</span>
              <Tag color={priceChanges[0]?.change > 0 ? 'red' : 'green'}>{selectedDate}</Tag>
              <span style={{ color: '#999' }}>对比</span>
              <Tag color="blue">{comparisonDate}</Tag>
            </div>
          </div>
          <div className="data-section-body">
            <Table
              dataSource={priceChanges}
              rowKey="key"
              pagination={{ pageSize: 10 }}
              size="small"
              columns={changeColumns}
            />
          </div>
        </div>
      )}

      {/* 价格明细表格 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <LineChartOutlined />
            <span>价格明细</span>
            {isRangeMode && dateRange[0] && dateRange[1] ? (
              <Tag color="#4A86C8" style={{ marginLeft: 8 }}>
                {dateRange[0].format('YYYY-MM-DD')} 至 {dateRange[1].format('YYYY-MM-DD')}
              </Tag>
            ) : selectedDate && (
              <>
                <Tag color="#4A86C8" style={{ marginLeft: 8 }}>{selectedDate}</Tag>
                {selectedSheet && (
                  <Tag color={selectedSheet.includes('_PM_') ? '#EF4444' : '#10B981'}>
                    {selectedSheet.includes('_PM_') ? '下午' : '上午'}
                  </Tag>
                )}
              </>
            )}
          </div>
          <Space className="btn-group-tech">
            <Button icon={<ReloadOutlined />} onClick={() => {
              if (isRangeMode && dateRange[0] && dateRange[1]) {
                fetchPricesByDateRange(dateRange[0].format('YYYY-MM-DD'), dateRange[1].format('YYYY-MM-DD'))
              } else if (selectedDate) {
                fetchPricesByDate(selectedDate, selectedSheet)
              }
            }}>
              刷新
            </Button>
            <Button icon={<SyncOutlined spin={loading} />} onClick={handleAutoFetch} loading={loading}>
              抓取最新
            </Button>
          </Space>
        </div>
        <div className="data-section-body">
          {initialLoading ? (
            <div className="page-loading">
              <Spin tip="数据加载中..." size="large" />
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
        </div>
      </div>
    </div>
  )
}