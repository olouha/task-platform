import { Table, Card, Button, Space, Tag, Tabs, Tree, Modal, Form, Input, Select, message } from 'antd'
import { PlusOutlined, AppstoreOutlined, FolderOutlined } from '@ant-design/icons'
import { useState } from 'react'
import PageHeader from '../components/PageHeader'

const mockCategories = [
  { id: '1', name: '钢筋类', icon: '🔩', color: '#16325C', count: 4 },
  { id: '2', name: '混凝土类', icon: '🧱', color: '#EF4444', count: 6 },
  { id: '3', name: '金属类', icon: '🔧', color: '#F59E0B', count: 2 },
  { id: '4', name: '有色金属类', icon: '🪙', color: '#8B5CF6', count: 3 },
]

const mockMaterials = [
  { id: '1', name: 'HRB400螺纹钢筋', category: '钢筋类', spec: '12-25mm', unit: '吨', base_price: 4500, source: '我的钢铁网' },
  { id: '2', name: 'HPB300光圆钢筋', category: '钢筋类', spec: '8-10mm', unit: '吨', base_price: 4600, source: '我的钢铁网' },
  { id: '3', name: '钢绞线', category: '钢筋类', spec: '15.2mm', unit: '吨', base_price: 5200, source: '我的钢铁网' },
  { id: '4', name: 'C30混凝土', category: '混凝土类', spec: '普通', unit: 'm³', base_price: 580, source: '我的钢铁网' },
  { id: '5', name: 'C35混凝土', category: '混凝土类', spec: '普通', unit: 'm³', base_price: 610, source: '我的钢铁网' },
  { id: '6', name: '铝锭', category: '有色金属类', spec: 'A00', unit: '吨', base_price: 18500, source: '有色金属网' },
  { id: '7', name: '铜锭', category: '有色金属类', spec: '1#电解铜', unit: '吨', base_price: 68000, source: '有色金属网' },
]

const materialColumns = [
  { title: '材料名称', dataIndex: 'name', key: 'name' },
  { title: '分类', dataIndex: 'category', key: 'category', render: (c: string) => <Tag style={{ background: '#4A86C8', color: 'white', border: 'none' }}>{c}</Tag> },
  { title: '规格', dataIndex: 'spec', key: 'spec' },
  { title: '单位', dataIndex: 'unit', key: 'unit' },
  { title: '基准价', dataIndex: 'base_price', key: 'base_price', render: (v: number) => <strong style={{ color: '#16325C' }}>¥{v.toLocaleString()}</strong> },
  { title: '价格来源', dataIndex: 'source', key: 'source', render: (s: string) => <Tag color="#4A86C8">{s}</Tag> },
  {
    title: '操作',
    width: 150,
    render: () => (
      <Space>
        <Button size="small" style={{ borderColor: '#4A86C8', color: '#4A86C8' }}>编辑</Button>
        <Button size="small" danger type="text">删除</Button>
      </Space>
    ),
  },
]

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
  const [form] = Form.useForm()

  const categoryTreeData = mockCategories.map((cat) => ({
    key: cat.id,
    title: `${cat.icon} ${cat.name} (${cat.count})`,
  }))

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
          value={mockMaterials.length}
          icon={<AppstoreOutlined />}
          color="#16325C"
          suffix="种材料"
        />
        <TechStatCard
          title="材料分类"
          value={mockCategories.length}
          icon={<FolderOutlined />}
          color="#4A86C8"
          suffix="个分类"
        />
        <TechStatCard
          title="平均基准价"
          value={Math.round(mockMaterials.reduce((sum, m) => sum + m.base_price, 0) / mockMaterials.length)}
          icon={<AppstoreOutlined />}
          color="#10B981"
          suffix="元/吨"
        />
      </div>

      {/* 内容区 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <AppstoreOutlined />
            <span>材料库</span>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
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
                  <Table dataSource={mockMaterials} columns={materialColumns} rowKey="id" pagination={{ pageSize: 10 }} />
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
                      <Button type="dashed" block style={{ marginTop: 16 }} icon={<PlusOutlined />}>
                        添加分类
                      </Button>
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
        title={<span style={{ color: 'white' }}>添加材料</span>}
        open={modalOpen}
        onOk={() => {
          form.validateFields().then(() => {
            message.success('材料添加成功')
            setModalOpen(false)
          })
        }}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="材料名称" rules={[{ required: true }]}>
            <Input placeholder="请输入材料名称" />
          </Form.Item>
          <Form.Item name="category" label="材料分类" rules={[{ required: true }]}>
            <Select placeholder="请选择分类">
              {mockCategories.map((c) => (
                <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="spec" label="规格">
            <Input placeholder="请输入规格" />
          </Form.Item>
          <Form.Item name="unit" label="单位">
            <Select placeholder="请选择单位">
              <Select.Option value="吨">吨</Select.Option>
              <Select.Option value="m³">m³</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="base_price" label="基准价">
            <Input placeholder="请输入基准价" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}