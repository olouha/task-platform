import { Table, Card, Button, Space, Tag, Modal, Form, Input, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, DollarOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { projectsApi, Project } from '../services/api'

const initialProjects: Project[] = []

const columns = [
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s === 'active' ? '进行中' : '已完成'}</Tag>,
  },
  {
    title: '操作',
    key: 'action',
    render: (_: any, record: Project) => (
      <Space>
        <Button size="small" icon={<EditOutlined />}>编辑</Button>
        <Button size="small" icon={<DollarOutlined />}>调差</Button>
        <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>删除</Button>
      </Space>
    ),
  },
]

async function handleDelete(id: string) {
  try {
    await projectsApi.delete(id)
    message.success('删除成功')
    // 刷新列表
  } catch (e) {
    message.error('删除失败')
  }
}

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>(initialProjects)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

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
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>项目管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建项目
        </Button>
      </div>

      <Card>
        <Table dataSource={projects} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 10 }} />
      </Card>

      <Modal
        title="新建项目"
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