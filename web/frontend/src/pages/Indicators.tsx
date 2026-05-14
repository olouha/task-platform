import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Progress, Modal, Form, Input, Select, message, Tabs } from 'antd'
import { PlusOutlined, EditOutlined, SyncOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useState } from 'react'

const mockIndicators = [
  { id: '1', name: '钢筋损耗率', category: '质量指标', unit: '%', target: 2.5, current: 2.8, status: 'warning', warning_threshold: 5 },
  { id: '2', name: '混凝土强度', category: '质量指标', unit: 'MPa', target: 30, current: 32, status: 'normal', warning_threshold: 10 },
  { id: '3', name: '施工进度', category: '进度指标', unit: '%', target: 60, current: 55, status: 'warning', warning_threshold: 10 },
  { id: '4', name: '成本控制', category: '成本指标', unit: '万元', target: 500, current: 480, status: 'normal', warning_threshold: 5 },
  { id: '5', name: '安全事故数', category: '安全指标', unit: '次', target: 0, current: 1, status: 'danger', warning_threshold: 0 },
]

const mockCategories = [
  { id: '1', name: '质量指标', icon: '📊', count: 2, color: '#1890ff' },
  { id: '2', name: '进度指标', icon: '⏰', count: 1, color: '#52c41a' },
  { id: '3', name: '成本指标', icon: '💰', count: 1, color: '#faad14' },
  { id: '4', name: '安全指标', icon: '⚠️', count: 1, color: '#f5222d' },
]

const statusMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  normal: { color: 'green', icon: <CheckCircleOutlined />, text: '正常' },
  warning: { color: 'orange', icon: <WarningOutlined />, text: '预警' },
  danger: { color: 'red', icon: <WarningOutlined />, text: '危险' },
}

export default function Indicators() {
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const getStatusTag = (status: string) => {
    const config = statusMap[status] || statusMap.normal
    return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>
  }

  const getProgressStatus = (status: string) => {
    if (status === 'danger') return 'exception'
    if (status === 'warning') return 'normal'
    return 'success'
  }

  return (
    <div>
      <h2>指标库</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="指标总数" value={15} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="正常" value={10} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="预警" value={4} valueStyle={{ color: '#faad14' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="危险" value={1} valueStyle={{ color: '#f5222d' }} /></Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'list',
            label: '指标列表',
            children: (
              <Card
                title="指标列表"
                extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>添加指标</Button>}
              >
                <Table
                  dataSource={mockIndicators}
                  rowKey="id"
                  columns={[
                    { title: '指标名称', dataIndex: 'name' },
                    { title: '分类', dataIndex: 'category', render: (c: string) => <Tag>{c}</Tag> },
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
                        />
                      ),
                    },
                    { title: '状态', dataIndex: 'status', render: getStatusTag },
                    {
                      title: '操作',
                      render: () => (
                        <Space>
                          <Button size="small" icon={<EditOutlined />}>编辑</Button>
                          <Button size="small" icon={<SyncOutlined />}>更新</Button>
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'categories',
            label: '分类管理',
            children: (
              <Row gutter={16}>
                {mockCategories.map((cat) => (
                  <Col span={6} key={cat.id}>
                    <Card style={{ borderTop: `4px solid ${cat.color}` }}>
                      <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: 32 }}>{cat.icon}</div>
                        <div style={{ fontSize: 18, fontWeight: 'bold', margin: '8px 0' }}>{cat.name}</div>
                        <div style={{ color: '#666' }}>{cat.count} 个指标</div>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            ),
          },
        ]}
      />

      <Modal
        title="添加指标"
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