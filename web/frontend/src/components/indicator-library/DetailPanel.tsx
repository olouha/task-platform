/**
 * 指标库详情面板组件
 * 展示和编辑指标的完整信息
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Card,
  Button,
  Space,
  Spin,
  Typography,
  Collapse,
  message,
  Tag,
  Tooltip,
  Alert,
} from 'antd'
import {
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  ReloadOutlined,
  DeleteOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import BasicInfoSection, { BasicInfoData } from './BasicInfoSection'
import CostSection, { CostData } from './CostSection'
import SpecialCostSection, { SpecialCostData } from './SpecialCostSection'
import MaterialSection, { MaterialData } from './MaterialSection'
import './DetailPanel.css'

// ============================================================================
// 类型定义
// ============================================================================

/** 指标库完整数据 */
export interface IndicatorDetail {
  // 基本信息
  id?: string
  name?: string
  category?: string
  location?: string
  structure?: string
  delivery_type?: string
  start_date?: string
  end_date?: string
  floor_above?: number
  floor_below?: number
  height?: number
  area_total?: number
  area_above?: number
  area_below?: number
  source?: string
  source_file?: string
  remarks?: string

  // 造价指标
  unit_cost?: number
  total_cost?: number
  unit_structure?: number
  unit_installation?: number
  unit_decoration?: number
  unit_measure?: number
  above_cost_ratio?: number
  below_cost_ratio?: number
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

  // 专项工程费用
  pile?: number
  foundation_support?: number
  curtain_wall?: number
  decoration?: number
  landscape?: number
  intelligent?: number
  gas?: number
  solar?: number

  // 材料含量
  concrete_above?: number
  concrete_below?: number
  concrete_total?: number
  rebar_above?: number
  rebar_below?: number
  rebar_total?: number
  formwork_above?: number
  formwork_below?: number
  formwork_total?: number
  block_above?: number
  block_below?: number
  block_total?: number
  cable?: number
  pipe?: number
  duct?: number

  // 审核状态
  verified?: boolean
  verified_by?: string
  verified_at?: string

  // 时间戳
  created_at?: string
  updated_at?: string
}

export interface DetailPanelProps {
  /** 项目ID，'new' 表示新建模式 */
  projectId: string | null
  /** 初始数据 */
  initialData?: IndicatorDetail | null
  /** 是否加载中 */
  loading?: boolean
  /** 加载详情数据的回调 */
  onLoadDetail?: (id: string) => Promise<IndicatorDetail | null>
  /** 保存数据的回调 */
  onSave?: (data: IndicatorDetail) => Promise<void>
  /** 删除数据的回调 */
  onDelete?: (id: string) => Promise<void>
  /** 数据变更回调（编辑模式下同步编辑数据） */
  onChange?: (data: IndicatorDetail) => void
}

// ============================================================================
// 常量定义
// ============================================================================

/** Collapse 面板配置 */
const COLLAPSE_PANELS = [
  { key: 'basic', label: '基本信息', icon: '🏠' },
  { key: 'cost', label: '造价指标', icon: '💰' },
  { key: 'special', label: '专项费用', icon: '📋' },
  { key: 'material', label: '材料含量', icon: '🧱' },
]

// ============================================================================
// 组件定义
// ============================================================================

const { Title, Text } = Typography

export default function DetailPanel({
  projectId,
  initialData,
  loading = false,
  onLoadDetail,
  onSave,
  onDelete,
  onChange,
}: DetailPanelProps) {
  // -------------------------------------------------------------------------
  // 状态管理
  // -------------------------------------------------------------------------

  /** 是否为新建模式 */
  const isNewMode = projectId === 'new'

  /** 是否为编辑模式 */
  const [editMode, setEditMode] = useState(false)

  /** 原始数据（只读） */
  const [originalData, setOriginalData] = useState<IndicatorDetail | null>(null)

  /** 编辑中的数据 */
  const [editData, setEditData] = useState<IndicatorDetail |null>(null)

  /** 保存中状态 */
  const [saving, setSaving] = useState(false)

  /** 删除确认弹窗 */
  const [deleteConfirmVisible, setDeleteConfirmVisible] = useState(false)

  // -------------------------------------------------------------------------
  // 计算属性
  // -------------------------------------------------------------------------

  /** 当前显示的数据（编辑模式用 editData，否则用 originalData） */
  const currentData = editMode ? editData : originalData

  /** 是否可以编辑 */
  const canEdit = !loading && (originalData || isNewMode)

  /** 是否显示内容 */
  const showContent = !loading && (originalData || isNewMode || editMode)

  // -------------------------------------------------------------------------
  // 数据加载
  // -------------------------------------------------------------------------

  /**
   * 加载详情数据
   */
  const loadDetail = useCallback(async () => {
    if (!projectId || projectId === 'new') {
      setOriginalData(null)
      setEditData(isNewMode ? {} : null)
      return
    }

    if (onLoadDetail) {
      try {
        const data = await onLoadDetail(projectId)
        setOriginalData(data)
        setEditData(data)
      } catch (error) {
        console.error('[DetailPanel] 加载详情失败:', error)
        message.error('加载详情失败')
      }
    }
  }, [projectId, isNewMode, onLoadDetail])

  // -------------------------------------------------------------------------
  // 副作用
  // -------------------------------------------------------------------------

  /** 监听 projectId 变化，加载详情 */
  useEffect(() => {
    if (projectId) {
      loadDetail()
    } else {
      setOriginalData(null)
      setEditData(null)
    }
    setEditMode(false)
  }, [projectId, loadDetail])

  /** 监听 initialData 变化 */
  useEffect(() => {
    if (initialData) {
      setOriginalData(initialData)
      setEditData(initialData)
    }
  }, [initialData])

  /** 同步编辑数据变化到父组件 */
  useEffect(() => {
    if (editMode && editData && onChange) {
      onChange(editData)
    }
  }, [editMode, editData, onChange])

  // -------------------------------------------------------------------------
  // 事件处理
  // -------------------------------------------------------------------------

  /**
   * 进入编辑模式
   */
  const handleEdit = useCallback(() => {
    setEditMode(true)
    setEditData(originalData || {})
  }, [originalData])

  /**
   * 取消编辑
   */
  const handleCancel = useCallback(() => {
    setEditMode(false)
    setEditData(originalData)
  }, [originalData])

  /**
   * 保存数据
   */
  const handleSave = useCallback(async () => {
    if (!editData?.name) {
      message.error('请填写项目名称')
      return
    }

    setSaving(true)
    try {
      if (onSave) {
        await onSave(editData)
      }
      setEditMode(false)
      setOriginalData(editData)
      message.success('保存成功')
    } catch (error) {
      console.error('[DetailPanel] 保存失败:', error)
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }, [editData, onSave])

  /**
   * 删除数据
   */
  const handleDelete = useCallback(async () => {
    if (!projectId || projectId === 'new') return

    try {
      if (onDelete) {
        await onDelete(projectId)
      }
      message.success('删除成功')
      setOriginalData(null)
      setEditData(null)
    } catch (error) {
      console.error('[DetailPanel] 删除失败:', error)
      message.error('删除失败')
    }
    setDeleteConfirmVisible(false)
  }, [projectId, onDelete])

  /**
   * 刷新数据
   */
  const handleRefresh = useCallback(() => {
    loadDetail()
    message.info('已刷新')
  }, [loadDetail])

  /**
   * 基础信息变更
   */
  const handleBasicInfoChange = useCallback(
    (field: keyof BasicInfoData, value: string | number | undefined) => {
      setEditData((prev) => (prev ? { ...prev, [field]: value } : null))
    },
    []
  )

  /**
   * 造价指标变更
   */
  const handleCostChange = useCallback(
    (field: keyof CostData, value: number | undefined) => {
      setEditData((prev) => (prev ? { ...prev, [field]: value } : null))
    },
    []
  )

  /**
   * 专项费用变更
   */
  const handleSpecialCostChange = useCallback(
    (field: keyof SpecialCostData, value: number | undefined) => {
      setEditData((prev) => (prev ? { ...prev, [field]: value } : null))
    },
    []
  )

  /**
   * 材料含量变更
   */
  const handleMaterialChange = useCallback(
    (field: keyof MaterialData, value: number | undefined) => {
      setEditData((prev) => (prev ? { ...prev, [field]: value } : null))
    },
    []
  )

  // -------------------------------------------------------------------------
  // 渲染
  // -------------------------------------------------------------------------

  /**
   * 渲染空状态
   */
  const renderEmpty = () => (
    <div className="detail-panel-empty">
      <Title level={5} style={{ color: '#999', marginBottom: 8 }}>
        暂无选中指标
      </Title>
      <Text type="secondary">
        请从左侧列表选择一个指标，或点击"新建"添加
      </Text>
    </div>
  )

  /**
   * 渲染加载状态
   */
  const renderLoading = () => (
    <div className="detail-panel-loading">
      <Spin size="large" tip="加载中..." />
    </div>
  )

  /**
   * 渲染新建模式提示
   */
  const renderNewModeTip = () => (
    <Alert
      message="新建指标"
      description="请填写以下信息创建新的指标记录"
      type="info"
      showIcon
      style={{ marginBottom: 16 }}
    />
  )

  /**
   * 渲染操作按钮
   */
  const renderActions = () => {
    if (editMode) {
      return (
        <Space>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存
          </Button>
          <Button icon={<CloseOutlined />} onClick={handleCancel}>
            取消
          </Button>
        </Space>
      )
    }

    return (
      <Space>
        {!isNewMode && (
          <>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={handleEdit}
            >
              编辑
            </Button>
            <Tooltip title="删除后无法恢复">
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={() => setDeleteConfirmVisible(true)}
              >
                删除
              </Button>
            </Tooltip>
          </>
        )}
        {isNewMode && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleEdit}
          >
            开始创建
          </Button>
        )}
        <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
          刷新
        </Button>
      </Space>
    )
  }

  /**
   * 渲染审核状态
   */
  const renderVerifyStatus = () => {
    if (!currentData) return null

    if (currentData.verified) {
      return (
        <Tag color="success" icon={<CheckCircleOutlined />}>
          已审核
          {currentData.verified_by && ` by ${currentData.verified_by}`}
        </Tag>
      )
    }

    return (
      <Tag color="warning" icon={<ExclamationCircleOutlined />}>
        未审核
      </Tag>
    )
  }

  /**
   * 渲染详情内容
   */
  const renderContent = () => {
    if (!currentData) return renderEmpty()

    return (
      <div className="detail-panel-content">
        {/* 操作按钮区域 */}
        <div className="detail-panel-header">
          <div className="detail-panel-actions">
            {renderActions()}
          </div>
          <div className="detail-panel-status">
            {renderVerifyStatus()}
          </div>
        </div>

        {/* Collapse 折叠面板 */}
        <Collapse
          defaultActiveKey={['basic', 'cost', 'special', 'material']}
          ghost
          className="detail-panel-collapse"
          items={[
            {
              key: 'basic',
              label: (
                <span className="detail-panel-collapse-header">
                  <span>🏠</span>
                  <span>基本信息</span>
                </span>
              ),
              children: (
                <BasicInfoSection
                  data={currentData}
                  editMode={editMode}
                  onChange={handleBasicInfoChange}
                />
              ),
            },
            {
              key: 'cost',
              label: (
                <span className="detail-panel-collapse-header">
                  <span>💰</span>
                  <span>造价指标</span>
                </span>
              ),
              children: (
                <CostSection
                  data={currentData}
                  editMode={editMode}
                  onChange={handleCostChange}
                />
              ),
            },
            {
              key: 'special',
              label: (
                <span className="detail-panel-collapse-header">
                  <span>📋</span>
                  <span>专项工程费用</span>
                </span>
              ),
              children: (
                <SpecialCostSection
                  data={currentData}
                  editMode={editMode}
                  onChange={handleSpecialCostChange}
                />
              ),
            },
            {
              key: 'material',
              label: (
                <span className="detail-panel-collapse-header">
                  <span>🧱</span>
                  <span>材料含量</span>
                </span>
              ),
              children: (
                <MaterialSection
                  data={currentData}
                  editMode={editMode}
                  onChange={handleMaterialChange}
                />
              ),
            },
          ]}
        />

        {/* 时间戳信息 */}
        {(currentData.created_at || currentData.updated_at) && !editMode && (
          <div className="detail-panel-timestamps">
            <Text type="secondary" className="detail-panel-timestamp">
              {currentData.created_at && `创建于 ${currentData.created_at}`}
              {currentData.created_at && currentData.updated_at && ' | '}
              {currentData.updated_at && `更新于 ${currentData.updated_at}`}
            </Text>
          </div>
        )}
      </div>
    )
  }

  // -------------------------------------------------------------------------
  // 主渲染
  // -------------------------------------------------------------------------

  return (
    <div className="detail-panel">
      <Card className="detail-panel-card">
        {loading ? (
          renderLoading()
        ) : showContent ? (
          <>
            {isNewMode && !editMode && renderNewModeTip()}
            {renderContent()}
          </>
        ) : (
          renderEmpty()
        )}
      </Card>

      {/* 删除确认弹窗 */}
      {deleteConfirmVisible && (
        <div className="detail-panel-delete-confirm-overlay">
          <div className="detail-panel-delete-confirm">
            <Title level={5}>确认删除</Title>
            <Text>确定要删除此指标记录吗？此操作无法撤销。</Text>
            <Space style={{ marginTop: 16 }}>
              <Button danger onClick={handleDelete}>
                删除
              </Button>
              <Button onClick={() => setDeleteConfirmVisible(false)}>
                取消
              </Button>
            </Space>
          </div>
        </div>
      )}
    </div>
  )
}