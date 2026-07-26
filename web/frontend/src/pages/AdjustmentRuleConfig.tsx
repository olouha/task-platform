import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Row,
  Col,
  Statistic,
  Input,
  Select,
  message,
  Tabs,
  Collapse,
  Alert,
  Modal,
  Form,
  Popconfirm,
} from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined, SettingOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { adjustmentRulesApi } from '../services/api';
import PageHeader from '../components/PageHeader';
import { getStoredIsAdmin, getStoredPosition } from '../auth';

// 全权限职位
const FULL_ACCESS_POSITIONS = ['管理层', '开发人员', '办公室团队']

const { Panel } = Collapse;

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

interface MaterialBidPrice {
  name: string;
  spec: string;
  unit: string;
  bid_price: number;
}

interface RuleConfig {
  id?: string;
  name?: string;
  config?: any;
  bid_prices?: MaterialBidPrice[];
  derived_from?: string | null;
  is_preset?: boolean;
  created_at?: string;
  updated_at?: string;
}

const PRESET_RULES = [
  { name: '朱家庄', description: '造价信息调整法，风险幅度±3%，不分阶段' },
  { name: '青特地产', description: '标准三段式，分3阶段调差，PC钢筋全额调差，电缆±1000元/吨' },
  { name: '莱山实验小学', description: '固定单价模式，不调差' },
  { name: '豪森海天映月', description: '比例调差法，分2阶段调差，混凝土按甲方代付价，电缆±2000元/吨' },
  { name: '龙湖集团', description: '增值税率换算法，钢筋0%全额调差，混凝土±3%，含税/不含税换算' },
];

const ruleColumns = (
  onEdit: (record: RuleConfig) => void,
  onDelete: (record: RuleConfig) => void,
  canDelete: boolean
) => [
  { title: '规则名称', dataIndex: 'name', key: 'name' },
  {
    title: '类型',
    dataIndex: 'is_preset',
    key: 'is_preset',
    render: (isPreset: boolean) => (
      <Tag style={{ background: isPreset ? '#4A86C8' : '#10B981', color: 'white', border: 'none' }}>
        {isPreset ? '预设' : '自定义'}
      </Tag>
    )
  },
  {
    title: '基准价来源',
    key: 'base_source',
    render: (_: any, record: RuleConfig) => {
      const config = record.config || {};
      const source = config.价格规则?.基准价来源 || '-';
      return <Tag>{source}</Tag>;
    }
  },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
    render: (d: string) => d ? new Date(d).toLocaleDateString() : '-' },
  {
    title: '操作',
    key: 'action',
    width: 180,
    render: (_: any, record: RuleConfig) => (
      <Space>
        <Button
          size="small"
          type="primary"
          icon={<SettingOutlined />}
          style={{ background: '#4A86C8', borderColor: '#4A86C8' }}
          onClick={() => onEdit(record)}
        >
          设置
        </Button>
        {canDelete && (
          <Popconfirm
            title="确定删除该规则？"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => onDelete(record)}
          >
            <Button size="small" danger type="text" icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        )}
      </Space>
    )
  }
];

export default function AdjustmentRuleConfig() {
  const [rules, setRules] = useState<RuleConfig[]>([]);
  const [loading, setLoading] = useState(false);
  // 是否具有删除权限
  const canDelete = getStoredIsAdmin() || FULL_ACCESS_POSITIONS.includes((getStoredPosition() || '').trim());

  // 编辑规则 Modal
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<RuleConfig | null>(null);
  const [editForm] = Form.useForm();

  // 应用预设 Modal
  const [applyOpen, setApplyOpen] = useState(false);
  const [applyPresetName, setApplyPresetName] = useState<string>('');
  const [applyProjectName, setApplyProjectName] = useState<string>('');
  const [applySubmitting, setApplySubmitting] = useState(false);

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await adjustmentRulesApi.list();
      setRules(res.rules || []);
    } catch (err) {
      console.error('获取规则失败', err);
      message.error('获取规则失败');
    } finally {
      setLoading(false);
    }
  };

  // 新建规则（打开 Modal，让用户填项目名后创建一条空规则）
  const handleCreate = () => {
    setEditing(null);
    editForm.resetFields();
    editForm.setFieldsValue({
      项目名称: '',
      调差项目: [],
      价格规则: {},
      周期与阶段: {},
      计算公式: {},
      特殊规则: {},
    });
    setEditOpen(true);
  };

  // 设置（编辑已有规则）
  const handleEdit = (record: RuleConfig) => {
    setEditing(record);
    const cfg = record.config || {};
    editForm.setFieldsValue({
      项目名称: record.name || cfg.项目名称 || '',
      调差项目: cfg.调差项目 || [],
      价格规则: cfg.价格规则 || {},
      周期与阶段: cfg.周期与阶段 || {},
      计算公式: cfg.计算公式 || {},
      特殊规则: cfg.特殊规则 || {},
    });
    setEditOpen(true);
  };

  // 删除
  const handleDelete = async (record: RuleConfig) => {
    if (!record.id) {
      message.warning('该规则无 id，无法删除');
      return;
    }
    try {
      const res = await adjustmentRulesApi.delete(record.id);
      if (res?.success) {
        message.success('已删除');
        fetchRules();
      } else {
        message.error(res?.detail || '删除失败');
      }
    } catch (err: any) {
      console.error('删除失败', err);
      message.error(err?.message || '删除失败');
    }
  };

  // 提交 Modal 表单
  const handleSubmitEdit = async () => {
    try {
      const values = await editForm.validateFields();
      const payload = {
        项目名称: values.项目名称,
        调差项目: values.调差项目 || [],
        价格规则: values.价格规则 || {},
        周期与阶段: values.周期与阶段 || {},
        计算公式: values.计算公式 || {},
        特殊规则: values.特殊规则 || {},
      };

      if (editing?.id) {
        const res = await adjustmentRulesApi.update(editing.id, payload);
        if (res?.success) {
          message.success('规则已更新');
          setEditOpen(false);
          fetchRules();
        } else {
          message.error(res?.detail || '更新失败');
        }
      } else {
        const res = await adjustmentRulesApi.create(payload);
        if (res?.success) {
          message.success('规则已创建');
          setEditOpen(false);
          fetchRules();
        } else {
          message.error(res?.detail || '创建失败');
        }
      }
    } catch (err: any) {
      if (err?.errorFields) {
        message.warning('请检查表单必填项');
      } else {
        console.error('提交失败', err);
        message.error(err?.message || '提交失败');
      }
    }
  };

  // 应用预设规则
  const openApplyPreset = (presetName: string) => {
    setApplyPresetName(presetName);
    setApplyProjectName(`${presetName}-副本`);
    setApplyOpen(true);
  };

  const handleApplyPreset = async () => {
    if (!applyProjectName.trim()) {
      message.warning('请输入项目名称');
      return;
    }
    setApplySubmitting(true);
    try {
      const res = await adjustmentRulesApi.applyPreset(applyPresetName, applyProjectName.trim());
      if (res?.success) {
        message.success(`已应用预设「${applyPresetName}」为「${applyProjectName}」`);
        setApplyOpen(false);
        fetchRules();
      } else {
        message.error(res?.detail || '应用失败');
      }
    } catch (err: any) {
      console.error('应用预设失败', err);
      message.error(err?.message || '应用预设失败');
    } finally {
      setApplySubmitting(false);
    }
  };

  return (
    <div>
      {/* 页面标题 - 科技风格 */}
      <PageHeader
        title="调差规则配置"
        subtitle="配置调差计算规则，支持预设规则与应用"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="预设规则"
          value={PRESET_RULES.length}
          icon={<SettingOutlined />}
          color="#16325C"
          suffix="个规则"
        />
        <TechStatCard
          title="自定义规则"
          value={rules.length}
          icon={<PlusOutlined />}
          color="#4A86C8"
          suffix="个规则"
        />
        <TechStatCard
          title="配置项"
          value={24}
          icon={<SettingOutlined />}
          color="#10B981"
          suffix="项配置"
        />
      </div>

      {/* 规则列表 */}
      <div className="data-section" style={{ marginBottom: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <SettingOutlined />
            <span>规则列表</span>
          </div>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            新建规则
          </Button>
        </div>
        <div className="data-section-body">
          <Table
            dataSource={rules}
            columns={ruleColumns(handleEdit, handleDelete, canDelete)}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: '暂无规则，点击新建规则开始配置' }}
          />
        </div>
      </div>

      {/* 预设规则 */}
      <div className="data-section" style={{ marginBottom: 24 }}>
        <div className="data-section-header">
          <div className="data-section-title">
            <SettingOutlined />
            <span>预设规则</span>
          </div>
        </div>
        <div className="data-section-body">
          <Table
            dataSource={PRESET_RULES}
            rowKey="name"
            pagination={false}
            columns={[
              { title: '规则名称', dataIndex: 'name', width: 150 },
              { title: '说明', dataIndex: 'description' },
              {
                title: '操作',
                width: 120,
                render: (_, record) => (
                  <Button
                    type="primary"
                    size="small"
                    style={{ background: '#10B981', borderColor: '#10B981' }}
                    onClick={() => openApplyPreset(record.name)}
                  >
                    应用此规则
                  </Button>
                )
              }
            ]}
          />
        </div>
      </div>

      {/* 配置说明 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <SettingOutlined />
            <span>24项配置说明</span>
          </div>
        </div>
        <div className="data-section-body">
          <Collapse defaultActiveKey={['1']}>
            <Panel header="1. 基础信息类（4项）" key="1">
              <ul style={{ lineHeight: 2 }}>
                <li><strong>调差项目</strong> - 可调差的材料种类（钢筋、商品混凝土等）</li>
                <li><strong>是否必调</strong> - 必选 / 可选 / 不调整</li>
                <li><strong>调差范围</strong> - 明确哪些费用参与调差（如仅调材料原价）</li>
                <li><strong>工程量范围</strong> - 明确哪些部位工程量参与调差</li>
              </ul>
            </Panel>
            <Panel header="2. 价格规则类（6项）" key="2">
              <ul style={{ lineHeight: 2 }}>
                <li><strong>风险幅度</strong> - 价格波动容忍范围（如±3%、±1000元/吨）</li>
                <li><strong>基准价来源</strong> - 造价信息 / 我的钢铁网 / 投标价 / 合同约定价</li>
                <li><strong>基准价取价规则</strong> - 如何确定基准价</li>
                <li><strong>施工期价格采集规则</strong> - 每月取价日期、平均方式</li>
                <li><strong>节假日/无价处理规则</strong> - 顺延1天 / 取前后日均价 / 取上月价</li>
                <li><strong>价格取整规则</strong> - 取整到元 / 保留2位小数</li>
              </ul>
            </Panel>
            <Panel header="3. 周期与阶段类（5项）" key="3">
              <ul style={{ lineHeight: 2 }}>
                <li><strong>是否分阶段调差</strong> - 是 / 否</li>
                <li><strong>阶段划分方式</strong> - 地下室/主体/建筑</li>
                <li><strong>阶段起始/结束点</strong> - 各阶段的开始和结束条件</li>
                <li><strong>短周期处理</strong> - ≤7天的施工期如何处理</li>
              </ul>
            </Panel>
            <Panel header="4. 计算公式类（4项）" key="4">
              <ul style={{ lineHeight: 2 }}>
                <li><strong>调差公式模板</strong> - 支持5种公式模板</li>
                <li><strong>税率</strong> - 增值税率（3%、9%、13%）</li>
                <li><strong>负数处理</strong> - 跌价时：扣回 / 不调整 / 按实计算</li>
                <li><strong>取费规则</strong> - 调差金额的取费方式</li>
              </ul>
            </Panel>
            <Panel header="5. 特殊规则类（5项）" key="5">
              <ul style={{ lineHeight: 2 }}>
                <li><strong>供货方式调差权限</strong> - 乙供/甲供/甲指乙供是否可调</li>
                <li><strong>工期延误处理</strong> - 承包人/发包人原因延误时的规则</li>
                <li><strong>工程量计算规则</strong> - 如何计算参与调差的工程量</li>
                <li><strong>变更签证是否参与</strong> - 是 / 否</li>
                <li><strong>业态例外规则</strong> - 特殊业态的处理</li>
              </ul>
            </Panel>
          </Collapse>
        </div>
      </div>

      {/* 新建/编辑规则 Modal */}
      <Modal
        title={editing ? `编辑规则：${editing.name || ''}` : '新建规则'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSubmitEdit}
        okText="保存"
        cancelText="取消"
        width={560}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" preserve={false}>
          <Form.Item
            label="项目名称"
            name="项目名称"
            rules={[{ required: true, message: '请输入项目名称' }]}
          >
            <Input placeholder="例如：朱家庄A区项目" maxLength={200} />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="其余字段（调差项目、价格规则、周期与阶段、计算公式、特殊规则）暂以 JSON 形式保存，保存后会原样存入 config。后续如需表单化编辑可在此基础上扩展。"
            style={{ marginBottom: 12 }}
          />
          <Form.Item label="调差项目（JSON）" name="调差项目">
            <Input.TextArea
              rows={3}
              placeholder='例如：[{"名称":"钢筋","是否必调":"必选"}]'
            />
          </Form.Item>
          <Form.Item label="价格规则（JSON）" name="价格规则">
            <Input.TextArea
              rows={3}
              placeholder='例如：{"基准价来源":"造价信息","风险幅度":{"钢筋":{"类型":"百分比","值":3}}}'
            />
          </Form.Item>
          <Form.Item label="周期与阶段（JSON）" name="周期与阶段">
            <Input.TextArea rows={2} placeholder='例如：{"是否分阶段调差":"否"}' />
          </Form.Item>
          <Form.Item label="计算公式（JSON）" name="计算公式">
            <Input.TextArea rows={2} placeholder='例如：{"调差公式模板":"标准三段式","税率":9}' />
          </Form.Item>
          <Form.Item label="特殊规则（JSON）" name="特殊规则">
            <Input.TextArea rows={2} placeholder='可选' />
          </Form.Item>
        </Form>
      </Modal>

      {/* 应用预设 Modal */}
      <Modal
        title={`应用预设：${applyPresetName}`}
        open={applyOpen}
        onCancel={() => setApplyOpen(false)}
        onOk={handleApplyPreset}
        okText="应用"
        cancelText="取消"
        confirmLoading={applySubmitting}
        destroyOnClose
      >
        <p style={{ marginBottom: 12 }}>
          将把预设规则「{applyPresetName}」的配置复制为新的自定义规则。
        </p>
        <Input
          placeholder="项目名称"
          value={applyProjectName}
          onChange={(e) => setApplyProjectName(e.target.value)}
          maxLength={200}
        />
      </Modal>
    </div>
  );
}