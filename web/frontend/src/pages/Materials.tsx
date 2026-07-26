import { Table, Button, Space, Tag, Tabs, Tree, Modal, Form, Input, Select, InputNumber, message } from 'antd'
import { PlusOutlined, AppstoreOutlined, FolderOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { useState, useEffect, useCallback } from 'react'
import type { ColumnsType } from 'antd/es/table'
import PageHeader from '../components/PageHeader'
import { materialsApi } from '../services/api'
import type { MaterialCategory, MaterialItem } from '../services/api'
import { getStoredIsAdmin, getStoredPosition } from '../auth'

// 全权限职位
const FULL_ACCESS_POSITIONS = ['管理层', '开发人员', '办公室团队']

// 科技数据卡片组件
const TechStatCard = ({
  title,
  value,
  suffix,
  icon,
  color
}: {
  title: string
  value: number | string
  suffix?: string
  icon: React.ReactNode
  color: string
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
    {suffix && <div className="tech-card-sub">{suffix}</div>}
  </div>
)

export default function Materials() {
  const [activeTab, setActiveTab] = useState('list')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<MaterialItem | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [categories, setCategories] = useState<MaterialCategory[]>([])
  const [materials, setMaterials] = useState<MaterialItem[]>([])
  const [form] = Form.useForm()
  // 是否具有删除权限
  const position = (getStoredPosition() || '').trim()
  const canDelete = getStoredIsAdmin() || FULL_ACCESS_POSITIONS.includes(position)
  console.log('[Materials] 权限检查:', { isAdmin: getStoredIsAdmin(), position, canDelete, allowed: FULL_ACCESS_POSITIONS })

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [cats, mats] = await Promise.all([
        materialsApi.listCategories(),
        materialsApi.list(),
      ])
      setCategories(cats)
      setMaterials(mats)
    } catch (e) {
      message.error((e as Error).message || '加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 打开新增
  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  // 打开编辑
  const openEdit = (record: MaterialItem) => {
    setEditing(record)
    form.setFieldsValue({
      name: record.name,
      category_id: record.category_id,
      spec: record.spec,
      unit: record.unit,
      base_price: record.base_price,
      source: record.source,
    })
    setModalOpen(true)
  }

  // 提交（新增/编辑）
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      if (editing) {
        await materialsApi.update(editing.id, values)
        message.success('材料更新成功')
      } else {
        await materialsApi.create(values)
        message.success('材料添加成功')
      }
      setModalOpen(false)
      await loadData()
    } catch (e) {
      if ((e as { errorFields?: unknown }).errorFields) return // 表单校验错误
      message.error((e as Error).message || '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  // 删除
  const handleDelete = (record: MaterialItem) => {
    Modal.confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除材料「${record.name}」吗？此操作不可撤销。`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        try {
          await materialsApi.delete(record.id)
          message.success('删除成功')
          await loadData()
        } catch (e) {
          message.error((e as Error).message || '删除失败')
        }
      },
    })
  }

  const materialColumns: ColumnsType<MaterialItem> = [
    { title: '材料名称', dataIndex: 'name', key: 'name' },
    { title: '分类', dataIndex: 'category', key: 'category', render: (c: string) => c ? <Tag style={{ background: '#4A86C8', color: 'white', border: 'none' }}>{c}</Tag> : '-' },
    { title: '规格', dataIndex: 'spec', key: 'spec', render: (v: string) => v || '-' },
    { title: '单位', dataIndex: 'unit', key: 'unit', render: (v: string) => v || '-' },
    { title: '基准价', dataIndex: 'base_price', key: 'base_price', render: (v?: number) => v != null ? <strong style={{ color: '#16325C' }}>¥{v.toLocaleString()}</strong> : '-' },
    { title: '价格来源', dataIndex: 'source', key: 'source', render: (s: string) => s ? <Tag color="#4A86C8">{s}</Tag> : '-' },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button size="small" style={{ borderColor: '#4A86C8', color: '#4A86C8' }} onClick={() => openEdit(record)}>编辑</Button>
          {canDelete && <Button size="small" danger type="text" onClick={() => handleDelete(record)}>删除</Button>}
        </Space>
      ),
    },
  ]

  const categoryTreeData = categories.map((cat) => ({
    key: cat.id,
    title: `${cat.icon || ''} ${cat.name} (${cat.count ?? 0})`,
  }))

  const avgPrice = materials.length
    ? Math.round(materials.reduce((sum, m) => sum + (m.base_price || 0), 0) / materials.length)
    : 0

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <PageHeader
        title="材料管理"
        subtitle="管理工程材料分类与基准价格"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="材料种类"
          value={materials.length}
          icon={<AppstoreOutlined />}
          color="#16325C"
          suffix="种材料"
        />
        <TechStatCard
          title="材料分类"
          value={categories.length}
          icon={<FolderOutlined />}
          color="#4A86C8"
          suffix="个分类"
        />
        <TechStatCard
          title="平均基准价"
          value={avgPrice}
          icon={<AppstoreOutlined />}
          color="#10B981"
          suffix="元"
        />
      </div>

      {/* 内容区 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <AppstoreOutlined />
            <span>材料库</span>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            添加材料
          </Button>
        </div>
        <div className="data-section-body">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'list',
                label: '材料列表',
                children: (
                  <Table
                    dataSource={materials}
                    columns={materialColumns}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                  />
                ),
              },
              {
                key: 'category',
                label: '分类管理',
                children: (
                  <div style={{ display: 'flex', gap: 24 }}>
                    <div style={{ width: 300, background: 'linear-gradient(135deg, #FAFBFC 0%, #F5F7FA 100%)', padding: 16, borderRadius: 10, border: '1px solid #E8EBF0' }}>
                      <h4 style={{ color: '#16325C', marginBottom: 16 }}>材料分类</h4>
                      <Tree treeData={categoryTreeData} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ color: '#16325C' }}>分类详情</h4>
                      <div style={{ color: '#999', marginTop: 16 }}>点击分类查看材料列表</div>
                    </div>
                  </div>
                ),
              },
            ]}
          />
        </div>
      </div>

      <Modal
        title={editing ? '编辑材料' : '添加材料'}
        open={modalOpen}
        confirmLoading={submitting}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="材料名称" rules={[{ required: true, message: '请输入材料名称' }]}>
            <Input placeholder="请输入材料名称" />
          </Form.Item>
          <Form.Item name="category_id" label="材料分类" rules={[{ required: true, message: '请选择分类' }]}>
            <Select placeholder="请选择分类">
              {categories.map((c) => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="spec" label="规格">
            <Input placeholder="请输入规格" />
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Select placeholder="请选择单位" allowClear>
              <Select.Option value="吨">吨</Select.Option>
              <Select.Option value="m³">m³</Select.Option>
              <Select.Option value="kg">kg</Select.Option>
              <Select.Option value="m">m</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="base_price" label="基准价">
            <InputNumber style={{ width: '100%' }} min={0} placeholder="请输入基准价" />
          </Form.Item>
          <Form.Item name="source" label="价格来源">
            <Input placeholder="如：我的钢铁网" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
