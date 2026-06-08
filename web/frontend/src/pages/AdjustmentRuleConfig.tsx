import { Table, Card, Button, Space, Tag, Row, Col, Statistic, Input, Select, message, Tabs, Collapse, Alert } from 'antd';
import { PlusOutlined, DeleteOutlined, SaveOutlined, SettingOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { adjustmentRulesApi } from '../services/api';
import PageHeader from '../components/PageHeader';

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
}

const PRESET_RULES = [
  { name: '朱家庄', description: '造价信息调整法，风险幅度±3%，不分阶段' },
  { name: '青特地产', description: '标准三段式，分3阶段调差，PC钢筋全额调差，电缆±1000元/吨' },
  { name: '莱山实验小学', description: '固定单价模式，不调差' },
  { name: '豪森海天映月', description: '比例调差法，分2阶段调差，混凝土按甲方代付价，电缆±2000元/吨' },
  { name: '龙湖集团', description: '增值税率换算法，钢筋0%全额调差，混凝土±3%，含税/不含税换算' },
];

const ruleColumns = [
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
    width: 150,
    render: (_: any, record: RuleConfig) => (
      <Space>
        <Button size="small" type="primary" icon={<SettingOutlined />} style={{ background: '#4A86C8', borderColor: '#4A86C8' }}>
          设置
        </Button>
        <Button size="small" danger type="text" icon={<DeleteOutlined />}>删除</Button>
      </Space>
    )
  }
];

export default function AdjustmentRuleConfig() {
  const [rules, setRules] = useState<RuleConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('list');

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
    } finally {
      setLoading(false);
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
          <Button type="primary" icon={<PlusOutlined />}>
            新建规则
          </Button>
        </div>
        <div className="data-section-body">
          <Table
            dataSource={rules}
            columns={ruleColumns}
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
                  <Button type="primary" size="small" style={{ background: '#10B981', borderColor: '#10B981' }}>
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
    </div>
  );
}