import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Progress, Modal, Form, Input, Select, message, Tabs } from 'antd'
import { PlusOutlined, EditOutlined, SyncOutlined, WarningOutlined, CheckCircleOutlined, DashboardOutlined } from '@ant-design/icons'
import { useState } from 'react'

const mockIndicators = [
  { id: '1', name: '钢筋损耗率', category: '质量指标', unit: '%', target: 2.5, current: 2.8, status: 'warning', warning_threshold: 5 },
  { id: '2', name: '混凝土强度', category: '质量指标', unit: 'MPa', target: 30, current: 32, status: 'normal', warning_threshold: 10 },
  { id: '3', name: '施工进度', category: '进度指标', unit: '%', target: 60, current: 55, status: 'warning', warning_threshold: 10 },
  { id: '4', name: '成本控制', category: '成本指标', unit: '万元', target: 500, current: 480, status: 'normal', warning_threshold: 5 },
  { id: '5', name: '安全事故数', category: '安全指标', unit: '次', target: 0, current: 1, status: 'danger', warning_threshold: 0 },
]

const mockCategories = [
  { id: '1', name: '质量指标', icon: '📊', count: 2, color: '#16325C' },
  { id: '2', name: '进度指标', icon: '⏰', count: 1, color: '#10B981' },
  { id: '3', name: '成本指标', icon: '💰', count: 1, color: '#F59E0B' },
  { id: '4', name: '安全指标', icon: '⚠️', count: 1, color: '#EF4444' },
]

const statusMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  normal: { color: '#10B981', icon: <CheckCircleOutlined />, text: '正常' },
  warning: { color: '#F59E0B', icon: <WarningOutlined />, text: '预警' },
  danger: { color: '#EF4444', icon: <WarningOutlined />, text: '危险' },
}

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

export default function Indicators() {
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const getStatusTag = (status: string) => {
    const config = statusMap[status] || statusMap.normal
    return (
      <Tag style={{ background: config.color, color: 'white', border: 'none' }} icon={config.icon}>
        {config.text}
      </Tag>
    )
  }

  const getProgressStatus = (status: string) => {
    if (status === 'danger') return 'exception'
    if (status === 'warning') return 'normal'
    return 'success'
  }

  const indicatorColumns = [
    { title: '指标名称', dataIndex: 'name' },
    { title: '分类', dataIndex: 'category', render: (c: string) => <Tag style={{ background: '#4A86C8', color: 'white', border: 'none' }}>{c}</Tag> },
    { title: '单位', dataIndex: 'unit' },
    { title: '目标值', dataIndex: 'target' },
    { title: '当前值', dataIndex: 'current' },
    {
      title: '进度',
      render: (_: unknown, record: { status: string; target: number; current: number }) => (
        <Progress
          percent={Math.min((record.current / record.target) * 100, 100)}
          size="small"
          status={getProgressStatus(record.status)}
          strokeColor="#4A86C8"
        />
      ),
    },
    { title: '状态', dataIndex: 'status', render: getStatusTag },
    {
      title: '操作',
      width: 150,
      render: () => (
        <Space>
          <Button size="small" icon={<EditOutlined />} style={{ borderColor: '#4A86C8', color: '#4A86C8' }}>编辑</Button>
          <Button size="small" icon={<SyncOutlined />} style={{ borderColor: '#10B981', color: '#10B981' }}>更新</Button>
        </Space>
      ),
    },
  ]

  // 统计
  const normalCount = mockIndicators.filter(i => i.status === 'normal').length
  const warningCount = mockIndicators.filter(i => i.status === 'warning').length
  const dangerCount = mockIndicators.filter(i => i.status === 'danger').length

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <div className="page-header">
        <h2 className="page-title">指标库</h2>
        <p className="page-subtitle">监控工程各项指标数据，及时预警异常情况</p>
      </div>

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="指标总数"
          value={mockIndicators.length}
          icon={<DashboardOutlined />}
          color="#16325C"
          suffix="个监控指标"
        />
        <TechStatCard
          title="正常"
          value={normalCount}
          icon={<CheckCircleOutlined />}
          color="#10B981"
          suffix="正常运行中"
        />
        <TechStatCard
          title="预警"
          value={warningCount}
          icon={<WarningOutlined />}
          color="#F59E0B"
          suffix="需要关注"
        />
        <TechStatCard
          title="危险"
          value={dangerCount}
          icon={<WarningOutlined />}
          color="#EF4444"
          suffix="急需处理"
        />
      </div>

      {/* 指标列表 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <DashboardOutlined />
            <span>指标列表</span>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            添加指标
          </Button>
        </div>
        <div className="data-section-body">
          <Table
            dataSource={mockIndicators}
            rowKey="id"
            columns={indicatorColumns}
            pagination={{ pageSize: 10 }}
          />
        </div>
      </div>

      {/* 添加指标弹窗 */}
      <Modal
        title={<span style={{ color: 'white' }}>添加指标</span>}
        open={modalOpen}
        onOk={() => {
          form.validateFields().then(() => {
            message.success('指标添加成功')
            setModalOpen(false)
          })
        }}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="指标名称" rules={[{ required: true }]}>
            <Input placeholder="请输入指标名称" />
          </Form.Item>
          <Form.Item name="category" label="指标分类" rules={[{ required: true }]}>
            <Select placeholder="请选择分类">
              <Select.Option value="质量指标">质量指标</Select.Option>
              <Select.Option value="进度指标">进度指标</Select.Option>
              <Select.Option value="成本指标">成本指标</Select.Option>
              <Select.Option value="安全指标">安全指标</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Input placeholder="例如：%、MPa、万元" />
          </Form.Item>
          <Form.Item name="target" label="目标值">
            <Input placeholder="请输入目标值" />
          </Form.Item>
          <Form.Item name="warning_threshold" label="预警阈值(%)">
            <Input placeholder="请输入预警阈值" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}