import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Input, Select, message, Tabs, Alert, Upload, Modal, List, Divider, DatePicker } from 'antd';
import { SearchOutlined, DollarOutlined, InboxOutlined, FileOutlined, DeleteOutlined, EyeOutlined, DatabaseOutlined, HistoryOutlined, LineChartOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { costReferenceApi, costHistoryApi } from '../services/api';
import type { UploadProps } from 'antd';

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

interface SourceOption {
  id: string;
  name: string;
  period: string;
  description: string;
  available: boolean;
}

interface SteelPriceItem {
  code: string;
  name: string;
  spec: string;
  unit: string;
  unit_price: number;
  tax_rate: number;
}

interface ConcretePriceItem {
  grade: string;
  pump_price: number;
  non_pump_price: number;
}

interface MortarPriceItem {
  name: string;
  code: string | null;
  unit_price: number;
  unit: string;
}

interface PeriodInfo {
  year: string;
  quarter: string;
  label: string;
  concrete_count: number;
  rebar_count: number;
}

interface ConcreteHistoryItem {
  grade: string;
  yantai: number | null;
  rushan: number | null;
}

interface SteelHistoryItem {
  grade: string;
  size: string;
  price: number | null;
  spec: string;
}

interface UploadFile {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  description?: string;
}

export default function CostReference() {
  const [activeTab, setActiveTab] = useState('steel');
  const [historyTab, setHistoryTab] = useState('concrete-history');
  const [steelPrices, setSteelPrices] = useState<SteelPriceItem[]>([]);
  const [concretePrices, setConcretePrices] = useState<ConcretePriceItem[]>([]);
  const [mortarPrices, setMortarPrices] = useState<MortarPriceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [steelType, setSteelType] = useState<string>('');
  const [steelSpec, setSteelSpec] = useState<string>('');
  const [steelTypes, setSteelTypes] = useState<string[]>([]);
  const [steelSpecs, setSteelSpecs] = useState<string[]>([]);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [sources, setSources] = useState<SourceOption[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>('yantai_2024q1');
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewFile, setPreviewFile] = useState<UploadFile | null>(null);

  // 历史数据状态
  const [periods, setPeriods] = useState<PeriodInfo[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [selectedQuarter, setSelectedQuarter] = useState<string>('');
  const [concreteHistory, setConcreteHistory] = useState<ConcreteHistoryItem[]>([]);
  const [steelHistory, setSteelHistory] = useState<SteelHistoryItem[]>([]);
  const [availableYears, setAvailableYears] = useState<string[]>([]);

  // 趋势分析状态
  const [trendData, setTrendData] = useState<any[]>([]);

  useEffect(() => {
    loadSources();
    loadInitialData();
    loadUploadedFiles();
    loadHistoryPeriods();
  }, []);

  const loadSources = async () => {
    try {
      const res = await costReferenceApi.getSources();
      if (res.sources) setSources(res.sources);
    } catch (error) {
      console.error('加载数据来源失败:', error);
    }
  };

  const loadInitialData = async () => {
    try {
      const [typesRes, specsRes] = await Promise.all([
        costReferenceApi.getSteelTypes(),
        costReferenceApi.getSteelSpecs(),
      ]);
      if (typesRes.types) setSteelTypes(typesRes.types);
      if (specsRes.specs) setSteelSpecs(specsRes.specs);
    } catch (error) {
      console.error('加载初始数据失败:', error);
    }
  };

  const loadHistoryPeriods = async () => {
    try {
      const [periodsRes, yearsRes] = await Promise.all([
        costHistoryApi.getPeriods(),
        costHistoryApi.getYears()
      ]);
      if (periodsRes) setPeriods(periodsRes);
      if (yearsRes?.years) {
        setAvailableYears(yearsRes.years);
        if (yearsRes.years.length > 0) {
          setSelectedYear(yearsRes.years[yearsRes.years.length - 1]);
        }
      }
    } catch (error) {
      console.error('加载历史时期失败:', error);
    }
  };

  const loadSteelPrices = async () => {
    setLoading(true);
    try {
      const params: { spec?: string; steel_type?: string } = {};
      if (steelSpec) params.spec = steelSpec;
      if (steelType) params.steel_type = steelType;
      const res = await costReferenceApi.getSteelPrices(params);
      if (res.items) setSteelPrices(res.items);
    } catch (error) {
      console.error('加载钢筋价格失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadConcretePrices = async () => {
    setLoading(true);
    try {
      const res = await costReferenceApi.getConcretePrices();
      if (res.items) setConcretePrices(res.items);
    } catch (error) {
      console.error('加载混凝土价格失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMortarPrices = async () => {
    setLoading(true);
    try {
      const res = await costReferenceApi.getMortarPrices();
      if (res.items) setMortarPrices(res.items);
    } catch (error) {
      console.error('加载砂浆价格失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadConcreteHistory = async (year: string, quarter: string) => {
    setLoading(true);
    try {
      const res = await costHistoryApi.getConcreteByPeriod(year, quarter);
      if (res.items) setConcreteHistory(res.items);
    } catch (error) {
      console.error('加载混凝土历史数据失败:', error);
      setConcreteHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const loadSteelHistory = async (year: string, quarter: string) => {
    setLoading(true);
    try {
      const res = await costHistoryApi.getSteelByPeriod(year, quarter);
      if (res.items) setSteelHistory(res.items);
    } catch (error) {
      console.error('加载钢筋历史数据失败:', error);
      setSteelHistory([]);
    } finally {
      setLoading(false);
    }
  };

  const loadConcreteTrend = async () => {
    setLoading(true);
    try {
      const res = await costHistoryApi.getLatestConcrete(undefined, 20);
      if (res.items) {
        // 转换数据为趋势图格式
        const trendItems: any[] = [];
        res.items.forEach((period: any) => {
          period.items.forEach((item: any) => {
            trendItems.push({
              period: period.label,
              grade: item.grade,
              yantai: item.yantai,
              rushan: item.rushan
            });
          });
        });
        setTrendData(trendItems);
      }
    } catch (error) {
      console.error('加载趋势数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUploadedFiles = () => {
    const saved = localStorage.getItem('cost_reference_files');
    if (saved) {
      setUploadFiles(JSON.parse(saved));
    }
  };

  const saveUploadedFiles = (files: UploadFile[]) => {
    localStorage.setItem('cost_reference_files', JSON.stringify(files));
    setUploadFiles(files);
  };

  const handleSearch = async () => {
    if (!searchKeyword.trim()) return;
    setLoading(true);
    try {
      const res = await costReferenceApi.search(searchKeyword, activeTab === 'search' ? undefined : activeTab);
      if (res.results) {
        if (activeTab === 'steel') setSteelPrices(res.results);
        else if (activeTab === 'concrete') setConcretePrices(res.results);
        else setMortarPrices(res.results);
      }
    } catch (error) {
      console.error('搜索失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodChange = (year: string, quarter: string) => {
    setSelectedYear(year);
    setSelectedQuarter(quarter);
    if (historyTab === 'concrete-history' && year && quarter) {
      loadConcreteHistory(year, quarter);
    } else if (historyTab === 'steel-history' && year && quarter) {
      loadSteelHistory(year, quarter);
    }
  };

  const handleUpload: UploadProps['beforeUpload'] = (file) => {
    const newFile: UploadFile = {
      id: Date.now().toString(),
      name: file.name,
      type: file.type || 'application/octet-stream',
      size: file.size,
      uploadedAt: new Date().toLocaleString(),
    };
    saveUploadedFiles([...uploadFiles, newFile]);
    message.success(`${file.name} 上传成功`);
    return false;
  };

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个文件吗？',
      onOk: () => {
        const updated = uploadFiles.filter(f => f.id !== id);
        saveUploadedFiles(updated);
        message.success('文件已删除');
      }
    });
  };

  const handlePreview = (file: UploadFile) => {
    setPreviewFile(file);
    setPreviewVisible(true);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const steelColumns = [
    { title: '编码', dataIndex: 'code', key: 'code', width: 100 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '规格', dataIndex: 'spec', key: 'spec', width: 80 },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 60 },
    { title: '含税单价(元)', dataIndex: 'unit_price', key: 'unit_price', width: 120,
      render: (val: number) => <strong style={{ color: '#16325C' }}>{val.toLocaleString()}</strong>
    },
    { title: '增值税率', dataIndex: 'tax_rate', key: 'tax_rate', width: 100,
      render: (val: number) => <Tag color="#4A86C8">{val}%</Tag>
    },
  ];

  const concreteColumns = [
    { title: '强度等级', dataIndex: 'grade', key: 'grade', width: 100,
      render: (val: string) => <Tag color="#10B981">{val}</Tag>
    },
    { title: '泵送价格(元/m³)', dataIndex: 'pump_price', key: 'pump_price',
      render: (val: number) => <strong style={{ color: '#16325C' }}>{val}</strong>
    },
    { title: '非泵送价格(元/m³)', dataIndex: 'non_pump_price', key: 'non_pump_price' },
    { title: '差价', key: 'diff',
      render: (_: any, record: ConcretePriceItem) => record.pump_price - record.non_pump_price
    },
  ];

  const mortarColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '型号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '单价(元/吨)', dataIndex: 'unit_price', key: 'unit_price',
      render: (val: number) => <strong style={{ color: '#16325C' }}>{val.toLocaleString()}</strong>
    },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 100 },
  ];

  // 历史混凝土列
  const concreteHistoryColumns = [
    { title: '强度等级', dataIndex: 'grade', key: 'grade', width: 100,
      render: (val: string) => <Tag color="#10B981">{val}</Tag>
    },
    { title: '烟台含税(元/m³)', dataIndex: 'yantai', key: 'yantai',
      render: (val: number | null) => val ? <strong style={{ color: '#16325C' }}>{val}</strong> : '-'
    },
    { title: '蓬莱含税(元/m³)', dataIndex: 'rushan', key: 'rushan',
      render: (val: number | null) => val ? <strong>{val}</strong> : '-'
    },
  ];

  // 历史钢筋列
  const steelHistoryColumns = [
    { title: '等级', dataIndex: 'grade', key: 'grade', width: 80,
      render: (val: string) => <Tag color="#16325C">{val}</Tag>
    },
    { title: '规格', dataIndex: 'size', key: 'size', width: 80 },
    { title: '完整规格', dataIndex: 'spec', key: 'spec' },
    { title: '价格(含税元/吨)', dataIndex: 'price', key: 'price',
      render: (val: number | null) => val ? <strong style={{ color: '#16325C' }}>{val.toLocaleString()}</strong> : '-'
    },
  ];

  const currentSource = sources.find(s => s.id === selectedSource);

  // 获取当前选中时期的数据
  const getQuartersForYear = () => {
    if (!selectedYear) return [];
    return periods.filter(p => p.year === selectedYear);
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    beforeUpload: handleUpload,
    showUploadList: false,
    accept: '.xlsx,.xls,.pdf,.csv,.doc,.docx,.txt',
  };

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <div className="page-header">
        <h2 className="page-title">造价参考价</h2>
        <p className="page-subtitle">管理材料基准价格与调差计算参考资料</p>
      </div>

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="钢筋品种"
          value={steelPrices.length || 0}
          icon={<DollarOutlined />}
          color="#16325C"
          suffix="条价格记录"
        />
        <TechStatCard
          title="混凝土等级"
          value={concretePrices.length || 0}
          icon={<InboxOutlined />}
          color="#10B981"
          suffix="个等级"
        />
        <TechStatCard
          title="历史数据时期"
          value={periods.length || 0}
          icon={<HistoryOutlined />}
          color="#4A86C8"
          suffix="个季度"
        />
        <TechStatCard
          title="上传资料"
          value={uploadFiles.length}
          icon={<FileOutlined />}
          color="#8B5CF6"
          suffix="份文档"
        />
      </div>

      {/* 主内容区 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <DatabaseOutlined />
            <span>价格数据库</span>
          </div>
          <Space>
            <Select
              placeholder="选择数据来源"
              style={{ width: 240 }}
              value={selectedSource}
              onChange={(val) => setSelectedSource(val)}
              options={sources.map(s => ({
                label: `${s.name} - ${s.period}`,
                value: s.id,
                disabled: !s.available
              }))}
            />
          </Space>
        </div>
        <div className="data-section-body">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'steel',
                label: '钢筋价格',
                children: (
                  <>
                    <Space style={{ marginBottom: 16 }} className="search-input-highlight">
                      <Input
                        placeholder="搜索关键词..."
                        prefix={<SearchOutlined />}
                        value={searchKeyword}
                        onChange={(e) => setSearchKeyword(e.target.value)}
                        onPressEnter={handleSearch}
                        style={{ width: 200 }}
                      />
                      <Button type="primary" onClick={handleSearch}>搜索</Button>
                      <Button onClick={loadSteelPrices}>刷新</Button>
                    </Space>
                    <Table
                      dataSource={steelPrices}
                      columns={steelColumns}
                      rowKey={(record: SteelPriceItem) => record.code}
                      loading={loading}
                      pagination={{ pageSize: 10, showSizeChanger: true }}
                      size="small"
                    />
                  </>
                ),
              },
              {
                key: 'concrete',
                label: '混凝土价格',
                children: (
                  <Table
                    dataSource={concretePrices}
                    columns={concreteColumns}
                    rowKey="grade"
                    loading={loading}
                    pagination={false}
                    size="small"
                  />
                ),
              },
              {
                key: 'mortar',
                label: '砂浆价格',
                children: (
                  <Table
                    dataSource={mortarPrices}
                    columns={mortarColumns}
                    rowKey="name"
                    loading={loading}
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                ),
              },
              {
                key: 'history',
                label: '历史数据',
                children: (
                  <div>
                    <Alert
                      message="历史造价参考价查询"
                      description="查询2021年至2026年的钢筋、混凝土历史造价参考价数据"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />

                    {/* 时期选择器 */}
                    <Space style={{ marginBottom: 16 }}>
                      <Select
                        placeholder="选择年份"
                        style={{ width: 120 }}
                        value={selectedYear || undefined}
                        onChange={(val) => {
                          setSelectedYear(val);
                          setSelectedQuarter('');
                          if (historyTab === 'concrete-history') {
                            const yearPeriods = periods.filter(p => p.year === val);
                            if (yearPeriods.length > 0) {
                              setSelectedQuarter(yearPeriods[yearPeriods.length - 1].quarter);
                              loadConcreteHistory(val, yearPeriods[yearPeriods.length - 1].quarter);
                            }
                          } else {
                            const yearPeriods = periods.filter(p => p.year === val);
                            if (yearPeriods.length > 0) {
                              setSelectedQuarter(yearPeriods[yearPeriods.length - 1].quarter);
                              loadSteelHistory(val, yearPeriods[yearPeriods.length - 1].quarter);
                            }
                          }
                        }}
                        options={availableYears.map(y => ({ label: `${y}年`, value: y }))}
                      />
                      <Select
                        placeholder="选择季度"
                        style={{ width: 150 }}
                        value={selectedQuarter || undefined}
                        onChange={(val) => {
                          setSelectedQuarter(val);
                          if (historyTab === 'concrete-history') {
                            loadConcreteHistory(selectedYear, val);
                          } else {
                            loadSteelHistory(selectedYear, val);
                          }
                        }}
                        options={getQuartersForYear().map(p => ({ label: p.quarter, value: p.quarter }))}
                      />
                      <Button icon={<HistoryOutlined />} onClick={() => {
                        if (historyTab === 'concrete-history') loadConcreteTrend();
                      }}>趋势分析</Button>
                    </Space>

                    {/* 历史数据子标签 */}
                    <Tabs
                      activeKey={historyTab}
                      onChange={setHistoryTab}
                      items={[
                        {
                          key: 'concrete-history',
                          label: '混凝土历史',
                          children: (
                            <Table
                              dataSource={concreteHistory}
                              columns={concreteHistoryColumns}
                              rowKey="grade"
                              loading={loading}
                              pagination={false}
                              size="small"
                              locale={{ emptyText: '请选择年份和季度查询' }}
                            />
                          ),
                        },
                        {
                          key: 'steel-history',
                          label: '钢筋历史',
                          children: (
                            <Table
                              dataSource={steelHistory}
                              columns={steelHistoryColumns}
                              rowKey="spec"
                              loading={loading}
                              pagination={{ pageSize: 15 }}
                              size="small"
                              locale={{ emptyText: '请选择年份和季度查询' }}
                            />
                          ),
                        },
                      ]}
                    />
                  </div>
                ),
              },
              {
                key: 'upload',
                label: '上传资料',
                children: (
                  <>
                    <Alert
                      message="调差资料上传"
                      description="上传工程量表，施工时间表、合同文件等调差计算所需的资料。支持的格式：Excel、PDF、Word、TXT"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    <Upload.Dragger {...uploadProps}>
                      <p className="ant-upload-drag-icon">
                        <InboxOutlined style={{ fontSize: 40, color: '#4A86C8' }} />
                      </p>
                      <p className="ant-upload-text" style={{ fontSize: 14, color: '#333', fontWeight: 500 }}>
                        点击或拖拽文件到此区域上传
                      </p>
                      <p className="ant-upload-hint" style={{ color: '#666' }}>
                        支持单个或批量上传，建议文件大小不超过50MB
                      </p>
                    </Upload.Dragger>

                    {uploadFiles.length > 0 && (
                      <>
                        <Divider>已上传的资料</Divider>
                        <List
                          size="small"
                          dataSource={uploadFiles}
                          renderItem={(file) => (
                            <List.Item
                              actions={[
                                <Button key="preview" size="small" icon={<EyeOutlined />} onClick={() => handlePreview(file)}>预览</Button>,
                                <Button key="delete" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(file.id)}>删除</Button>
                              ]}
                            >
                              <List.Item.Meta
                                avatar={<FileOutlined style={{ fontSize: 24, color: '#4A86C8' }} />}
                                title={<strong>{file.name}</strong>}
                                description={`大小: ${formatFileSize(file.size)} | 上传时间: ${file.uploadedAt}`}
                              />
                            </List.Item>
                          )}
                        />
                      </>
                    )}
                  </>
                ),
              },
            ]}
          />
        </div>
      </div>

      {/* 预览弹窗 */}
      <Modal
        title={<span style={{ color: 'white' }}>文件预览</span>}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>关闭</Button>
        ]}
        width={600}
      >
        {previewFile && (
          <div>
            <p><strong>文件名：</strong>{previewFile.name}</p>
            <p><strong>文件类型：</strong>{previewFile.type}</p>
            <p><strong>文件大小：</strong>{formatFileSize(previewFile.size)}</p>
            <p><strong>上传时间：</strong>{previewFile.uploadedAt}</p>
            <Alert
              message="预览功能"
              description="当前仅支持显示文件基本信息。如需查看文件内容，请下载后在本地打开。"
              type="info"
              showIcon
              style={{ marginTop: 16 }}
            />
          </div>
        )}
      </Modal>
    </div>
  );
}
