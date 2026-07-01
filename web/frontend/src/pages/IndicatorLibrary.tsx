/**
 * 指标库管理主页面
 * Master-detail layout: 左侧摘要列表 (35%) + 右侧详情面板 (65%)
 */
import { useState, useEffect, useCallback } from 'react'
import { Layout, Button, Space, message, Spin, Card, Typography, Modal, Table, Badge, Descriptions } from 'antd'
import { PlusOutlined, UploadOutlined, DownloadOutlined, ReloadOutlined, FileExcelOutlined, HistoryOutlined, SyncOutlined } from '@ant-design/icons'
import PageHeader from '../components/PageHeader'

// 导入子组件
import SummaryList from '../components/indicator-library/SummaryList'
import DetailPanel from '../components/indicator-library/DetailPanel'
import ImportPreview from '../components/indicator-library/ImportPreview'

// 导入 API
import { indicatorLibraryApi } from '../services/api'
import type { IndicatorLibrarySummary, IndicatorLibraryDetail, IndicatorLibraryFilter, ImportPreviewItem } from '../types/indicator'

// ============================================================================
// 类型定义（保持向后兼容）
// ============================================================================

/** 指标库摘要项 - 向后兼容别名 */
export type IndicatorSummary = IndicatorLibrarySummary

/** 指标库详情 - 向后兼容别名 */
export type IndicatorDetail = IndicatorLibraryDetail

/** 筛选条件 - 向后兼容别名 */
export type IndicatorFilters = IndicatorLibraryFilter

/** API 响应类型 */
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

// ============================================================================
// API 别名（使用真实API）
// ============================================================================

/** 指标库 API - 使用真实API实现 */
const indicatorLibraryAPI = indicatorLibraryApi

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
  const [importPreviewData, setImportPreviewData] = useState<ImportPreviewItem[]>([])

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

  /** 导入历史弹窗 */
  const [historyVisible, setHistoryVisible] = useState(false)
  const [importHistory, setImportHistory] = useState<any[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  /** 同步状态 */
  const [syncStatus, setSyncStatus] = useState<any>(null)
  const [syncVisible, setSyncVisible] = useState(false)

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
    setSelectedId('new')
    setSelectedDetail(null)
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
        const previewData = await indicatorLibraryAPI.preview(file)
        setImportPreviewData(previewData.items || [])
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
   * 下载导入模板
   */
  const handleDownloadTemplate = useCallback(async () => {
    try {
      await indicatorLibraryApi.downloadTemplate()
      message.success('模板下载成功')
    } catch (error) {
      console.error('[IndicatorLibrary] 下载模板失败:', error)
      message.error('下载模板失败')
    }
  }, [])

  /**
   * 查看导入历史
   */
  const handleShowHistory = useCallback(async () => {
    setHistoryVisible(true)
    setHistoryLoading(true)
    try {
      const history = await indicatorLibraryApi.getImportHistory(50)
      setImportHistory(history)
    } catch (error) {
      console.error('[IndicatorLibrary] 获取导入历史失败:', error)
      message.error('获取导入历史失败')
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  /**
   * 查看同步状态
   */
  const handleShowSync = useCallback(async () => {
    setSyncVisible(true)
    try {
      const status = await indicatorLibraryApi.syncCheck()
      setSyncStatus(status)
    } catch (error) {
      console.error('[IndicatorLibrary] 获取同步状态失败:', error)
      message.error('获取同步状态失败')
    }
  }, [])

  /**
   * 自动导入（使用新接口）
   */
  const handleAutoImport = useCallback(async (file: File) => {
    try {
      const result = await indicatorLibraryApi.autoImport(file)
      if (result.success) {
        message.success(`导入成功！共导入 ${result.imported} 条数据`)
        loadSummaryList()
      } else {
        // 有错误，返回错误信息
        message.warning(`校验未通过：${result.errors?.length || 0} 条错误`)
        return result
      }
    } catch (error) {
      console.error('[IndicatorLibrary] 自动导入失败:', error)
      message.error('自动导入失败')
    }
    return null
  }, [loadSummaryList])

  /**
   * 导出指标
   */
  const handleExport = useCallback(async () => {
    try {
      const blob = await indicatorLibraryAPI.exportExcel(filters?.category)
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
      if (selectedId && selectedId !== 'new') {
        await indicatorLibraryAPI.update(selectedId, data)
        message.success('更新成功')
        loadDetail(selectedId)
      } else {
        await indicatorLibraryAPI.create(data)
        message.success('创建成功')
        // 创建成功后刷新列表
        loadSummaryList()
        setSelectedId(null)
        setSelectedDetail(null)
      }
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
            icon={<FileExcelOutlined />}
            onClick={handleDownloadTemplate}
          >
            下载模板
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            导出
          </Button>
          <Button
            icon={<HistoryOutlined />}
            onClick={handleShowHistory}
          >
            导入历史
          </Button>
          <Button
            icon={<SyncOutlined spin={!!syncStatus} />}
            onClick={handleShowSync}
          >
            同步状态
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

      {/* 导入历史弹窗 */}
      <Modal
        title="导入历史"
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={null}
        width={800}
      >
        <Table
          dataSource={importHistory}
          loading={historyLoading}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '序号', dataIndex: 'id', key: 'id', width: 60 },
            { title: '文件名', dataIndex: 'filename', key: 'filename' },
            { title: '总数', dataIndex: 'total_count', key: 'total_count', width: 80 },
            { title: '成功', dataIndex: 'success_count', key: 'success_count', width: 80, render: (v) => <span style={{ color: '#52c41a' }}>{v}</span> },
            { title: '失败', dataIndex: 'fail_count', key: 'fail_count', width: 80, render: (v) => v > 0 ? <span style={{ color: '#ff4d4f' }}>{v}</span> : v },
            { title: '导入时间', dataIndex: 'imported_at', key: 'imported_at', width: 180 },
          ]}
        />
      </Modal>

      {/* 同步状态弹窗 */}
      <Modal
        title="数据同步状态"
        open={syncVisible}
        onCancel={() => setSyncVisible(false)}
        footer={null}
        width={600}
      >
        {syncStatus && (
          <div>
            <Descriptions bordered column={1}>
              <Descriptions.Item label="SQLite 项目数">
                {syncStatus.sqlite?.project_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="快照数量">
                {syncStatus.sqlite?.snapshot_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="导入记录数">
                {syncStatus.sqlite?.import_count || 0}
              </Descriptions.Item>
              <Descriptions.Item label="最高版本号">
                {syncStatus.sqlite?.max_version || 1}
              </Descriptions.Item>
              <Descriptions.Item label="最后更新时间">
                {syncStatus.last_update || '无'}
              </Descriptions.Item>
              <Descriptions.Item label="最后导入时间">
                {syncStatus.last_import || '无'}
              </Descriptions.Item>
              <Descriptions.Item label="数据同步状态">
                <Badge status="success" text="正常" />
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>

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