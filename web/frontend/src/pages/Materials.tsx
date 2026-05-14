import { Table, Card, Button, Space, Tag, Tabs, Tree, Modal, Form, Input, Select, message } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState } from 'react'

const mockCategories = [
  { id: '1', name: '钢筋类', icon: '🔩', color: '#3498db', count: 4 },
  { id: '2', name: '混凝土类', icon: '🧱', color: '#e74c3c', count: 6 },
  { id: '3', name: '金属类', icon: '🔧', color: '#f39c12', count: 2 },
  { id: '4', name: '有色金属类', icon: '🪙', color: '#9b59b6', count: 3 },
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
  { title: '分类', dataIndex: 'category', key: 'category', render: (c: string) => <Tag>{c}</Tag> },
  { title: '规格', dataIndex: 'spec', key: 'spec' },
  { title: '单位', dataIndex: 'unit', key: 'unit' },
  { title: '基准价', dataIndex: 'base_price', key: 'base_price', render: (v: number) => `¥${v.toLocaleString()}` },
  { title: '价格来源', dataIndex: 'source', key: 'source', render: (s: string) => <Tag color="blue">{s}</Tag> },
  {
    title: '操作',
    render: () => (
      <Space>
        <Button size="small">编辑</Button>
        <Button size="small" danger>删除</Button>
      </Space>
    ),
  },
]

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
      <h2>材料管理</h2>

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'list',
              label: '材料列表',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                      添加材料
                    </Button>
                  </div>
                  <Table dataSource={mockMaterials} columns={materialColumns} rowKey="id" />
                </div>
              ),
            },
            {
              key: 'category',
              label: '分类管理',
              children: (
                <div style={{ display: 'flex', gap: 24 }}>
                  <div style={{ width: 300 }}>
                    <h4>材料分类</h4>
                    <Tree treeData={categoryTreeData} />
                    <Button type="dashed" block style={{ marginTop: 16 }} icon={<PlusOutlined />}>
                      添加分类
                    </Button>
                  </div>
                  <div style={{ flex: 1 }}>
                    <h4>分类详情</h4>
                    <p style={{ color: '#999' }}>点击分类查看材料列表</p>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="添加材料"
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