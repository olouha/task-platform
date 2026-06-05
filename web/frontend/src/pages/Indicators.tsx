import { Table, Card, Button, Space, Tag, Progress, Modal, Form, Input, Select, message, InputNumber, Divider, Collapse, Row, Col, Popconfirm } from 'antd'
import { PlusOutlined, EditOutlined, SyncOutlined, WarningOutlined, CheckCircleOutlined, DashboardOutlined, SearchOutlined, FilterOutlined, UploadOutlined, DeleteOutlined, DownloadOutlined } from '@ant-design/icons'
import { useState, useEffect, useRef } from 'react'
import PageHeader from '../components/PageHeader'
import api from '../services/api'

// 指标库数据结构 - 与 Supabase indicator_projects 表对应
interface IndicatorData {
  id: string
  name: string
  category: string        // 业态类型: 住宅/商业/办公/酒店等
  location: string         // 地区
  structure: string        // 结构形式: 框架/剪力墙等
  floor_above: number
  floor_below: number
  area_total: number
  area_above?: number
  area_below?: number
  height: number
  complete_date?: string
  source?: string
  source_file?: string
  remarks?: string
  // 造价指标
  total_cost?: number
  unit_cost?: number
  unit_structure?: number
  unit_installation?: number
  unit_decoration?: number
  unit_measure?: number
  // 经济指标
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
  // 材料含量
  steel?: number
  concrete?: number
  formwork?: number
  block?: number
  cable?: number
  pipe?: number
  duct?: number
  // 状态
  verified?: boolean
  verified_by?: string
  verified_at?: string
  created_at?: string
}

// 行业态选项
const CATEGORY_TYPES = ['住宅', '商业', '办公', '酒店', '别墅', '车库', '厂房', '学校', '医院', '其他']
// 结构形式选项
const STRUCTURE_TYPES = ['框架结构', '剪力墙结构', '框架剪力墙结构', '钢结构', '砖混结构', '其他']
// 地区选项
const LOCATION_TYPES = ['一线城市', '二线城市', '三线城市', '四线城市']
// 高度修正系数
const HEIGHT_FACTORS: Record<string, number> = {
  '<=30': 1.00,
  '30-60': 1.03,
  '60-100': 1.08,
  '>100': 1.15
}

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

// 按层高匹配函数
const matchByHeight = (targetHeight: number, indicators: IndicatorData[], tolerance: number = 10) => {
  return indicators
    .map(ind => {
      const diff = Math.abs(targetHeight - ind.height)
      const diffPct = targetHeight > 0 ? (diff / targetHeight * 100).toFixed(1) : '0'
      let score = 100
      let recommendation = '推荐'

      if (diff === 0) {
        score = 100
        recommendation = '完全匹配'
      } else if (diff <= 5) {
        score = 95
        recommendation = '推荐'
      } else if (diff <= 10) {
        score = 85
        recommendation = '推荐'
      } else if (diff <= 20) {
        score = 70
        recommendation = '可用'
      } else if (diff <= 30) {
        score = 55
        recommendation = '参考'
      } else {
        score = 40
        recommendation = '慎用'
      }

      return { ...ind, heightDiff: diff, diffPct, score, recommendation }
    })
    .sort((a, b) => a.heightDiff - b.heightDiff)
}

export default function Indicators() {
  const [modalOpen, setModalOpen] = useState(false)
  const [detailModalOpen, setDetailModalOpen] = useState(false)
  const [matchModalOpen, setMatchModalOpen] = useState(false)
  const [selectedIndicator, setSelectedIndicator] = useState<IndicatorData | null>(null)
  const [form] = Form.useForm()
  const [matchForm] = Form.useForm()
  const [indicators, setIndicators] = useState<IndicatorData[]>([])
  const [filteredIndicators, setFilteredIndicators] = useState<IndicatorData[]>([])
  const [searchText, setSearchText] = useState('')
  const [filterCategory, setFilterCategory] = useState<string | undefined>()
  const [filterStructure, setFilterStructure] = useState<string | undefined>()
  const [matchResults, setMatchResults] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const importFileRef = useRef<HTMLInputElement>(null)

  // 从API加载指标库
  const loadIndicators = async () => {
    setLoading(true)
    try {
      const res = await api.indicatorDatabaseApi.list({ limit: 100 })
      setIndicators(res.projects || [])
      setFilteredIndicators(res.projects || [])
    } catch (error) {
      console.error('加载指标库失败:', error)
      message.error('加载指标库失败')
    } finally {
      setLoading(false)
    }
  }

  // 组件挂载时加载数据
  useEffect(() => {
    loadIndicators()
  }, [])

  // 过滤指标
  useEffect(() => {
    let filtered = [...indicators]
    if (searchText) {
      filtered = filtered.filter(ind =>
        ind.name?.toLowerCase().includes(searchText.toLowerCase()) ||
        ind.category?.includes(searchText) ||
        ind.location?.includes(searchText)
      )
    }
    if (filterCategory) {
      filtered = filtered.filter(ind => ind.category === filterCategory)
    }
    if (filterStructure) {
      filtered = filtered.filter(ind => ind.structure === filterStructure)
    }
    setFilteredIndicators(filtered)
  }, [indicators, searchText, filterCategory, filterStructure])

  const getStatusTag = (verified: boolean | undefined) => {
    if (verified) {
      return <Tag style={{ background: '#10B981', color: 'white', border: 'none' }} icon={<CheckCircleOutlined />}>已审核</Tag>
    }
    return <Tag style={{ background: '#6B7280', color: 'white', border: 'none' }}>待审核</Tag>
  }

  // 列表列定义
  const indicatorColumns = [
    { title: '项目名称', dataIndex: 'name', width: 200 },
    { title: '业态', dataIndex: 'category', width: 80, render: (c: string) => c ? <Tag color="blue">{c}</Tag> : '-' },
    { title: '地区', dataIndex: 'location', width: 90 },
    { title: '结构', dataIndex: 'structure', width: 120 },
    { title: '层数(地上/下)', width: 100, render: (_: any, r: IndicatorData) => `${r.floor_above}/${r.floor_below}` },
    { title: '总面积(㎡)', dataIndex: 'area_total', width: 100, render: (v: number) => v?.toLocaleString() },
    { title: '檐高(m)', dataIndex: 'height', width: 80 },
    { title: '单方造价', dataIndex: 'unit_cost', width: 100, render: (v: number) => v ? `${v}元/㎡` : '-' },
    { title: '钢筋含量', dataIndex: 'steel', width: 100, render: (v: number) => v ? `${v}kg/㎡` : '-' },
    { title: '状态', dataIndex: 'verified', width: 80, render: getStatusTag },
    {
      title: '操作',
      width: 200,
      render: (_: any, record: IndicatorData) => (
        <Space size="small">
          <Button size="small" type="link" onClick={() => { setSelectedIndicator(record); setDetailModalOpen(true) }}>详情</Button>
          <Button size="small" type="link" icon={<EditOutlined />} onClick={() => { setSelectedIndicator(record); form.setFieldsValue(record); setModalOpen(true) }}>编辑</Button>
          <Popconfirm title="确定删除该项目吗？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消" okButtonProps={{ danger: true }}>
            <Button size="small" type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 主要经济指标列
  const economyColumns = [
    { title: '分部分项', dataIndex: 'name', width: 120 },
    { title: '单方(元/㎡)', dataIndex: 'value', width: 100 },
    { title: '占比', dataIndex: 'percent', width: 80 },
    { title: '备注', dataIndex: 'remark', width: 150 },
  ]

  // 统计
  const totalCount = indicators.length
  const commercialCount = indicators.filter(i => i.category === '商业').length
  const residentialCount = indicators.filter(i => i.category === '住宅').length
  const officeCount = indicators.filter(i => i.category === '办公').length

  // 处理添加/编辑指标
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (selectedIndicator) {
        // 编辑
        await api.indicatorDatabaseApi.update(selectedIndicator.id, values)
        message.success('指标更新成功')
      } else {
        // 新增
        await api.indicatorDatabaseApi.create(values)
        message.success('指标添加成功')
      }
      setModalOpen(false)
      setSelectedIndicator(null)
      form.resetFields()
      loadIndicators()
    } catch (error) {
      console.error('保存失败', error)
      message.error('保存失败')
    }
  }

  // 删除指标
  const handleDelete = async (id: string) => {
    try {
      await api.indicatorDatabaseApi.delete(id)
      message.success('删除成功')
      loadIndicators()
    } catch (error) {
      console.error('删除失败', error)
      message.error('删除失败')
    }
  }

  // 层高匹配
  const handleMatchByHeight = () => {
    matchForm.validateFields().then(values => {
      const results = matchByHeight(values.targetHeight, indicators, values.tolerance || 10)
      setMatchResults(results)
    })
  }

  // 导入Excel
  const handleImport = async (file: File) => {
    try {
      const res = await api.indicatorDatabaseApi.import(file)
      if (res.success) {
        message.success(`导入成功: ${res.imported}/${res.total}`)
        loadIndicators()
      } else {
        message.warning(res.message || '导入失败')
      }
    } catch (error) {
      console.error('导入失败', error)
      message.error('导入失败')
    }
  }

  // 导出Excel
  const handleExport = async () => {
    try {
      const blob = await api.indicatorDatabaseApi.export('excel')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `指标库_${new Date().toISOString().split('T')[0]}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (error) {
      console.error('导出失败', error)
      message.error('导出失败')
    }
  }

  // 主要经济指标数据
  const getEconomyIndicators = (ind: IndicatorData) => {
    const total = ind.unit_cost || 0
    return [
      { name: '地下结构', value: ind.underground_structure, percent: total ? ((ind.underground_structure! / total) * 100).toFixed(1) + '%' : '-', remark: '含土方、基础、地下室' },
      { name: '地上结构', value: ind.above_structure, percent: total ? ((ind.above_structure! / total) * 100).toFixed(1) + '%' : '-', remark: '含混凝土、钢筋、模板' },
      { name: '屋面工程', value: ind.roof, percent: total ? ((ind.roof! / total) * 100).toFixed(1) + '%' : '-', remark: '含防水、保温、瓦等' },
      { name: '外墙装饰', value: ind.exterior_wall, percent: total ? ((ind.exterior_wall! / total) * 100).toFixed(1) + '%' : '-', remark: '含幕墙、涂料等' },
      { name: '内墙装饰', value: ind.interior_wall, percent: total ? ((ind.interior_wall! / total) * 100).toFixed(1) + '%' : '-', remark: '含抹灰、涂料等' },
      { name: '楼地面', value: ind.floor, percent: total ? ((ind.floor! / total) * 100).toFixed(1) + '%' : '-', remark: '含垫层、面层' },
      { name: '电气工程', value: ind.electrical, percent: total ? ((ind.electrical! / total) * 100).toFixed(1) + '%' : '-', remark: '含强电、弱电' },
      { name: '给排水', value: ind.plumbing, percent: total ? ((ind.plumbing! / total) * 100).toFixed(1) + '%' : '-', remark: '含管道、设备' },
      { name: '暖通空调', value: ind.hvac, percent: total ? ((ind.hvac! / total) * 100).toFixed(1) + '%' : '-', remark: '含通风、空调' },
      { name: '电梯工程', value: ind.elevator, percent: total ? ((ind.elevator! / total) * 100).toFixed(1) + '%' : '-', remark: '含电梯设备、安装' },
      { name: '消防工程', value: ind.fire, percent: total ? ((ind.fire! / total) * 100).toFixed(1) + '%' : '-', remark: '含消火栓、喷淋' },
    ]
  }

  // 主要材料含量数据
  const getMaterialContent = (ind: IndicatorData) => [
    { name: '钢筋', value: ind.steel, unit: 'kg/㎡', remark: '含地上+地下' },
    { name: '混凝土', value: ind.concrete, unit: 'm³/㎡', remark: '含梁板柱墙' },
    { name: '模板', value: ind.formwork, unit: '㎡/㎡', remark: '含木模、铝模' },
    { name: '砌块', value: ind.block, unit: 'm³/㎡', remark: '墙体材料' },
    { name: '电缆', value: ind.cable, unit: 'm/㎡', remark: '电气主干线' },
    { name: '管道', value: ind.pipe, unit: 'm/㎡', remark: '给排水管道' },
    { name: '风管', value: ind.duct, unit: '㎡/㎡', remark: '通风管道' },
  ]

  return (
    <div>
      {/* 页面标题 */}
      <PageHeader
        title="指标库"
        subtitle="工程造价指标数据库，支持按层高自动匹配和综合指标分析"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard title="指标总数" value={totalCount} icon={<DashboardOutlined />} color="#16325C" suffix="个项目" />
        <TechStatCard title="商业类" value={commercialCount} icon={<DashboardOutlined />} color="#4A86C8" suffix="个" />
        <TechStatCard title="住宅类" value={residentialCount} icon={<DashboardOutlined />} color="#10B981" suffix="个" />
        <TechStatCard title="办公类" value={officeCount} icon={<DashboardOutlined />} color="#F59E0B" suffix="个" />
      </div>

      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <Input placeholder="搜索项目名称/业态/地区" prefix={<SearchOutlined />} style={{ width: 200 }}
          onChange={e => setSearchText(e.target.value)} value={searchText} />
        <Select placeholder="业态筛选" style={{ width: 120 }} allowClear onChange={v => setFilterCategory(v)}>
          {CATEGORY_TYPES.map(c => <Select.Option key={c} value={c}>{c}</Select.Option>)}
        </Select>
        <Select placeholder="结构筛选" style={{ width: 150 }} allowClear onChange={v => setFilterStructure(v)}>
          {STRUCTURE_TYPES.map(s => <Select.Option key={s} value={s}>{s}</Select.Option>)}
        </Select>
        <Button icon={<FilterOutlined />} onClick={() => { setSearchText(''); setFilterCategory(undefined); setFilterStructure(undefined) }}>
          重置筛选
        </Button>
        <Button icon={<SyncOutlined />} onClick={loadIndicators} loading={loading}>
          刷新
        </Button>
        <Button type="primary" icon={<DashboardOutlined />} onClick={() => setMatchModalOpen(true)}>
          按层高匹配
        </Button>
        <Button icon={<UploadOutlined />} onClick={() => importFileRef.current?.click()}>
          导入Excel
        </Button>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>
          导出Excel
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setSelectedIndicator(null); form.resetFields(); setModalOpen(true) }}>
          添加指标
        </Button>
        <input
          type="file"
          accept=".xlsx,.xls"
          ref={importFileRef}
          style={{ display: 'none' }}
          onChange={e => {
            const file = e.target.files?.[0]
            if (file) handleImport(file)
            e.target.value = ''
          }}
        />
      </div>

      {/* 指标列表 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title"><DashboardOutlined /> <span>指标列表</span></div>
          <span style={{ color: '#888' }}>共 {filteredIndicators.length} 条记录</span>
        </div>
        <div className="data-section-body">
          <Table dataSource={filteredIndicators} rowKey="id" columns={indicatorColumns} pagination={{ pageSize: 10 }} size="small" loading={loading} />
        </div>
      </div>

      {/* 添加/编辑指标弹窗 */}
      <Modal
        title={selectedIndicator ? '编辑指标' : '添加指标'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); setSelectedIndicator(null); form.resetFields() }}
        width={800}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Divider>基本信息</Divider>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="name" label="项目名称" rules={[{ required: true }]}><Input placeholder="如：龙湖天街商业综合体_北京_2025" /></Form.Item></Col>
            <Col span={6}><Form.Item name="category" label="业态类型" rules={[{ required: true }]}><Select>{CATEGORY_TYPES.map(c => <Select.Option key={c} value={c}>{c}</Select.Option>)}</Select></Form.Item></Col>
            <Col span={6}><Form.Item name="location" label="地区"><Select options={LOCATION_TYPES.map(l => ({ value: l, label: l }))} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="structure" label="结构形式"><Select options={STRUCTURE_TYPES.map(s => ({ value: s, label: s }))} /></Form.Item></Col>
            <Col span={8}><Form.Item name="floor_above" label="地上层数"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="floor_below" label="地下层数"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="area_total" label="总面积(㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="height" label="檐高(m)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="complete_date" label="竣工时间"><Input placeholder="如：2025-06" /></Form.Item></Col>
          </Row>
          <Divider>造价指标</Divider>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="total_cost" label="总造价(万元)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_cost" label="单方造价(元/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_structure" label="土建单方(元/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="unit_installation" label="安装单方(元/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_decoration" label="装饰单方(元/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="unit_measure" label="措施费单方(元/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Divider>主要材料含量</Divider>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="steel" label="钢筋(kg/㎡)"><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}><Form.Item name="concrete" label="混凝土(m³/㎡)"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item></Col>
            <Col span={8}><Form.Item name="formwork" label="模板(㎡/㎡)"><InputNumber style={{ width: '100%' }} step={0.1} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="block" label="砌块(m³/㎡)"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item></Col>
            <Col span={8}><Form.Item name="cable" label="电缆(m/㎡)"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item></Col>
            <Col span={8}><Form.Item name="pipe" label="管道(m/㎡)"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item></Col>
          </Row>
          <Divider>附加信息</Divider>
          <Row gutter={16}>
            <Col span={12}><Form.Item name="source_file" label="原始文件"><Input placeholder="如：结算书_xxx.pdf" /></Form.Item></Col>
            <Col span={12}><Form.Item name="source" label="数据来源"><Select options={[
              { value: '结算文件', label: '结算文件 ★★★★★' },
              { value: '施工图预算', label: '施工图预算 ★★★★☆' },
              { value: '清单控制价', label: '清单控制价 ★★★☆☆' },
              { value: '概算文件', label: '概算文件 ★★☆☆☆' },
            ]} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}><Form.Item name="remarks" label="备注"><Input.TextArea rows={2} /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>

      {/* 指标详情弹窗 */}
      <Modal title={selectedIndicator?.name || '指标详情'} open={detailModalOpen} onCancel={() => setDetailModalOpen(false)} footer={null} width={900} destroyOnClose>
        {selectedIndicator && (
          <div>
            <Row gutter={16}>
              <Col span={6}><b>业态：</b>{selectedIndicator.category || '-'}</Col>
              <Col span={6}><b>地区：</b>{selectedIndicator.location || '-'}</Col>
              <Col span={6}><b>结构：</b>{selectedIndicator.structure || '-'}</Col>
              <Col span={6}><b>檐高：</b>{selectedIndicator.height}m</Col>
            </Row>
            <Row gutter={16} style={{ marginTop: 8 }}>
              <Col span={6}><b>总面积：</b>{selectedIndicator.area_total?.toLocaleString()}㎡</Col>
              <Col span={6}><b>地上/下：</b>{selectedIndicator.floor_above}/{selectedIndicator.floor_below}层</Col>
              <Col span={6}><b>总造价：</b>{selectedIndicator.total_cost}万元</Col>
              <Col span={6}><b>单方造价：</b>{selectedIndicator.unit_cost}元/㎡</Col>
            </Row>
            <Divider>主要经济指标</Divider>
            <Table dataSource={getEconomyIndicators(selectedIndicator)} rowKey="name" columns={economyColumns} pagination={false} size="small" />
            <Divider>主要材料含量</Divider>
            <Row gutter={16}>
              {getMaterialContent(selectedIndicator).map(m => (
                <Col span={8} key={m.name} style={{ marginBottom: 8 }}>
                  <b>{m.name}：</b>{m.value}{m.unit} <span style={{ color: '#888' }}>({m.remark})</span>
                </Col>
              ))}
            </Row>
            {selectedIndicator.source_file && <><Divider>来源</Divider><div>原始文件：{selectedIndicator.source_file}</div></>}
            {selectedIndicator.remarks && <div style={{ marginTop: 8 }}><b>备注：</b>{selectedIndicator.remarks}</div>}
            {selectedIndicator.created_at && <div style={{ marginTop: 8, color: '#888' }}><b>创建时间：</b>{selectedIndicator.created_at}</div>}
          </div>
        )}
      </Modal>

      {/* 按层高匹配弹窗 */}
      <Modal title="按层高自动匹配" open={matchModalOpen} onCancel={() => setMatchModalOpen(false)} footer={null} width={700} destroyOnClose>
        <Form form={matchForm} layout="horizontal">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="targetHeight" label="目标层高(m)" rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} placeholder="输入目标层高" min={0} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="tolerance" label="容许偏差(m)">
                <InputNumber style={{ width: '100%' }} placeholder="默认10m" min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleMatchByHeight} style={{ marginBottom: 16 }}>
            开始匹配
          </Button>
        </Form>
        {matchResults.length > 0 && (
          <div>
            <Divider>匹配结果（按偏差从小到大排序）</Divider>
            <Table dataSource={matchResults} rowKey="id" pagination={false} size="small">
              <Table.Column title="项目名称" dataIndex="name" width={180} />
              <Table.Column title="层高" dataIndex="height" width={60} />
              <Table.Column title="偏差" dataIndex="heightDiff" width={60} render={(v: number) => `${v}m`} />
              <Table.Column title="偏差%" dataIndex="diffPct" width={70} />
              <Table.Column title="推荐" dataIndex="recommendation" width={80}
                render={(r: string) => <Tag color={r === '推荐' ? 'green' : r === '慎用' ? 'red' : 'orange'}>{r}</Tag>} />
              <Table.Column title="单方造价" dataIndex="unit_cost" width={100} render={(v: number) => v ? `${v}元/㎡` : '-'} />
              <Table.Column title="匹配分" dataIndex="score" width={80} />
            </Table>
          </div>
        )}
      </Modal>
    </div>
  )
}