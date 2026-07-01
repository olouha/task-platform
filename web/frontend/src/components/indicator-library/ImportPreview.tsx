/**
 * 指标库导入预览组件
 * 支持 Excel 文件上传、预览、验证和导入
 */
import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  Modal,
  Upload,
  Table,
  Tag,
  Button,
  Alert,
  Space,
  Typography,
  message,
} from 'antd'
import {
  UploadOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  FileExcelOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd/es/upload'
import type { RcFile } from 'antd/es/upload'
import { indicatorLibraryApi } from '../../services/api'
import type { ImportPreviewResult } from '../../services/api'
import './ImportPreview.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 预览数据项 */
export interface PreviewItem {
  /** 序号 */
  index: number
  /** 项目名称 */
  name: string
  /** 业态 */
  category: string
  /** 地区 */
  location: string
  /** 平米造价 */
  unit_cost?: number
  /** 验证状态 */
  status: 'valid' | 'warning' | 'error'
  /** 验证消息（警告或错误信息） */
  message?: string
}

/** 预览响应数据 */
interface PreviewResponse {
  success: boolean
  data?: PreviewItem[]
  errors?: string[]
  message?: string
}

/** 导入响应数据 */
interface ImportResponse {
  success: boolean
  imported?: number
  errors?: string[]
  message?: string
}

/** 组件 Props - 支持两种模式 */
export interface ImportPreviewProps {
  /** 弹窗是否可见 */
  visible: boolean
  /** 关闭弹窗回调（新版 API） */
  onClose?: () => void
  /** 导入成功回调（新版 API） */
  onSuccess?: (count: number) => void
  /** 预填数据（兼容旧版 API）- 支持任意对象数组 */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: any[]
  /** 确认导入回调（兼容旧版 API） */
  onConfirm?: () => Promise<void>
  /** 取消导入回调（兼容旧版 API） */
  onCancel?: () => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** 状态标签配置 */
const STATUS_CONFIG = {
  valid: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    text: '正常',
  },
  warning: {
    color: 'warning',
    icon: <WarningOutlined />,
    text: '警告',
  },
  error: {
    color: 'error',
    icon: <CloseCircleOutlined />,
    text: '错误',
  },
}

/** Excel 文件类型 */
const EXCEL_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.ms-excel',
]

// ============================================================================
// 组件定义
// ============================================================================

const { Text } = Typography

export default function ImportPreview({
  visible,
  onClose,
  onSuccess,
  data: externalData,
  onConfirm,
  onCancel,
}: ImportPreviewProps) {
  // -------------------------------------------------------------------------
  // 状态管理
  // -------------------------------------------------------------------------

  /** 是否使用外部预填数据（兼容模式） */
  const isExternalMode = !!externalData

  /** 已选择的文件 */
  const [fileList, setFileList] = useState<UploadFile[]>([])

  /** 预览数据（内部模式） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [internalPreviewData, setInternalPreviewData] = useState<any[]>([])

  /** 预览加载状态 */
  const [previewLoading, setPreviewLoading] = useState(false)

  /** 导入加载状态 */
  const [importLoading, setImportLoading] = useState(false)

  /** 错误信息 */
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  /** 成功信息 */
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // -------------------------------------------------------------------------
  // 计算属性
  // -------------------------------------------------------------------------

  /** 当前预览数据（根据模式选择） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const previewData: any[] = isExternalMode ? (externalData || []) : internalPreviewData

  /** 预览数据统计 */
  const previewStats = useMemo(() => {
    const stats = { valid: 0, warning: 0, error: 0 }
    previewData.forEach((item) => {
      const status = item.status as 'valid' | 'warning' | 'error'
      if (status && stats[status] !== undefined) {
        stats[status]++
      } else {
        // 默认认为有效的记录
        stats.valid++
      }
    })
    return stats
  }, [previewData])

  /** 是否可以导入（有有效数据且无错误） */
  const canImport = useMemo(() => {
    return (
      previewData.length > 0 &&
      previewData.some((item) => {
        const status = item.status as 'valid' | 'warning' | 'error' | undefined
        return status !== 'error'
      })
    )
  }, [previewData])

  /** 是否可以预览（已选择文件） */
  const canPreview = fileList.length > 0

  // -------------------------------------------------------------------------
  // 副作用
  // -------------------------------------------------------------------------

  /** 当 visible 变为 false 时重置状态 */
  useEffect(() => {
    if (!visible) {
      setFileList([])
      setInternalPreviewData([])
      setErrorMessage(null)
      setSuccessMessage(null)
    }
  }, [visible])

  // -------------------------------------------------------------------------
  // 事件处理
  // -------------------------------------------------------------------------

  /**
   * 文件选择变化
   */
  const handleFileChange: UploadProps['onChange'] = useCallback(
    ({ fileList: newFileList }: { fileList: UploadFile[] }) => {
      setFileList(newFileList)
      if (!isExternalMode) {
        setInternalPreviewData([])
      }
      setErrorMessage(null)
      setSuccessMessage(null)
    },
    [isExternalMode]
  )

  /**
   * 文件上传前校验
   */
  const beforeUpload: UploadProps['beforeUpload'] = useCallback(
    (file: RcFile) => {
      // 校验文件类型
      const isExcel = EXCEL_TYPES.includes(file.type) ||
        file.name.endsWith('.xlsx') ||
        file.name.endsWith('.xls')

      if (!isExcel) {
        message.error('只能上传 Excel 文件 (.xlsx, .xls)')
        return false
      }

      // 校验文件大小（限制 10MB）
      const isLt10M = file.size / 1024 / 1024 < 10
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB')
        return false
      }

      return true
    },
    []
  )

  /**
   * 预览按钮点击
   */
  const handlePreview = useCallback(async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件')
      return
    }

    const file = fileList[0].originFileObj
    if (!file) {
      message.error('文件读取失败')
      return
    }

    setPreviewLoading(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      const response: ImportPreviewResult = await indicatorLibraryApi.preview(file)

      // ImportPreviewResult has items[], total, valid_count, warning_count, error_count
      const dataWithIndex = response.items.map((item, idx) => ({
        ...item,
        index: idx + 1,
      }))

      if (!isExternalMode) {
        setInternalPreviewData(dataWithIndex as Record<string, unknown>[])
      }

      // 检查是否有错误
      const hasErrors = response.error_count > 0
      if (hasErrors) {
        setErrorMessage(`部分数据存在错误，共 ${response.error_count} 条错误`)
      } else {
        setSuccessMessage(`预览成功，共 ${response.total} 条数据`)
      }
      message.success('解析预览完成')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '预览失败'
      setErrorMessage(errorMsg)
      message.error(errorMsg)
      if (!isExternalMode) {
        setInternalPreviewData([])
      }
    } finally {
      setPreviewLoading(false)
    }
  }, [fileList, isExternalMode])

  /**
   * 确认导入按钮点击
   */
  const handleImport = useCallback(async () => {
    // 兼容模式：调用外部确认回调
    if (isExternalMode && onConfirm) {
      setImportLoading(true)
      try {
        await onConfirm()
        message.success('导入成功')
        handleClose()
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : '导入失败'
        setErrorMessage(errorMsg)
        message.error(errorMsg)
      } finally {
        setImportLoading(false)
      }
      return
    }

    // 标准模式：使用内部导入逻辑
    if (!canImport) {
      message.warning('数据存在错误，无法导入')
      return
    }

    const file = fileList[0].originFileObj
    if (!file) {
      message.error('文件读取失败')
      return
    }

    setImportLoading(true)
    setErrorMessage(null)

    try {
      const response = await indicatorLibraryApi.import(file) as ImportResponse

      if (response.success) {
        const importedCount = response.imported || previewData.filter(
          (item) => {
            const status = item.status as 'valid' | 'warning' | 'error' | undefined
            return status !== 'error'
          }
        ).length
        message.success(`导入成功，共导入 ${importedCount} 条数据`)

        // 调用成功回调
        if (onSuccess) {
          onSuccess(importedCount)
        }

        // 关闭弹窗并重置状态
        setTimeout(() => {
          handleClose()
        }, 500)
      } else {
        throw new Error(response.message || '导入失败')
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '导入失败'
      setErrorMessage(errorMsg)
      message.error(errorMsg)
    } finally {
      setImportLoading(false)
    }
  }, [isExternalMode, onConfirm, canImport, fileList, previewData, onSuccess])

  /**
   * 关闭弹窗
   */
  const handleClose = useCallback(() => {
    if (isExternalMode && onCancel) {
      onCancel()
    } else if (onClose) {
      onClose()
    }
  }, [isExternalMode, onCancel, onClose])

  /**
   * 重置状态
   */
  const handleReset = useCallback(() => {
    setFileList([])
    setInternalPreviewData([])
    setErrorMessage(null)
    setSuccessMessage(null)
  }, [])

  /**
   * 重新选择文件
   */
  const handleReselect = useCallback(() => {
    if (!isExternalMode) {
      setInternalPreviewData([])
    }
    setErrorMessage(null)
    setSuccessMessage(null)
  }, [isExternalMode])

  // -------------------------------------------------------------------------
  // 表格列配置
  // -------------------------------------------------------------------------

  /** 表格列定义 */
  const columns = useMemo(
    () => [
      {
        title: '序号',
        dataIndex: 'index',
        key: 'index',
        width: 60,
        fixed: 'left' as const,
      },
      {
        title: '项目名称',
        dataIndex: 'name',
        key: 'name',
        width: 200,
        ellipsis: true,
        render: (value: unknown) => String(value ?? '-'),
      },
      {
        title: '业态',
        dataIndex: 'category',
        key: 'category',
        width: 100,
        render: (value: unknown) => String(value ?? '-'),
      },
      {
        title: '地区',
        dataIndex: 'location',
        key: 'location',
        width: 100,
        render: (value: unknown) => String(value ?? '-'),
      },
      {
        title: '平米造价',
        dataIndex: 'unit_cost',
        key: 'unit_cost',
        width: 100,
        render: (value: unknown) =>
          value !== undefined && value !== null ? Number(value).toLocaleString() : '-',
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        width: 90,
        render: (status: unknown) => {
          const statusValue = status as 'valid' | 'warning' | 'error' | undefined
          if (!statusValue || !STATUS_CONFIG[statusValue]) {
            return <Tag color="default">未知</Tag>
          }
          const config = STATUS_CONFIG[statusValue]
          return (
            <Tag color={config.color} icon={config.icon}>
              {config.text}
            </Tag>
          )
        },
      },
      {
        title: '问题',
        dataIndex: 'message',
        key: 'message',
        width: 200,
        ellipsis: true,
        render: (text: unknown) =>
          text ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {String(text)}
            </Text>
          ) : (
            '-'
          ),
      },
    ],
    []
  )

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------

  /**
   * 渲染上传区域（仅内部模式显示）
   */
  const renderUploadArea = () => {
    if (isExternalMode) {
      return null
    }

    return (
      <div className="import-preview-upload-area">
        <Upload.Dragger
          fileList={fileList}
          onChange={handleFileChange}
          beforeUpload={beforeUpload}
          maxCount={1}
          accept=".xlsx,.xls"
          className="import-preview-dragger"
          showUploadList={{
            showPreviewIcon: true,
            showRemoveIcon: true,
            removeIcon: (
              <CloseCircleOutlined
                onClick={(e) => {
                  e.stopPropagation()
                  handleReset()
                }}
              />
            ),
          }}
        >
          <p className="import-preview-upload-icon">
            <FileExcelOutlined style={{ fontSize: 48, color: '#52c41a' }} />
          </p>
          <p className="import-preview-upload-text">
            点击或拖拽 Excel 文件到此区域
          </p>
          <p className="import-preview-upload-hint">
            支持 .xlsx, .xls 格式，文件大小不超过 10MB
          </p>
        </Upload.Dragger>

        <div className="import-preview-upload-actions">
          <Button
            type="primary"
            icon={<UploadOutlined />}
            onClick={handlePreview}
            loading={previewLoading}
            disabled={!canPreview}
          >
            解析预览
          </Button>
        </div>
      </div>
    )
  }

  /**
   * 渲染预览区域
   */
  const renderPreviewArea = () => (
    <div className="import-preview-preview-area">
      {/* 统计信息 */}
      <div className="import-preview-stats">
        <Text>共 {previewData.length} 条数据</Text>
        <Space size="large">
          <Tag color="success" icon={<CheckCircleOutlined />}>
            正常 {previewStats.valid}
          </Tag>
          <Tag color="warning" icon={<WarningOutlined />}>
            警告 {previewStats.warning}
          </Tag>
          <Tag color="error" icon={<CloseCircleOutlined />}>
            错误 {previewStats.error}
          </Tag>
        </Space>
      </div>

      {/* 数据表格 */}
      <Table
        dataSource={previewData}
        columns={columns}
        rowKey="index"
        size="small"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        scroll={{ x: 860 }}
        className="import-preview-table"
      />

      {/* 操作按钮 */}
      <div className="import-preview-preview-actions">
        <Space>
          {!isExternalMode && (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReselect}
              disabled={importLoading}
            >
              重新选择
            </Button>
          )}
          {!isExternalMode && (
            <Button
              icon={<FileExcelOutlined />}
              onClick={handlePreview}
              loading={previewLoading}
            >
              刷新预览
            </Button>
          )}
          <Button onClick={handleClose}>
            取消
          </Button>
        </Space>
        <Button
          type="primary"
          onClick={handleImport}
          loading={importLoading}
          disabled={!canImport}
        >
          确认导入
        </Button>
      </div>
    </div>
  )

  // -------------------------------------------------------------------------
  // 主渲染
  // -------------------------------------------------------------------------

  return (
    <Modal
      title="导入指标库数据"
      open={visible}
      onCancel={handleClose}
      width={960}
      footer={null}
      destroyOnClose
      className="import-preview-modal"
    >
      <div className="import-preview-content">
        {/* 错误提示 */}
        {errorMessage && (
          <Alert
            message="导入失败"
            description={errorMessage}
            type="error"
            showIcon
            closable
            onClose={() => setErrorMessage(null)}
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 成功提示 */}
        {successMessage && !errorMessage && (
          <Alert
            message="操作成功"
            description={successMessage}
            type="success"
            showIcon
            closable
            onClose={() => setSuccessMessage(null)}
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 内容区域 */}
        {renderUploadArea()}
        {renderPreviewArea()}
      </div>
    </Modal>
  )
}