import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Modal, Descriptions } from 'antd'
import { CalculatorOutlined, DownloadOutlined } from '@ant-design/icons'
import { useState } from 'react'

const mockProjects = [
  { id: '1', name: 'XX商业综合体项目', contract_no: 'HT2024001', total_adjustment: 258000, status: 'calculated' },
  { id: '2', name: 'YY住宅小区项目', contract_no: 'HT2024002', total_adjustment: -125000, status: 'pending' },
]

const mockAdjustmentDetail = {
  phase_name: '主体结构阶段',
  start_date: '2024-03-01',
  end_date: '2024-05-31',
  materials: [
    { name: 'HRB400螺纹钢筋', spec: '12-25mm', quantity: 500, unit: '吨', base_price: 4200, avg_price: 4500, change_rate: 7.14, adjustment: 150000 },
    { name: 'HPB300光圆钢筋', spec: '8-10mm', quantity: 200, unit: '吨', base_price: 4300, avg_price: 4600, change_rate: 6.98, adjustment: 60000 },
    { name: 'C30混凝土', spec: '普通', quantity: 2000, unit: 'm³', base_price: 550, avg_price: 580, change_rate: 5.45, adjustment: 48000 },
  ],
  total: 258000,
}

export default function Adjustment() {
  const [detailModalOpen, setDetailModalOpen] = useState(false)

  return (
    <div>
      <h2>调差计算</h2>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card><Statistic title="项目总数" value={5} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="待计算" value={2} valueStyle={{ color: '#faad14' }} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="本季度调差总额" value={1280000} precision={0} prefix="¥" valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
      </Row>

      <Card
        title="项目调差"
        extra={
          <Space>
            <Button icon={<DownloadOutlined />}>导出报表</Button>
            <Button type="primary" icon={<CalculatorOutlined />}>新建调差</Button>
          </Space>
        }
      >
        <Table
          dataSource={mockProjects}
          rowKey="id"
          columns={[
            { title: '项目名称', dataIndex: 'name' },
            { title: '合同编号', dataIndex: 'contract_no' },
            {
              title: '调差总额',
              dataIndex: 'total_adjustment',
              render: (v: number) => (
                <span style={{ color: v > 0 ? '#52c41a' : '#f5222d', fontWeight: 'bold' }}>
                  {v > 0 ? '+' : ''}¥{v.toLocaleString()}
                </span>
              ),
            },
            { title: '状态', dataIndex: 'status', render: (s: string) => <Tag color={s === 'calculated' ? 'green' : 'orange'}>{s === 'calculated' ? '已计算' : '待计算'}</Tag> },
            {
              title: '操作',
              render: () => (
                <Space>
                  <Button size="small" type="link" onClick={() => setDetailModalOpen(true)}>查看详情</Button>
                  <Button size="small" icon={<CalculatorOutlined />}>计算</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="调差详情"
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        footer={[
          <Button key="export" icon={<DownloadOutlined />} type="default">导出Excel</Button>,
          <Button key="close" onClick={() => setDetailModalOpen(false)}>关闭</Button>,
        ]}
        width={900}
      >
        <Descriptions title={mockAdjustmentDetail.phase_name} bordered column={2}>
          <Descriptions.Item label="开始日期">{mockAdjustmentDetail.start_date}</Descriptions.Item>
          <Descriptions.Item label="结束日期">{mockAdjustmentDetail.end_date}</Descriptions.Item>
        </Descriptions>

        <Table
          dataSource={mockAdjustmentDetail.materials}
          rowKey="name"
          style={{ marginTop: 16 }}
          pagination={false}
          columns={[
            { title: '材料名称', dataIndex: 'name' },
            { title: '规格', dataIndex: 'spec' },
            { title: '数量', dataIndex: 'quantity' },
            { title: '单位', dataIndex: 'unit' },
            { title: '基准价', dataIndex: 'base_price', render: (v: number) => `¥${v}` },
            { title: '平均价', dataIndex: 'avg_price', render: (v: number) => `¥${v}` },
            { title: '涨幅', dataIndex: 'change_rate', render: (v: number) => <Tag color="red">+{v}%</Tag> },
            { title: '调差金额', dataIndex: 'adjustment', render: (v: number) => <span style={{ color: '#52c41a' }}>¥{v.toLocaleString()}</span> },
          ]}
        />

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <h3>调差总额：<span style={{ color: '#52c41a', fontSize: 24 }}>¥{mockAdjustmentDetail.total.toLocaleString()}</span></h3>
        </div>
      </Modal>
    </div>
  )
}