import { Table, Card, Button, Space, Tag, Row, Col, Modal, Descriptions, Tabs, Input, Select, Upload, List, message, Alert, Form, Popconfirm, Divider, Statistic, Collapse, DatePicker, Steps, Spin } from 'antd';
import { CalculatorOutlined, PlusOutlined, FileOutlined, DeleteOutlined, InboxOutlined, SettingOutlined, PlaySquareOutlined, FolderOutlined, FileExcelOutlined, CheckCircleOutlined, WarningOutlined, CloudUploadOutlined, DatabaseOutlined, ThunderboltOutlined, UploadOutlined, EyeOutlined, DownloadOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { adjustmentProjectApi, adjustmentCalcApi, fileParserApi, adjustmentPricesApi, adjustmentTemplateApi, config } from '../services/api';
import type { UploadProps } from 'antd';
import dayjs from 'dayjs';
import PageHeader from '../components/PageHeader';

const { TabPane } = Tabs;
const { RangePicker } = DatePicker;

interface MaterialItem {
  id?: number;
  name: string;
  spec: string;
  unit: string;
  quantity: number;
  bid_price: number;
  base_price: number;
  phase: string;
  location: string;  // 部位/楼栋
  start_date?: string;  // 施工开始日期
  end_date?: string;  // 施工结束日期
}

interface AdjustmentDetail {
  材料名称: string;
  阶段: string;
  工程量: number;
  工程量单位: string;
  基准价: number;
  施工均价: number;
  风险幅度: string;
  是否超幅: boolean;
  调整单价: number;
  调整金额: number;
  税率: number;
  含税调整金额: number;
  计算公式: string;
  计算依据: string;
}

interface CalculationResult {
  项目名称: string;
  调差总金额: number;
  明细: AdjustmentDetail[];
  使用规则版本: string;
  计算时间: string;
  阶段汇总?: any[];
  价格校验?: {
    total_materials: number;
    valid_materials: number;
    invalid_materials: number;
    average_completeness: number;
    missing_dates?: Record<string, string[]>;
  };
}

interface Project {
  id: string;
  name: string;
  contract_no: string;
  rule_id: string;
  rule_name: string;
  base_price_source: string;
  status: string;
  materials: MaterialItem[];
  attachments: any[];
  construction_start?: string;
  construction_end?: string;
  base_date?: string;
  created_at: string;
}

interface ParseResult {
  材料清单: any[];
  总数: number;
  总行数: number;
  解析行数: number;
}

const PRESET_RULES = [
  { name: '朱家庄', base_price_source: '造价信息', formula: '造价信息调整法' },
  { name: '青特地产', base_price_source: '造价信息', formula: '标准三段式' },
  { name: '莱山实验小学', base_price_source: '投标价', formula: '固定单价' },
  { name: '豪森海天映月', base_price_source: '钢铁网', formula: '比例调差法' },
  { name: '龙湖集团', base_price_source: '钢铁网', formula: '龙湖增值税率换算法' },
];

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

// 计算流程向导步骤
const CalculationSteps = Steps;

export default function Adjustment() {
  const [activeTab, setActiveTab] = useState('projects');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [calculateModalOpen, setCalculateModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [materials, setMaterials] = useState<MaterialItem[]>([]);
  const [createForm] = Form.useForm();
  const [configForm] = Form.useForm();

  // 新增：计算向导相关状态
  const [wizardStep, setWizardStep] = useState(0); // 0: 上传文件, 1: 选择规则, 2: 设置时间段, 3: 执行计算
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [parsedMaterials, setParsedMaterials] = useState<any[]>([]);
  const [selectedRule, setSelectedRule] = useState<string>('');
  const [constructionPeriod, setConstructionPeriod] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [baseDate, setBaseDate] = useState<string>('');
  const [fetchingPrices, setFetchingPrices] = useState(false);
  const [priceData, setPriceData] = useState<Record<string, any>>({});

  const [uploadFiles, setUploadFiles] = useState<any[]>([]);
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [resultModalOpen, setResultModalOpen] = useState(false);

  // 文件预览
  const [previewData, setPreviewData] = useState<any[]>([]);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);

  // 加载状态
  const [uploading, setUploading] = useState(false);
  const [parseProgress, setParseProgress] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const res = await adjustmentProjectApi.list();
      setProjects(res.projects || []);
    } catch (error) {
      console.error('加载项目失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async (values: any) => {
    try {
      const res = await adjustmentProjectApi.create({
        name: values.name,
        contract_no: values.contract_no,
        rule_name: values.rule_name,
        base_price_source: PRESET_RULES.find(r => r.name === values.rule_name)?.base_price_source || '造价信息',
      });
      if (res.success) {
        message.success('项目创建成功');
        setCreateModalOpen(false);
        createForm.resetFields();
        loadProjects();
      }
    } catch (error) {
      console.error('创建项目失败:', error);
      message.error('创建项目失败');
    }
  };

  const handleDeleteProject = async (id: string) => {
    try {
      await adjustmentProjectApi.delete(id);
      message.success('项目已删除');
      loadProjects();
    } catch (error) {
      console.error('删除项目失败:', error);
      message.error('删除项目失败');
    }
  };

  const handleSelectProject = async (project: Project) => {
    setSelectedProject(project);
    setMaterials(project.materials || []);
    setUploadFiles(project.attachments || []);
    setConfigModalOpen(true);
    configForm.setFieldsValue({
      name: project.name,
      rule_name: project.rule_name,
    });
  };

  const handleSaveMaterials = async () => {
    if (!selectedProject) return;
    try {
      await adjustmentProjectApi.setMaterials(selectedProject.id, materials);
      message.success('材料清单已保存');
    } catch (error) {
      console.error('保存材料失败:', error);
      message.error('保存材料失败');
    }
  };

  const handleAddMaterial = () => {
    setMaterials([...materials, {
      name: '',
      spec: '',
      unit: 't',
      quantity: 0,
      bid_price: 0,
      base_price: 0,
      phase: '',
      location: '',
    }]);
  };

  const handleRemoveMaterial = (index: number) => {
    setMaterials(materials.filter((_, i) => i !== index));
  };

  const handleMaterialChange = (index: number, field: string, value: any) => {
    const updated = [...materials];
    updated[index] = { ...updated[index], [field]: value };
    setMaterials(updated);
  };

  // ========== 新增：计算向导方法 ==========

  const resetWizard = () => {
    setWizardStep(0);
    setUploadFile(null);
    setParsedMaterials([]);
    setSelectedRule('');
    setConstructionPeriod(null);
    setBaseDate('');
    setPriceData({});
  };

  const handleFileSelect = async (info: any) => {
    if (info.file.status === 'uploading') return;

    const file = info.file.originFileObj || info.file;
    if (!file) return;

    setUploadFile(file);
    setUploading(true);
    setParseProgress('正在解析...');

    try {
      // 构造 FormData 直接发送
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${config.apiUrl}/api/file-parser/upload`, {
        method: 'POST',
        body: formData,
      });

      console.log('响应状态:', response.status);
      console.log('响应头:', response.headers.get('content-type'));

      const parseRes = await response.text();
      console.log('原始响应:', parseRes);

      let parseJson;
      try {
        parseJson = JSON.parse(parseRes);
      } catch (e) {
        console.error('JSON解析失败:', e);
        message.error('响应格式错误');
        setUploading(false);
        setParseProgress('');
        return;
      }

      setUploading(false);
      setParseProgress('');

      console.log('解析响应:', parseJson);

      // 打印更多调试信息
      console.log('success:', parseJson.success);
      console.log('result:', parseJson.result);
      console.log('部位时段:', parseJson.result?.部位时段);

      if (parseJson.success && parseJson.result?.材料清单?.length > 0) {
        setParsedMaterials(parseJson.result.材料清单);
        message.success(`解析成功: ${parseJson.result.解析行数 || 0} 条材料`);

        // 如果有部位时段信息，自动设置
        const locations = parseJson.result?.部位时段;
        if (locations && Object.keys(locations).length > 0) {
          console.log('检测到部位时段:', locations);
          message.info(`检测到 ${Object.keys(locations).length} 个施工部位`);
        }
      } else {
        message.warning('文件解析结果为空，请检查格式是否包含"材料名称"和"工程量"列');
      }
    } catch (error) {
      setUploading(false);
      setParseProgress('');
      console.error('文件处理失败:', error);
      const errorMessage = (error as any).message || String(error);
      message.error('文件处理失败: ' + errorMessage);
    }
  };

  const handleApplyParsedMaterials = () => {
    if (parsedMaterials.length === 0) {
      message.warning('没有可导入的材料数据');
      return;
    }

    const newMaterials: MaterialItem[] = parsedMaterials.map((m: any) => ({
      name: m.名称 || m.name || '',
      spec: m.规格 || m.spec || '',
      unit: m.单位 || m.unit || 't',
      quantity: m.工程量 || m.quantity || 0,
      bid_price: m.投标单价 || m.bid_price || m.price || 0,
      base_price: m.基准价 || m.base_price || 0,
      phase: m.阶段 || m.phase || '',
      location: m.部位 || m.location || '',
      start_date: m.开始日期 || m.start_date || '',
      end_date: m.结束日期 || m.end_date || '',
    }));

    setMaterials(newMaterials);
    message.success(`已导入 ${newMaterials.length} 条材料（含部位时段信息）`);
    setWizardStep(1);
  };

  // 批量获取所有材料价格（新接口）
  const handleBatchFetchPrices = async () => {
    if (!constructionPeriod || !baseDate || materials.length === 0) {
      message.warning('请先设置施工时间段和基准日期');
      return;
    }

    setFetchingPrices(true);
    const startDate = constructionPeriod[0].format('YYYY-MM-DD');
    const endDate = constructionPeriod[1].format('YYYY-MM-DD');

    try {
      const materialNames = [...new Set(materials.map(m => m.name).filter(Boolean))];

      const res = await fetch(`${config.apiUrl}/api/adjustments/prices/batch-get`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          materials: materialNames,
          start_date: startDate,
          end_date: endDate,
          base_date: baseDate
        })
      }).then(r => r.json());

      if (res.success && res.data) {
        const updated = materials.map(m => {
          const priceData = res.data[m.name];
          return {
            ...m,
            base_price: m.base_price || priceData?.base || 4500,
          };
        });
        setMaterials(updated);
        setPriceData(res.data);
        message.success(`已获取 ${Object.keys(res.data).length} 种材料的价格`);
        setWizardStep(3);
      } else {
        message.warning('未能获取价格数据，继续使用默认值');
        setWizardStep(3);
      }
    } catch (error) {
      console.error('获取价格失败:', error);
      message.error('获取价格失败，使用默认值');
      setWizardStep(3);
    } finally {
      setFetchingPrices(false);
    }
  };

  const handleExecuteCalculation = async () => {
    if (!selectedProject || materials.length === 0) {
      message.warning('请先配置材料清单');
      return;
    }

    setCalculating(true);
    try {
      // 如果有解析的材料，先更新
      if (parsedMaterials.length > 0) {
        await adjustmentProjectApi.setMaterials(selectedProject.id, materials);
      }

      // 更新项目时间段
      if (constructionPeriod) {
        await adjustmentProjectApi.update(selectedProject.id, {
          construction_start: constructionPeriod[0].format('YYYY-MM-DD'),
          construction_end: constructionPeriod[1].format('YYYY-MM-DD'),
          base_date: baseDate,
        });
      }

      // 执行计算
      const res = await adjustmentCalcApi.calculateByProject(selectedProject.id);

      if (res.success) {
        setCalculationResult(res.data);
        setResultModalOpen(true);
        message.success('调差计算完成！');
        loadProjects();
      } else {
        message.error(res.error || '计算失败');
      }
    } catch (error) {
      console.error('计算失败:', error);
      message.error('计算失败，请检查后端服务');
    } finally {
      setCalculating(false);
    }
  };

  // 快速计算向导
  const openQuickCalculate = (project: Project) => {
    setSelectedProject(project);
    setMaterials(project.materials || []);
    resetWizard();
    setCalculateModalOpen(true);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    beforeUpload: () => false,
    showUploadList: false,
    accept: '.xlsx,.xls,.csv',
    onChange: handleFileSelect,
  };

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      draft: { color: 'default', text: '草稿' },
      configured: { color: '#4A86C8', text: '已配置' },
      calculated: { color: '#10B981', text: '已计算' },
    };
    const s = statusMap[status] || statusMap.draft;
    return <Tag style={{ background: s.color, color: 'white', border: 'none' }}>{s.text}</Tag>;
  };

  const projectColumns = [
    { title: '项目名称', dataIndex: 'name', key: 'name' },
    { title: '合同编号', dataIndex: 'contract_no', key: 'contract_no' },
    { title: '调差规则', dataIndex: 'rule_name', key: 'rule_name',
      render: (v: string) => v || <span style={{ color: '#999' }}>未选择</span>
    },
    { title: '基准价来源', dataIndex: 'base_price_source', key: 'base_price_source' },
    { title: '材料数', dataIndex: 'materials', key: 'materials',
      render: (arr: any[]) => arr?.length || 0
    },
    { title: '状态', dataIndex: 'status', key: 'status', render: getStatusTag },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: any, record: Project) => (
        <Space>
          <Button
            size="small"
            icon={<SettingOutlined />}
            onClick={() => handleSelectProject(record)}
            style={{ borderColor: '#4A86C8', color: '#4A86C8' }}
          >
            配置
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={() => openQuickCalculate(record)}
            style={{ background: '#10B981', borderColor: '#10B981' }}
          >
            快速计算
          </Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDeleteProject(record.id)}>
            <Button size="small" danger type="text" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <PageHeader
        title="工程材料调差计算"
        subtitle="上传工程量底稿 → 选择调差规则 → 设置施工时间 → 自动计算"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="调差项目"
          value={projects.length}
          icon={<FolderOutlined />}
          color="#16325C"
          suffix="个项目"
        />
        <TechStatCard
          title="已配置"
          value={projects.filter(p => p.status !== 'draft').length}
          icon={<SettingOutlined />}
          color="#4A86C8"
          suffix="个项目"
        />
        <TechStatCard
          title="已完成计算"
          value={projects.filter(p => p.status === 'calculated').length}
          icon={<CalculatorOutlined />}
          color="#10B981"
          suffix="个项目"
        />
        <TechStatCard
          title="材料总数"
          value={projects.reduce((sum, p) => sum + (p.materials?.length || 0), 0)}
          icon={<FileExcelOutlined />}
          color="#722ed1"
          suffix="条记录"
        />
      </div>

      {/* 项目列表 */}
      <div className="data-section" style={{ marginBottom: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <FolderOutlined />
            <span>调差项目管理</span>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalOpen(true)}
          >
            新建项目
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={async () => {
              try {
                const result = await adjustmentTemplateApi.generateTemplate({
                  project_name: 'XX项目',
                  rule_name: '标准调差规则',
                  include_examples: true
                });
                if (result.success) {
                  adjustmentTemplateApi.downloadTemplate(result.file_name);
                  message.success('模板下载成功');
                }
              } catch (err) {
                console.error('下载模板失败', err);
                message.error('下载模板失败');
              }
            }}
          >
            下载模板
          </Button>
        </div>
        <div className="data-section-body">
          <Table
            dataSource={projects}
            columns={projectColumns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </div>
      </div>

      {/* 新建项目弹窗 */}
      <Modal
        title={<span style={{ color: 'white' }}>新建调差项目</span>}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
        width={500}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateProject}>
          <Form.Item name="name" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
            <Input placeholder="如：XX商业综合体项目" />
          </Form.Item>
          <Form.Item name="contract_no" label="合同编号">
            <Input placeholder="如：HT2024001" />
          </Form.Item>
          <Form.Item name="rule_name" label="调差规则">
            <Select placeholder="选择预设规则">
              {PRESET_RULES.map(r => (
                <Select.Option key={r.name} value={r.name}>
                  {r.name} ({r.formula})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" block>
              创建项目
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 快速计算向导弹窗 */}
      <Modal
        title={<span style={{ color: 'white' }}>调差计算向导</span>}
        open={calculateModalOpen}
        onCancel={() => { setCalculateModalOpen(false); resetWizard(); }}
        width={900}
        footer={null}
      >
        {selectedProject && (
          <div>
            {/* 步骤指示器 */}
            <CalculationSteps
              current={wizardStep}
              style={{ marginBottom: 24 }}
              items={[
                { title: '上传文件', icon: <UploadOutlined /> },
                { title: '选择规则', icon: <SettingOutlined /> },
                { title: '设置时间', icon: <DatabaseOutlined /> },
                { title: '执行计算', icon: <CalculatorOutlined /> },
              ]}
            />

            {/* 步骤1：上传文件 - 合并为一个窗格 */}
            {wizardStep === 0 && (
              <div>
                <Alert
                  message="步骤1：上传工程量底稿"
                  description="上传包含材料清单和施工时间段的Excel文件，系统自动解析材料数据和时间范围。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Upload.Dragger {...uploadProps} disabled={uploading}>
                  <p className="ant-upload-drag-icon">
                    <CloudUploadOutlined style={{ fontSize: 48, color: '#4A86C8' }} />
                  </p>
                  <p className="ant-upload-text" style={{ fontSize: 16, fontWeight: 500 }}>
                    点击或拖拽文件上传
                  </p>
                  <p className="ant-upload-hint">支持 .xlsx, .xls, .csv 格式</p>
                </Upload.Dragger>

                {uploading && (
                  <div style={{ textAlign: 'center', padding: 20 }}>
                    <Spin tip={parseProgress || '正在解析...'} size="large" />
                  </div>
                )}

                {/* 解析结果 */}
                {parsedMaterials.length > 0 && !uploading && (
                  <div style={{ marginTop: 16 }}>
                    <Alert
                      message={`解析成功：共 ${parsedMaterials.length} 条材料`}
                      type="success"
                      showIcon
                      style={{ marginBottom: 12 }}
                    />
                    <Table
                      dataSource={parsedMaterials.slice(0, 10)}
                      rowKey={(_, idx) => idx?.toString() || '0'}
                      size="small"
                      pagination={false}
                      scroll={{ x: 600 }}
                      columns={[
                        { title: '名称', dataIndex: '名称', key: '名称', width: 150 },
                        { title: '规格', dataIndex: '规格', key: '规格', width: 80 },
                        { title: '工程量', dataIndex: '工程量', key: '工程量', width: 100 },
                        { title: '单位', dataIndex: '单位', key: '单位', width: 60 },
                      ]}
                    />
                    {parsedMaterials.length > 10 && (
                      <div style={{ textAlign: 'center', color: '#999', marginTop: 8 }}>
                        还有 {parsedMaterials.length - 10} 条数据...
                      </div>
                    )}
                  </div>
                )}

                <div style={{ textAlign: 'right', marginTop: 24 }}>
                  <Space>
                    {parsedMaterials.length > 0 && (
                      <Button onClick={() => setParsedMaterials([])}>清除</Button>
                    )}
                    <Button
                      type="primary"
                      onClick={handleApplyParsedMaterials}
                      disabled={parsedMaterials.length === 0}
                    >
                      导入材料并下一步 →
                    </Button>
                  </Space>
                </div>
              </div>
            )}

            {/* 步骤2：选择规则 */}
            {wizardStep === 1 && (
              <div>
                <Alert
                  message="步骤2：选择调差规则"
                  description="选择适用于本项目的调差计算规则，不同规则有不同的价格采集方式和风险幅度计算方法。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Form layout="vertical">
                  <Form.Item label="项目名称">
                    <Input disabled value={selectedProject.name} />
                  </Form.Item>

                  <Form.Item label="调差规则" required>
                    <Select
                      placeholder="请选择调差规则"
                      value={selectedRule}
                      onChange={setSelectedRule}
                      size="large"
                    >
                      {PRESET_RULES.map(r => (
                        <Select.Option key={r.name} value={r.name}>
                          <div>
                            <strong>{r.name}</strong>
                            <div style={{ fontSize: 12, color: '#666' }}>
                              公式: {r.formula} | 基准价: {r.base_price_source}
                            </div>
                          </div>
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item label="材料清单预览">
                    <Table
                      dataSource={materials.slice(0, 10)}
                      rowKey={(_, idx) => idx?.toString() || '0'}
                      size="small"
                      pagination={false}
                      columns={[
                        { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
                        { title: '规格', dataIndex: 'spec', key: 'spec', width: 80 },
                        { title: '工程量', dataIndex: 'quantity', key: 'quantity', width: 100,
                          render: (v: number) => v?.toLocaleString() },
                        { title: '单位', dataIndex: 'unit', key: 'unit', width: 60 },
                      ]}
                    />
                    {materials.length > 10 && (
                      <div style={{ textAlign: 'center', color: '#999' }}>
                        还有 {materials.length - 10} 条材料...
                      </div>
                    )}
                  </Form.Item>
                </Form>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                  <Button onClick={() => setWizardStep(0)}>← 上一步</Button>
                  <Button
                    type="primary"
                    onClick={() => setWizardStep(2)}
                    disabled={!selectedRule}
                  >
                    下一步 →
                  </Button>
                </div>
              </div>
            )}

            {/* 步骤3：设置时间 */}
            {wizardStep === 2 && (
              <div>
                <Alert
                  message="步骤3：设置施工时间段"
                  description="设置基准日期和施工时间段，系统将从价格数据库获取对应期间的材料均价进行计算。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Form layout="vertical">
                  <Form.Item label="基准日期" required>
                    <DatePicker
                      style={{ width: '100%' }}
                      value={baseDate ? dayjs(baseDate) : null}
                      onChange={(date, dateString) => setBaseDate(dateString as string)}
                      placeholder="选择基准日期（招标/签约时期）"
                    />
                  </Form.Item>

                  <Form.Item label="施工时间段" required>
                    <RangePicker
                      style={{ width: '100%' }}
                      value={constructionPeriod}
                      onChange={(dates) => setConstructionPeriod(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
                      placeholder={['施工开始日期', '施工结束日期']}
                    />
                  </Form.Item>

                  <Form.Item label="价格来源">
                    <Select
                      placeholder="价格数据来源"
                      value={selectedProject.base_price_source}
                      disabled
                      options={[
                        { value: '造价信息', label: '造价信息（烟台市工程建设标准造价管理指导价）' },
                        { value: '我的钢铁网', label: '我的钢铁网（钢铁网每日行情价）' },
                        { value: '投标价', label: '投标价（合同约定固定单价）' },
                      ]}
                    />
                  </Form.Item>

                  {Object.keys(priceData).length > 0 && (
                    <Alert
                      message="价格已获取"
                      description={`已获取 ${Object.keys(priceData).length} 种材料的价格数据`
                    }
                    type="success"
                    showIcon
                      style={{ marginBottom: 16 }}
                    />
                  )}
                </Form>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                  <Button onClick={() => setWizardStep(1)}>← 上一步</Button>
                  <Space>
                    <Button
                      onClick={handleBatchFetchPrices}
                      loading={fetchingPrices}
                      icon={<DatabaseOutlined />}
                    >
                      批量获取价格
                    </Button>
                    <Button
                      type="primary"
                      onClick={() => setWizardStep(3)}
                    >
                      下一步 →
                    </Button>
                  </Space>
                </div>
              </div>
            )}

            {/* 步骤4：执行计算 */}
            {wizardStep === 3 && (
              <div>
                <Alert
                  message="步骤4：执行调差计算"
                  description="确认所有参数后，点击「执行计算」按钮开始计算调差金额。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Descriptions bordered size="small" column={2}>
                  <Descriptions.Item label="项目名称" labelStyle={{ background: '#EEF2F7' }}>
                    {selectedProject.name}
                  </Descriptions.Item>
                  <Descriptions.Item label="调差规则" labelStyle={{ background: '#EEF2F7' }}>
                    {selectedRule || selectedProject.rule_name}
                  </Descriptions.Item>
                  <Descriptions.Item label="基准日期" labelStyle={{ background: '#EEF2F7' }}>
                    {baseDate || '未设置'}
                  </Descriptions.Item>
                  <Descriptions.Item label="施工时间段" labelStyle={{ background: '#EEF2F7' }}>
                    {constructionPeriod ? `${constructionPeriod[0].format('YYYY-MM-DD')} 至 ${constructionPeriod[1].format('YYYY-MM-DD')}` : '未设置'}
                  </Descriptions.Item>
                  <Descriptions.Item label="材料数量" labelStyle={{ background: '#EEF2F7' }}>
                    {materials.length} 种
                  </Descriptions.Item>
                  <Descriptions.Item label="价格来源" labelStyle={{ background: '#EEF2F7' }}>
                    {selectedProject.base_price_source}
                  </Descriptions.Item>
                </Descriptions>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 24 }}>
                  <Button onClick={() => setWizardStep(2)}>← 上一步</Button>
                  <Button
                    type="primary"
                    size="large"
                    icon={<CalculatorOutlined />}
                    loading={calculating}
                    onClick={handleExecuteCalculation}
                    style={{ background: '#10B981', borderColor: '#10B981' }}
                  >
                    {calculating ? '计算中...' : '执行调差计算'}
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 文件预览弹窗 */}
      <Modal
        title="文件预览"
        open={previewModalOpen}
        onCancel={() => setPreviewModalOpen(false)}
        footer={null}
        width={800}
      >
        <Table
          dataSource={previewData}
          rowKey="row"
          pagination={{ pageSize: 10 }}
          columns={[
            { title: '行号', dataIndex: 'row', key: 'row', width: 60 },
            { title: '数据', dataIndex: 'cells', key: 'cells',
              render: (cells: string[]) => cells?.join(' | ') || ''
            },
          ]}
        />
      </Modal>

      {/* 计算结果弹窗 */}
      <Modal
        title={<span style={{ color: 'white' }}>调差计算结果</span>}
        open={resultModalOpen}
        onCancel={() => setResultModalOpen(false)}
        width={1100}
        footer={[
          <Button key="close" onClick={() => setResultModalOpen(false)}>关闭</Button>,
        ]}
      >
        {calculationResult && (
          <div>
            {/* 总金额统计 - 含税/不含税/税金分开显示 */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={6}>
                <Statistic
                  title="调差总金额（含税）"
                  value={calculationResult.调差总金额}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: calculationResult.调差总金额 >= 0 ? '#10B981' : '#FF4D4F' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="调差总金额（不含税）"
                  value={(() => {
                    const total = calculationResult.调差总金额;
                    const taxRate = 1.09;
                    return total / taxRate;
                  })()}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: calculationResult.调差总金额 >= 0 ? '#4A86C8' : '#FF4D4F' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="税金（9%）"
                  value={(() => {
                    const total = calculationResult.调差总金额;
                    const preTax = total / 1.09;
                    return total - preTax;
                  })()}
                  precision={2}
                  prefix="¥"
                  valueStyle={{ color: '#722ed1' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="使用规则版本"
                  value={calculationResult.使用规则版本}
                />
              </Col>
            </Row>

            {/* 明细表格 */}
            <div style={{ marginBottom: 16 }}>
              <strong style={{ color: '#16325C' }}>调差明细</strong>
            </div>
            <Table
              dataSource={calculationResult.明细 || []}
              rowKey={(_, idx) => idx?.toString() || '0'}
              size="small"
              pagination={false}
              scroll={{ x: 1000 }}
              columns={[
                { title: '部位/楼栋', dataIndex: '计算依据', key: 'location', width: 120,
                  render: (v: string) => {
                    const loc = v?.replace('部位:', '')?.split('|')[0] || '整体';
                    return <Tag color="purple">{loc}</Tag>;
                  }
                },
                { title: '材料名称', dataIndex: '材料名称', key: '材料名称', width: 120, fixed: 'left' },
                { title: '阶段', dataIndex: '阶段', key: '阶段', width: 80 },
                { title: '工程量', dataIndex: '工程量', key: '工程量', width: 100, align: 'right',
                  render: (v: number) => v?.toLocaleString() || '-' },
                { title: '基准价', dataIndex: '基准价', key: '基准价', width: 100, align: 'right',
                  render: (v: number) => v?.toLocaleString() || '-' },
                { title: '施工均价', dataIndex: '施工均价', key: '施工均价', width: 100, align: 'right',
                  render: (v: number) => v?.toLocaleString() || '-' },
                { title: '风险幅度', dataIndex: '风险幅度', key: '风险幅度', width: 100,
                  render: (v: string) => <Tag color="blue">{v}</Tag> },
                { title: '是否超幅', dataIndex: '是否超幅', key: '是否超幅', width: 90, align: 'center',
                  render: (v: boolean) => v ? (
                    <Tag color="green" icon={<CheckCircleOutlined />}>是</Tag>
                  ) : (
                    <Tag color="default" icon={<WarningOutlined />}>否</Tag>
                  ) },
                { title: '调整单价', dataIndex: '调整单价', key: '调整单价', width: 100, align: 'right',
                  render: (v: number) => (
                    <span style={{ color: v >= 0 ? '#10B981' : '#FF4D4F' }}>
                      {v?.toLocaleString() || '-'}
                    </span>
                  ) },
                { title: '调整金额', dataIndex: '调整金额', key: '调整金额', width: 110, align: 'right',
                  render: (v: number) => (
                    <span style={{ color: v >= 0 ? '#10B981' : '#FF4D4F', fontWeight: 600 }}>
                      {v?.toLocaleString() || '-'}
                    </span>
                  ) },
                { title: '含税金额', dataIndex: '含税调整金额', key: '含税调整金额', width: 110, align: 'right',
                  render: (v: number) => (
                    <span style={{ color: v >= 0 ? '#10B981' : '#FF4D4F', fontWeight: 600 }}>
                      ¥{v?.toLocaleString() || '-'}
                    </span>
                  ) },
                { title: '计算公式', dataIndex: '计算公式', key: '计算公式', width: 200, ellipsis: true },
              ]}
            />

            {/* 阶段汇总（新增） */}
            {calculationResult.阶段汇总 && calculationResult.阶段汇总.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <strong style={{ color: '#16325C' }}>按阶段汇总</strong>
                <Table
                  dataSource={calculationResult.阶段汇总.map((item: any, idx: number) => ({
                    key: idx,
                    ...item
                  }))}
                  rowKey="key"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '阶段名称', dataIndex: '阶段名称', key: '阶段名称', width: 150,
                      render: (v: string) => <Tag color="blue">{v}</Tag> },
                    { title: '材料种数', dataIndex: '材料种数', key: '材料种数', width: 100, align: 'center' },
                    { title: '小计金额（不含税）', dataIndex: '小计金额（不含税）', key: '小计金额（不含税）', align: 'right',
                      render: (v: number) => v?.toLocaleString() || '-' },
                    { title: '含税小计', dataIndex: '含税小计', key: '含税小计', align: 'right',
                      render: (v: number) => (
                        <span style={{ color: '#10B981', fontWeight: 600 }}>
                          ¥{v?.toLocaleString() || '-'}
                        </span>
                      )
                    },
                  ]}
                />
              </div>
            )}

            {/* 价格校验信息（新增） */}
            {calculationResult.价格校验 && (
              <div style={{ marginTop: 16, padding: 12, background: calculationResult.价格校验.invalid_materials > 0 ? '#FFF7E6' : '#E6F7FF', borderRadius: 8 }}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic
                      title="价格数据完整率"
                      value={calculationResult.价格校验.average_completeness}
                      suffix="%"
                      precision={1}
                      valueStyle={{ color: calculationResult.价格校验.average_completeness >= 80 ? '#52c41a' : '#faad14' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="有效材料数"
                      value={calculationResult.价格校验.valid_materials}
                      suffix={`/ ${calculationResult.价格校验.total_materials}`}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title="问题材料数"
                      value={calculationResult.价格校验.invalid_materials || 0}
                      valueStyle={{ color: (calculationResult.价格校验.invalid_materials || 0) > 0 ? '#ff4d4f' : '#52c41a' }}
                    />
                  </Col>
                </Row>
                {/* 缺失日期详情 */}
                {calculationResult.价格校验.missing_dates && Object.keys(calculationResult.价格校验.missing_dates).length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Alert
                      type="warning"
                      message={`存在 ${Object.keys(calculationResult.价格校验.missing_dates).length} 种材料缺失价格数据`}
                      description={
                        <div style={{ maxHeight: 100, overflowY: 'auto' }}>
                          {Object.entries(calculationResult.价格校验.missing_dates as Record<string, string[]>).map(([material, dates]) => (
                            <div key={material} style={{ marginTop: 4 }}>
                              <Tag color="orange">{material}</Tag>
                              <span style={{ fontSize: 12, color: '#666' }}>缺失 {dates.length} 天: {dates.slice(0, 5).join(', ')}{dates.length > 5 ? '...' : ''}</span>
                            </div>
                          ))}
                        </div>
                      }
                      showIcon
                    />
                  </div>
                )}
              </div>
            )}

            {/* 按部位汇总 */}
            <div style={{ marginTop: 16 }}>
              <strong style={{ color: '#16325C' }}>按部位汇总</strong>
              <Table
                dataSource={(() => {
                  const locationSummary: Record<string, { name: string; amount: number }> = {};
                  (calculationResult.明细 || []).forEach((d: any) => {
                    const loc = d.计算依据?.replace('部位:', '')?.split('|')[0] || '整体';
                    if (!locationSummary[loc]) {
                      locationSummary[loc] = { name: loc, amount: 0 };
                    }
                    locationSummary[loc].amount += d.含税调整金额 || 0;
                  });
                  return Object.values(locationSummary).map((item, idx) => ({
                    key: idx,
                    location: item.name,
                    total: item.amount
                  }));
                })()}
                rowKey="key"
                size="small"
                pagination={false}
                columns={[
                  { title: '部位/楼栋', dataIndex: 'location', key: 'location', width: 200,
                    render: (v: string) => <Tag color="purple">{v}</Tag> },
                  { title: '含税调差金额', dataIndex: 'total', key: 'total', align: 'right',
                    render: (v: number) => (
                      <span style={{ color: '#10B981', fontWeight: 600 }}>
                        ¥{v?.toLocaleString() || '-'}
                      </span>
                    )
                  },
                ]}
              />
            </div>

            {/* 计算信息 */}
            <div style={{ marginTop: 16, padding: 12, background: '#F8FAFC', borderRadius: 8 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <span style={{ color: '#666' }}>项目名称：</span>
                  <strong>{calculationResult.项目名称}</strong>
                </Col>
                <Col span={12}>
                  <span style={{ color: '#666' }}>计算时间：</span>
                  <strong>{new Date(calculationResult.计算时间).toLocaleString()}</strong>
                </Col>
              </Row>
            </div>
          </div>
        )}
      </Modal>

      {/* 项目配置弹窗（保留原有功能） */}
      <Modal
        title={<span style={{ color: 'white' }}>项目配置 - {selectedProject?.name || ''}</span>}
        open={configModalOpen}
        onCancel={() => setConfigModalOpen(false)}
        width={1000}
        footer={[
          <Button key="cancel" onClick={() => setConfigModalOpen(false)}>关闭</Button>,
          <Button key="save" type="primary" onClick={handleSaveMaterials}>保存材料清单</Button>,
        ]}
      >
        <Form form={configForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="项目名称">
                <Input disabled value={selectedProject?.name} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="调差规则">
                <Select disabled value={selectedProject?.rule_name} placeholder="选择预设规则">
                  {PRESET_RULES.map(r => (
                    <Select.Option key={r.name} value={r.name}>{r.name}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>

        <div className="tech-divider" style={{ margin: '16px 0' }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Space>
            <span style={{ fontWeight: 600, color: '#16325C', fontSize: 14 }}>材料清单</span>
            <Tag color="green">{materials.length} 种材料</Tag>
          </Space>
          <Space>
            <Button
              icon={<DatabaseOutlined />}
              onClick={async () => {
                try {
                  const res = await adjustmentTemplateApi.getAutoMaterials({ material_type: '钢筋' });
                  if (res.success && res.materials) {
                    const newMaterials = res.materials.map((m: any, idx: number) => ({
                      name: m.material_name,
                      spec: m.spec,
                      unit: 't',
                      quantity: 0,
                      bid_price: 0,
                      base_price: m.latest_price || 0,
                      phase: '',
                      location: '',
                    }));
                    setMaterials(newMaterials);
                    message.success(`已自动获取 ${newMaterials.length} 种材料`);
                  } else {
                    message.warning('暂无可用材料数据');
                  }
                } catch (err) {
                  console.error('获取材料失败', err);
                  message.error('获取材料失败');
                }
              }}
              style={{ borderColor: '#10B981', color: '#10B981' }}
            >
              自动获取材料
            </Button>
            <Button
              icon={<ThunderboltOutlined />}
              onClick={async () => {
                if (materials.length === 0) {
                  message.warning('请先获取材料清单');
                  return;
                }
                // 批量获取价格
                const materialSpecs = materials.map(m => `${m.name}@${m.spec}`).join(',');
                try {
                  const res = await adjustmentTemplateApi.batchGetPeriodAverage({
                    materials: materialSpecs,
                    start_date: selectedProject?.construction_start || '2024-01-01',
                    end_date: selectedProject?.construction_end || '2024-12-31',
                  });
                  if (res.success && res.results) {
                    const updatedMaterials = materials.map(m => {
                      const found = res.results.find((r: any) => r.material_name === m.name && (!m.spec || r.spec === m.spec));
                      return {
                        ...m,
                        base_price: found?.avg_price || m.base_price || 0,
                      };
                    });
                    setMaterials(updatedMaterials);
                    message.success('价格已更新');
                  }
                } catch (err) {
                  console.error('获取价格失败', err);
                  message.error('获取价格失败');
                }
              }}
              style={{ borderColor: '#4A86C8', color: '#4A86C8' }}
            >
              获取价格
            </Button>
            <Button icon={<PlusOutlined />} onClick={handleAddMaterial}>
              添加
            </Button>
          </Space>
        </div>

        <Table
          dataSource={materials}
          rowKey={(_, index) => index?.toString() || '0'}
          pagination={false}
          size="small"
          scroll={{ x: 900 }}
          columns={[
            { title: '材料名称', dataIndex: 'name', key: 'name', width: 150,
              render: (val, _, index) => (
                <Input value={val} onChange={e => handleMaterialChange(index ?? 0, 'name', e.target.value)} placeholder="如：钢筋HRB400" />
              )
            },
            { title: '规格', dataIndex: 'spec', key: 'spec', width: 100,
              render: (val, _, index) => (
                <Input value={val} onChange={e => handleMaterialChange(index ?? 0, 'spec', e.target.value)} placeholder="如：Φ12" />
              )
            },
            { title: '单位', dataIndex: 'unit', key: 'unit', width: 80,
              render: (val, _, index) => (
                <Select value={val || 't'} onChange={v => handleMaterialChange(index ?? 0, 'unit', v)}
                  options={[{label:'吨(t)',value:'t'},{label:'立方米(m³)',value:'m³'},{label:'米(m)',value:'m'}]}
                />
              )
            },
            { title: '工程量', dataIndex: 'quantity', key: 'quantity', width: 100,
              render: (val, _, index) => (
                <Input type="number" value={val} onChange={e => handleMaterialChange(index ?? 0, 'quantity', parseFloat(e.target.value) || 0)} />
              )
            },
            { title: '投标单价', dataIndex: 'bid_price', key: 'bid_price', width: 100,
              render: (val, _, index) => (
                <Input type="number" value={val} onChange={e => handleMaterialChange(index ?? 0, 'bid_price', parseFloat(e.target.value) || 0)} />
              )
            },
            { title: '基准价', dataIndex: 'base_price', key: 'base_price', width: 100,
              render: (val, _, index) => (
                <Input type="number" value={val} onChange={e => handleMaterialChange(index ?? 0, 'base_price', parseFloat(e.target.value) || 0)} />
              )
            },
            { title: '施工阶段', dataIndex: 'phase', key: 'phase', width: 80,
              render: (val, _, index) => (
                <Input value={val} onChange={e => handleMaterialChange(index ?? 0, 'phase', e.target.value)} placeholder="如：地下室" />
              )
            },
            { title: '部位/楼栋', dataIndex: 'location', key: 'location', width: 100,
              render: (val, _, index) => (
                <Input value={val} onChange={e => handleMaterialChange(index ?? 0, 'location', e.target.value)} placeholder="如：1#楼" />
              )
            },
            { title: '操作', width: 60,
              render: (_, __, index) => (
                <Button size="small" danger onClick={() => handleRemoveMaterial(index ?? 0)}>删除</Button>
              )
            },
          ]}
        />

        {materials.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#F8FAFC', borderRadius: 8, marginTop: 16 }}>
            暂无材料数据，点击"添加材料"开始录入或使用"快速计算"导入Excel
          </div>
        )}
      </Modal>
    </div>
  );
}