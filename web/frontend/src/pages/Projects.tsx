import { Table, Card, Button, Space, Tag, Modal, Form, Input, message, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderOutlined, DollarOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { projectsApi, Project } from '../services/api'
import PageHeader from '../components/PageHeader'
import { getStoredIsAdmin, getStoredPosition } from '../auth'

// 全权限职位
const FULL_ACCESS_POSITIONS = ['管理层', '开发人员', '办公室团队']

const initialProjects: Project[] = []

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

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>(initialProjects)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  // 是否具有删除权限
  const canDelete = getStoredIsAdmin() || FULL_ACCESS_POSITIONS.includes((getStoredPosition() || '').trim())

  // 表格列定义
  const columns = [
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description', render: (t: string) => t || <span style={{ color: '#999' }}>-</span> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag style={{ background: s === 'active' ? '#10B981' : '#999', color: 'white', border: 'none' }}>{s === 'active' ? '进行中' : '已完成'}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: any, record: Project) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} style={{ borderColor: '#4A86C8', color: '#4A86C8' }}>编辑</Button>
          <Button size="small" type="primary" icon={<DollarOutlined />}>调差</Button>
          {canDelete && (
            <Popconfirm title="确定删除此项目？" okText="删除" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={() => handleDelete(record.id)}>
              <Button size="small" danger type="text" icon={<DeleteOutlined />}>删除</Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const loadProjects = async () => {
    setLoading(true)
    try {
      const data = await projectsApi.list()
      setProjects(data)
    } catch (e) {
      console.error('加载项目失败', e)
    }
    setLoading(false)
  }

  const handleDelete = async (id: string) => {
    try {
      await projectsApi.delete(id)
      message.success('删除成功')
      loadProjects()
    } catch (e) {
      message.error('删除失败')
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleCreate = async (values: any) => {
    try {
      const newProject = await projectsApi.create(values)
      setProjects([...projects, newProject])
      message.success('项目创建成功')
      setModalOpen(false)
      form.resetFields()
    } catch (e) {
      message.error('创建失败')
    }
  }

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <PageHeader
        title="项目管理"
        subtitle="管理工程项目基本信息"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="项目总数"
          value={projects.length}
          icon={<FolderOutlined />}
          color="#16325C"
          suffix="个工程项目"
        />
        <TechStatCard
          title="进行中"
          value={projects.filter(p => p.status === 'active').length}
          icon={<EditOutlined />}
          color="#10B981"
          suffix="个项目"
        />
        <TechStatCard
          title="已完成"
          value={projects.filter(p => p.status !== 'active').length}
          icon={<DollarOutlined />}
          color="#4A86C8"
          suffix="个项目"
        />
      </div>

      {/* 项目列表 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <FolderOutlined />
            <span>项目列表</span>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            新建项目
          </Button>
        </div>
        <div className="data-section-body">
          <Table dataSource={projects} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
        </div>
      </div>

      <Modal
        title={<span style={{ color: 'white' }}>新建项目</span>}
        open={modalOpen}
        onOk={() => {
          form.validateFields().then(handleCreate)
        }}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
            <Input placeholder="请输入项目名称" />
          </Form.Item>
          <Form.Item name="description" label="项目描述">
            <Input.TextArea placeholder="请输入项目描述" rows={3} />
          </Form.Item>
          <Form.Item name="status" label="状态" initialValue="active">
            <Input placeholder="active 或 completed" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
