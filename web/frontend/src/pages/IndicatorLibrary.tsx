/**
 * 指标库管理主页面
 * Master-detail layout: 左侧摘要列表 (35%) + 右侧详情面板 (65%)
 */
import { useState, useEffect, useCallback } from 'react'
import { Layout, Button, Space, message, Spin, Card, Typography } from 'antd'
import { PlusOutlined, UploadOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import PageHeader from '../components/PageHeader'

// 导入子组件（将在后续任务中实现）
import SummaryList from '../components/indicator-library/SummaryList'
import DetailPanel from '../components/indicator-library/DetailPanel'
import ImportPreview from '../components/indicator-library/ImportPreview'

// API 类型占位符 - 后续将从 api.ts 导入
// import { indicatorLibraryAPI } from '../services/api'

// ============================================================================
// 类型定义
// ============================================================================

/** 指标库摘要项 */
export interface IndicatorSummary {
  id: string
  name: string
  category: string
  location: string
  structure: string
  unit_cost?: number
  area_total?: number
  height?: number
  floor_above?: number
  floor_below?: number
  verified?: boolean
  created_at?: string
  updated_at?: string
}

/** 指标库详情 */
export interface IndicatorDetail extends IndicatorSummary {
  // 造价指标
  total_cost?: number
  unit_structure?: number
  unit_installation?: number
  unit_decoration?: number
  unit_measure?: number
  // 经济指标
  underground_structure?: number
  above_structure?: number
  roof?: number
  exterior_wall?: number
  interior_wall?: number
  floor?: number
  electrical?: number
  plumbing?: number
  hvac?: number
  elevator?: number
  fire?: number
  measures?: number
  // 材料含量
  steel?: number
  concrete?: number
  formwork?: number
  block?: number
  cable?: number
  pipe?: number
  duct?: number
  // 附加信息
  source?: string
  source_file?: string
  remarks?: string
  verified_by?: string
  verified_at?: string
}

/** 筛选条件 */
export interface IndicatorFilters {
  search_text?: string
  category?: string
  location?: string
  delivery_type?: string
  start_date_from?: string
  start_date_to?: string
  end_date_from?: string
  end_date_to?: string
}

/** API 响应类型 */
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// ============================================================================
// 占位符 API（后续替换为实际实现）
// ============================================================================

/** 指标库 API 占位符 */
const indicatorLibraryAPI = {
  /** 获取摘要列表 */
  getSummary: async (filters?: IndicatorFilters): Promise<IndicatorSummary[]> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] getSummary', filters)
    // 模拟数据
    return []
  },

  /** 获取详情 */
  getDetail: async (id: string): Promise<IndicatorDetail | null> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] getDetail', id)
    return null
  },

  /** 创建指标 */
  create: async (data: Partial<IndicatorDetail>): Promise<IndicatorSummary> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] create', data)
    return {} as IndicatorSummary
  },

  /** 更新指标 */
  update: async (id: string, data: Partial<IndicatorDetail>): Promise<IndicatorSummary> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] update', id, data)
    return {} as IndicatorSummary
  },

  /** 删除指标 */
  delete: async (id: string): Promise<void> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] delete', id)
  },

  /** 导入指标 */
  import: async (file: File): Promise<{ success: boolean; imported: number; failed: number }> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] import', file.name)
    return { success: true, imported: 0, failed: 0 }
  },

  /** 导出指标 */
  export: async (filters?: IndicatorFilters): Promise<Blob> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] export', filters)
    return new Blob()
  },

  /** 预览导入数据 */
  previewImport: async (file: File): Promise<IndicatorDetail[]> => {
    // TODO: 替换为实际 API 调用
    console.log('[IndicatorLibrary] previewImport', file.name)
    return []
  },
}

// ============================================================================
// 组件定义
// ============================================================================

const { Content, Sider } = Layout
const { Title } = Typography

export default function IndicatorLibrary() {
  // -------------------------------------------------------------------------
  // 状态管理
  // -------------------------------------------------------------------------

  /** 摘要列表数据 */
  const [summaryList, setSummaryList] = useState<IndicatorSummary[]>([])

  /** 当前选中的指标 ID */
  const [selectedId, setSelectedId] = useState<string | null>(null)

  /** 当前选中的指标详情 */
  const [selectedDetail, setSelectedDetail] = useState<IndicatorDetail | null>(null)

  /** 加载状态 */
  const [loading, setLoading] = useState(false)

  /** 导入预览弹窗可见性 */
  const [importVisible, setImportVisible] = useState(false)

  /** 导入预览数据 */
  const [importPreviewData, setImportPreviewData] = useState<IndicatorDetail[]>([])

  /** 筛选条件 */
  const [filters, setFilters] = useState<IndicatorFilters>({
    search_text: '',
    category: undefined,
    location: undefined,
    delivery_type: undefined,
    start_date_from: undefined,
    start_date_to: undefined,
    end_date_from: undefined,
    end_date_to: undefined,
  })

  /** 文件上传 input ref */
  const fileInputRef = useState<HTMLInputElement | null>(null)

  // -------------------------------------------------------------------------
  // 数据加载
  // -------------------------------------------------------------------------

  /**
   * 加载摘要列表
   */
  const loadSummaryList = useCallback(async () => {
    setLoading(true)
    try {
      const data = await indicatorLibraryAPI.getSummary(filters)
      setSummaryList(data)
      message.success(`加载成功，共 ${data.length} 条记录`)
    } catch (error) {
      console.error('[IndicatorLibrary] 加载摘要列表失败:', error)
      message.error('加载摘要列表失败')
    } finally {
      setLoading(false)
    }
  }, [filters])

  /**
   * 加载指标详情
   */
  const loadDetail = useCallback(async (id: string) => {
    setLoading(true)
    try {
      const detail = await indicatorLibraryAPI.getDetail(id)
      setSelectedDetail(detail)
    } catch (error) {
      console.error('[IndicatorLibrary] 加载详情失败:', error)
      message.error('加载详情失败')
    } finally {
      setLoading(false)
    }
  }, [])

  // -------------------------------------------------------------------------
  // 事件处理
  // -------------------------------------------------------------------------

  /**
   * 选中指标
   */
  const handleSelect = useCallback((id: string) => {
    setSelectedId(id)
    loadDetail(id)
  }, [loadDetail])

  /**
   * 新建指标
   */
  const handleCreate = useCallback(() => {
    setSelectedId(null)
    setSelectedDetail(null)
    // TODO: 打开新建表单弹窗
    message.info('新建指标功能开发中')
  }, [])

  /**
   * 导入指标
   */
  const handleImportClick = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.xlsx,.xls,.csv'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return

      try {
        const previewData = await indicatorLibraryAPI.previewImport(file)
        setImportPreviewData(previewData)
        setImportVisible(true)
      } catch (error) {
        console.error('[IndicatorLibrary] 预览导入失败:', error)
        message.error('预览导入失败')
      }
    }
    input.click()
  }, [])

  /**
   * 确认导入
   */
  const handleImportConfirm = useCallback(async () => {
    setImportVisible(false)
    setImportPreviewData([])
    message.success('导入成功')
    loadSummaryList()
  }, [loadSummaryList])

  /**
   * 取消导入
   */
  const handleImportCancel = useCallback(() => {
    setImportVisible(false)
    setImportPreviewData([])
  }, [])

  /**
   * 导出指标
   */
  const handleExport = useCallback(async () => {
    try {
      const blob = await indicatorLibraryAPI.export(filters)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `指标库_${new Date().toISOString().split('T')[0]}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (error) {
      console.error('[IndicatorLibrary] 导出失败:', error)
      message.error('导出失败')
    }
  }, [filters])

  /**
   * 刷新数据
   */
  const handleRefresh = useCallback(() => {
    loadSummaryList()
    if (selectedId) {
      loadDetail(selectedId)
    }
  }, [loadSummaryList, loadDetail, selectedId])

  /**
   * 筛选条件变更
   */
  const handleFilterChange = useCallback((newFilters: IndicatorFilters) => {
    setFilters(newFilters)
  }, [])

  /**
   * 清除筛选
   */
  const handleClearFilters = useCallback(() => {
    setFilters({
      search_text: '',
      category: undefined,
      location: undefined,
      delivery_type: undefined,
      start_date_from: undefined,
      start_date_to: undefined,
      end_date_from: undefined,
      end_date_to: undefined,
    })
  }, [])

  /**
   * 删除指标
   */
  const handleDelete = useCallback(async (id: string) => {
    try {
      await indicatorLibraryAPI.delete(id)
      message.success('删除成功')
      if (selectedId === id) {
        setSelectedId(null)
        setSelectedDetail(null)
      }
      loadSummaryList()
    } catch (error) {
      console.error('[IndicatorLibrary] 删除失败:', error)
      message.error('删除失败')
    }
  }, [selectedId, loadSummaryList])

  /**
   * 保存指标（新建或更新）
   */
  const handleSave = useCallback(async (data: Partial<IndicatorDetail>) => {
    try {
      if (selectedId) {
        await indicatorLibraryAPI.update(selectedId, data)
        message.success('更新成功')
        loadDetail(selectedId)
      } else {
        await indicatorLibraryAPI.create(data)
        message.success('创建成功')
      }
      loadSummaryList()
    } catch (error) {
      console.error('[IndicatorLibrary] 保存失败:', error)
      message.error('保存失败')
    }
  }, [selectedId, loadDetail, loadSummaryList])

  // -------------------------------------------------------------------------
  // 副作用
  // -------------------------------------------------------------------------

  /** 组件挂载时加载数据 */
  useEffect(() => {
    loadSummaryList()
  }, [loadSummaryList])

  /** 筛选条件变更时重新加载数据 */
  useEffect(() => {
    loadSummaryList()
  }, [filters, loadSummaryList])

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------

  return (
    <div className="indicator-library-page">
      {/* 页面标题 */}
      <PageHeader
        title="指标库管理"
        subtitle="管理工程造价指标数据，支持按业态、地区、结构等条件筛选和分析"
      />

      {/* 操作按钮区域 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建
          </Button>
          <Button
            icon={<UploadOutlined />}
            onClick={handleImportClick}
          >
            导入
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            导出
          </Button>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
      </Card>

      {/* Master-Detail 布局 */}
      <Layout style={{ background: '#fff', minHeight: 'calc(100vh - 200px)' }}>
        {/* 左侧边栏 - 摘要列表 (35%) */}
        <Sider
          width="35%"
          style={{
            background: '#fff',
            borderRight: '1px solid #f0f0f0',
            overflow: 'auto',
          }}
        >
          {/* 摘要列表（包含筛选功能） */}
          <div style={{ overflow: 'auto', height: '100%' }}>
            {loading && summaryList.length === 0 ? (
              <div style={{ padding: 40, textAlign: 'center' }}>
                <Spin size="large" />
              </div>
            ) : (
              <SummaryList
                data={summaryList}
                selectedId={selectedId}
                onSelect={handleSelect}
                filters={filters}
                onFilterChange={handleFilterChange}
              />
            )}
          </div>
        </Sider>

        {/* 右侧内容区 - 详情面板 (65%) */}
        <Content
          style={{
            padding: 16,
            background: '#fff',
            overflow: 'auto',
          }}
        >
          <DetailPanel
            projectId={selectedId}
            initialData={selectedDetail}
            loading={loading && !!selectedId}
            onLoadDetail={async (id) => {
              const detail = await indicatorLibraryAPI.getDetail(id)
              return detail
            }}
            onSave={handleSave}
            onDelete={async (id) => {
              await indicatorLibraryAPI.delete(id)
              if (selectedId === id) {
                setSelectedId(null)
                setSelectedDetail(null)
              }
              loadSummaryList()
            }}
          />
        </Content>
      </Layout>

      {/* 导入预览弹窗 */}
      <ImportPreview
        visible={importVisible}
        data={importPreviewData}
        onConfirm={handleImportConfirm}
        onCancel={handleImportCancel}
      />
    </div>
  )
}