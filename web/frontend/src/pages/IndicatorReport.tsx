import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Table,
  Tag,
  Progress,
  Alert,
  List,
  Typography,
  Space,
  Statistic,
  message,
  Collapse,
  Tooltip,
  Badge,
} from 'antd';
import {
  BarChartOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  DollarOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useState, useEffect } from 'react';
import PageHeader from '../components/PageHeader';
import { indicatorLibraryApi } from '../services/api';
import type {
  IndicatorLibrarySummary,
  IndicatorLibraryDetail,
} from '../types/indicator';

const { Text, Title } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

interface ProjectForm {
  name: string;
  category: string;
  location: string;
  structure: string;
  floor_above: number;
  floor_below: number;
  area_total: number;
  area_above?: number;
  area_below?: number;
  height: number;
}

interface IndicatorForm {
  unit_cost: number;
  unit_structure?: number;
  unit_installation?: number;
  unit_decoration?: number;
  unit_measure?: number;
  steel_content?: number;
  concrete_content?: number;
}

interface MatchedIndicator {
  project_id: string;
  project_name: string;
  match_score: number;
  recommendation: string;
  height_diff: number;
  height_diff_pct: number;
  category_match: number;
  structure_match: number;
  location_match: number;
  corrected_unit_cost?: number;
  corrected_steel?: number;
  corrected_concrete?: number;
}

interface ComparisonItem {
  indicator_name: string;
  target_value: number;
  reference_value: number;
  corrected_reference?: number;
  deviation: number;
  corrected_deviation?: number;
  status: string;
}

interface CostBreakdown {
  category: string;
  amount: number;
  proportion: number;
}

interface CorrectionFactor {
  factor_type: string;
  factor_value: number;
  reason: string;
}

interface AnalysisReport {
  report_id: string;
  generated_at: string;
  project_id?: string;
  project_name: string;
  project_snapshot?: any;
  matched_indicators: MatchedIndicator[];
  comparison: ComparisonItem[];
  cost_breakdown: CostBreakdown[];
  corrections: CorrectionFactor[];
  suggestions: string[];
  risk_warnings: string[];
}

interface DbSummary {
  total_count: number;
  by_category: Record<string, { count: number; avg_unit_cost: number; avg_steel: number }>;
  by_location: Record<string, number>;
  by_source: Record<string, number>;
  price_range: { min: number; max: number };
}

export default function IndicatorReport() {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [dbSummary, setDbSummary] = useState<DbSummary | null>(null);
  const [activeKey, setActiveKey] = useState<string[]>([]);

  // 指标库列表（与「指标库管理」页同源，用于下拉选择）
  const [dbProjects, setDbProjects] = useState<IndicatorLibrarySummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | undefined>(undefined);
  // 选中项目的详情（含层高/钢筋/混凝土等摘要中不存在的字段）
  const [selectedDetail, setSelectedDetail] = useState<IndicatorLibraryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    loadDbSummary();
    loadDbProjects();
  }, []);

  // 选中项目变化时，拉取详情用于展示摘要卡片
  useEffect(() => {
    if (!selectedProjectId) {
      setSelectedDetail(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    indicatorLibraryApi
      .getDetail(selectedProjectId)
      .then((detail) => {
        if (!cancelled) setSelectedDetail(detail);
      })
      .catch((error) => {
        if (!cancelled) {
          console.error('加载项目详情失败:', error);
          setSelectedDetail(null);
        }
      })
      .finally(() => {
        if (!cancelled) setDetailLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedProjectId]);

  const loadDbSummary = async () => {
    try {
      const res = await fetch('/api/indicator-report/database/summary');
      const data = await res.json();
      setDbSummary(data);
    } catch (error) {
      console.error('加载指标库汇总失败:', error);
    }
  };

  const loadDbProjects = async () => {
    // 数据源：指标库管理页同款 /api/indicator-library/summary
    try {
      const list = await indicatorLibraryApi.getSummary({ limit: 500 });
      setDbProjects(Array.isArray(list) ? list : []);
    } catch (error) {
      console.error('加载指标库列表失败:', error);
      setDbProjects([]);
    }
  };

  const handleGenerateReport = async () => {
    if (!selectedProjectId) {
      message.warning('请先从指标库中选择一个项目');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/indicator-report/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: selectedProjectId }),
      });
      const data = await res.json();
      if (res.ok) {
        setReport(data);
        setActiveKey(['report']);
        message.success('分析报告生成成功');
      } else {
        message.error(data.detail || '报告生成失败');
      }
    } catch (error) {
      console.error('生成报告失败:', error);
      message.error('生成报告失败');
    } finally {
      setLoading(false);
    }
  };

  const matchedColumns = [
    {
      title: '参考项目',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (val: string, record: MatchedIndicator) => (
        <Space>
          <FileTextOutlined />
          <span>{val}</span>
          <Tag color={record.recommendation === '推荐使用' ? 'green' : record.recommendation === '可参考' ? 'orange' : 'red'}>
            {record.recommendation}
          </Tag>
        </Space>
      ),
    },
    {
      title: '匹配分数',
      dataIndex: 'match_score',
      key: 'match_score',
      width: 120,
      render: (val: number) => (
        <Progress
          percent={val}
          size="small"
          strokeColor={val >= 80 ? '#52c41a' : val >= 60 ? '#faad14' : '#f5222d'}
          format={(p) => `${p}分`}
        />
      ),
    },
    {
      title: '层高偏差',
      dataIndex: 'height_diff',
      key: 'height_diff',
      width: 100,
      render: (val: number, record: MatchedIndicator) => (
        <Tooltip title={`偏差 ${record.height_diff_pct}%`}>
          <Text type={val <= 10 ? 'secondary' : val <= 20 ? 'warning' : 'danger'}>
            ±{val}m
          </Text>
        </Tooltip>
      ),
    },
    {
      title: '修正后单方(元/㎡)',
      dataIndex: 'corrected_unit_cost',
      key: 'corrected_unit_cost',
      width: 130,
      render: (val: number) => val ? (
        <Text strong style={{ color: '#16325C' }}>{val.toLocaleString()}</Text>
      ) : '-',
    },
  ];

  const comparisonColumns = [
    {
      title: '指标名称',
      dataIndex: 'indicator_name',
      key: 'indicator_name',
      width: 150,
    },
    {
      title: '目标值',
      dataIndex: 'target_value',
      key: 'target_value',
      width: 120,
      render: (val: number) => <Text strong>{val.toLocaleString()}</Text>,
    },
    {
      title: '原始参考值',
      dataIndex: 'reference_value',
      key: 'reference_value',
      width: 120,
      render: (val: number) => <Text type="secondary">{val.toLocaleString()}</Text>,
    },
    {
      title: '修正后参考',
      dataIndex: 'corrected_reference',
      key: 'corrected_reference',
      width: 120,
      render: (val: number) => val ? <Text style={{ color: '#52c41a' }}>{val.toLocaleString()}</Text> : '-',
    },
    {
      title: '偏差',
      dataIndex: 'deviation',
      key: 'deviation',
      width: 80,
      render: (val: number) => (
        <Text type={Math.abs(val) <= 15 ? 'secondary' : val > 0 ? 'danger' : 'warning'}>
          {val > 0 ? '+' : ''}{val.toFixed(1)}%
        </Text>
      ),
    },
    {
      title: '修正后偏差',
      dataIndex: 'corrected_deviation',
      key: 'corrected_deviation',
      width: 100,
      render: (val: number) => val !== undefined && val !== null ? (
        <Tag color={Math.abs(val) <= 15 ? 'green' : val > 0 ? 'red' : 'blue'}>
          {val > 0 ? '+' : ''}{val.toFixed(1)}%
        </Tag>
      ) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (val: string) => (
        <Tag color={val === '正常' ? 'green' : val === '偏高' ? 'red' : 'blue'}>
          {val}
        </Tag>
      ),
    },
  ];

  const correctionColumns = [
    {
      title: '修正类型',
      dataIndex: 'factor_type',
      key: 'factor_type',
      width: 100,
      render: (val: string) => {
        const colors: Record<string, string> = {
          height: 'blue',
          structure: 'purple',
          region: 'orange',
        };
        const labels: Record<string, string> = {
          height: '高度修正',
          structure: '结构修正',
          region: '地区修正',
        };
        return <Tag color={colors[val] || 'default'}>{labels[val] || val}</Tag>;
      },
    },
    {
      title: '修正系数',
      dataIndex: 'factor_value',
      key: 'factor_value',
      width: 100,
      render: (val: number) => (
        <Text strong type={val !== 1.0 ? 'warning' : 'secondary'}>
          {val.toFixed(2)}
        </Text>
      ),
    },
    {
      title: '说明',
      dataIndex: 'reason',
      key: 'reason',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <PageHeader
        title="指标库分析报告"
        subtitle="基于历史指标数据 + 修正系数生成分析报告"
      />

      {/* 指标库统计 */}
      {dbSummary && (
        <Card style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title="指标库项目总数"
                value={dbSummary.total_count}
                prefix={<BarChartOutlined />}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="单方造价范围"
                value={dbSummary.price_range?.min}
                suffix={`~ ${dbSummary.price_range?.max} 元/㎡`}
                valueStyle={{ fontSize: 16 }}
              />
            </Col>
            {dbSummary.by_category && (
              <>
                <Col span={4}>
                  <Statistic
                    title="商业"
                    value={dbSummary.by_category['商业']?.count || 0}
                    valueStyle={{ fontSize: 20 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="住宅"
                    value={dbSummary.by_category['住宅']?.count || 0}
                    valueStyle={{ fontSize: 20 }}
                  />
                </Col>
                <Col span={4}>
                  <Statistic
                    title="办公"
                    value={dbSummary.by_category['办公']?.count || 0}
                    valueStyle={{ fontSize: 20 }}
                  />
                </Col>
              </>
            )}
          </Row>
        </Card>
      )}

      <Row gutter={24}>
        {/* 左侧：项目信息输入 */}
        <Col span={12}>
          <Card
            title={
              <span>
                <ExperimentOutlined style={{ marginRight: 8 }} />
                项目信息录入
              </span>
            }
          >
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <div>
                <div style={{ marginBottom: 4, color: '#666' }}>选择指标库项目（与「指标库管理」页联动，系统将对该项目进行深度分析）</div>
                <Select
                  showSearch
                  allowClear
                  placeholder="搜索项目名 / 业态 / 地区，选中后点击「生成分析报告」"
                  style={{ width: '100%' }}
                  value={selectedProjectId}
                  onChange={setSelectedProjectId}
                  optionFilterProp="label"
                  filterOption={(input, opt: any) =>
                    (opt?.label as string || '').toLowerCase().includes(input.toLowerCase())
                  }
                  options={dbProjects.map((p) => ({
                    value: p.id,
                    label: `${p.name || '(无名称)'}  ·  ${p.category || ''}  ·  ${p.location || ''}`,
                  }))}
                />
              </div>

              {selectedProjectId && (() => {
                const summary = dbProjects.find((x) => x.id === selectedProjectId);
                // 详情优先（含层高/楼层/钢筋/混凝土），未加载完时回退摘要
                const p: Partial<IndicatorLibraryDetail> = selectedDetail || summary || {};
                if (!p) return null;
                // 钢筋：库内字段为 above_rebar_unit(t/㎡)，转 kg/㎡ 与算法一致
                const steelKg = selectedDetail?.above_rebar_unit != null
                  ? Math.round(selectedDetail.above_rebar_unit * 1000)
                  : undefined;
                return (
                  <Card
                    size="small"
                    title="选中项目摘要"
                    extra={detailLoading ? <Text type="secondary">加载中…</Text> : undefined}
                    style={{ background: '#fafafa' }}
                  >
                    <Row gutter={[16, 8]}>
                      <Col span={12}><Text type="secondary">项目名称：</Text><Text strong> {p.name || '-'}</Text></Col>
                      <Col span={6}><Text type="secondary">业态：</Text>{p.category || '-'}</Col>
                      <Col span={6}><Text type="secondary">地区：</Text>{p.location || '-'}</Col>
                      <Col span={6}><Text type="secondary">结构：</Text>{p.structure || '-'}</Col>
                      <Col span={6}><Text type="secondary">地上/地下层：</Text>{selectedDetail?.floor_above ?? '-'} / {selectedDetail?.floor_below ?? 0}</Col>
                      <Col span={6}><Text type="secondary">檐高(m)：</Text>{selectedDetail?.height ?? '-'}</Col>
                      <Col span={6}><Text type="secondary">总面积(㎡)：</Text>{p.area_total?.toLocaleString?.() ?? '-'}</Col>
                      <Col span={6}><Text type="secondary">单方造价(元/㎡)：</Text><Text strong>{p.unit_cost ?? '-'}</Text></Col>
                      <Col span={6}><Text type="secondary">钢筋(kg/㎡)：</Text>{steelKg ?? '-'}</Col>
                      <Col span={6}><Text type="secondary">混凝土(m³/㎡)：</Text>{selectedDetail?.above_concrete_unit ?? '-'}</Col>
                    </Row>
                  </Card>
                );
              })()}

              <Button
                type="primary"
                size="large"
                block
                icon={<BarChartOutlined />}
                loading={loading}
                disabled={!selectedProjectId}
                onClick={handleGenerateReport}
              >
                生成分析报告
              </Button>

              <Text type="secondary" style={{ fontSize: 12 }}>
                分析 = 该项目 vs 指标库其他项目（业态/结构/地区/层高匹配 + 高度/结构/地区修正 + 对比 + 风险）
              </Text>
            </Space>
          </Card>
        </Col>

        {/* 右侧：分析报告展示 */}
        <Col span={12}>
          <Collapse activeKey={activeKey} onChange={(k) => setActiveKey(k as string[])}>
            <Panel
              header={
                <Badge status={report ? 'success' : 'default'} text="分析报告" />
              }
              key="report"
              disabled={!report}
            >
              {report ? (
                <>
                  {/* 报告头部 */}
                  <Card size="small" style={{ marginBottom: 16 }}>
                    <Row justify="space-between" align="middle">
                      <Col>
                        <Title level={5} style={{ margin: 0 }}>
                          {report.project_name}
                        </Title>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          报告ID: {report.report_id} | {report.generated_at}
                        </Text>
                      </Col>
                      <Col>
                        <Tag color="blue">分析完成</Tag>
                      </Col>
                    </Row>
                    {report.project_snapshot && (
                      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                        <Space size="middle" wrap>
                          <span>业态: {report.project_snapshot.category}</span>
                          <span>地区: {report.project_snapshot.location}</span>
                          <span>结构: {report.project_snapshot.structure}</span>
                          <span>层数: {report.project_snapshot.floor_above}/{report.project_snapshot.floor_below || 0}</span>
                          <span>檐高: {report.project_snapshot.height}m</span>
                          <span>面积: {report.project_snapshot.area_total?.toLocaleString?.() || report.project_snapshot.area_total}㎡</span>
                        </Space>
                      </div>
                    )}
                  </Card>

                  {/* 匹配结果 */}
                  <Card
                    title={
                      <span>
                        <FileTextOutlined style={{ marginRight: 8 }} />
                        匹配指标库项目
                      </span>
                    }
                    size="small"
                    style={{ marginBottom: 16 }}
                    extra={
                      <Text type="secondary">{report.matched_indicators.length} 个匹配</Text>
                    }
                  >
                    <Table
                      dataSource={report.matched_indicators}
                      columns={matchedColumns}
                      rowKey="project_id"
                      pagination={false}
                      size="small"
                    />
                  </Card>

                  {/* 修正系数 */}
                  {report.corrections && report.corrections.length > 0 && (
                    <Card
                      title={
                        <span>
                          <ThunderboltOutlined style={{ marginRight: 8, color: '#faad14' }} />
                          应用修正系数
                        </span>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Table
                        dataSource={report.corrections}
                        columns={correctionColumns}
                        rowKey="factor_type"
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  )}

                  {/* 指标对比 */}
                  {report.comparison && report.comparison.length > 0 && (
                    <Card
                      title={
                        <span>
                          <SafetyCertificateOutlined style={{ marginRight: 8 }} />
                          指标对比分析
                        </span>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Table
                        dataSource={report.comparison}
                        columns={comparisonColumns}
                        rowKey="indicator_name"
                        pagination={false}
                        size="small"
                      />
                    </Card>
                  )}

                  {/* 造价分解 */}
                  {report.cost_breakdown && report.cost_breakdown.length > 0 && (
                    <Card
                      title={
                        <span>
                          <DollarOutlined style={{ marginRight: 8 }} />
                          造价分解
                        </span>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Row gutter={16}>
                        {report.cost_breakdown.map((item, idx) => (
                          <Col span={12} key={idx} style={{ marginBottom: 8 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Text>{item.category}</Text>
                              <Text strong>{item.amount}元/㎡ ({item.proportion}%)</Text>
                            </div>
                            <Progress percent={item.proportion} size="small" showInfo={false} />
                          </Col>
                        ))}
                      </Row>
                    </Card>
                  )}

                  {/* 建议 */}
                  {report.suggestions && report.suggestions.length > 0 && (
                    <Card
                      title={
                        <span>
                          <CheckCircleOutlined style={{ marginRight: 8, color: '#52c41a' }} />
                          分析建议
                        </span>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <List
                        size="small"
                        dataSource={report.suggestions}
                        renderItem={(item) => (
                          <List.Item>
                            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                            {item}
                          </List.Item>
                        )}
                      />
                    </Card>
                  )}

                  {/* 风险提示 */}
                  {report.risk_warnings && report.risk_warnings.length > 0 && (
                    <Card
                      title={
                        <span>
                          <WarningOutlined style={{ marginRight: 8, color: '#faad14' }} />
                          风险提示
                        </span>
                      }
                      size="small"
                    >
                      <Alert
                        message="风险预警"
                        description={
                          <List
                            size="small"
                            dataSource={report.risk_warnings}
                            renderItem={(item) => (
                              <List.Item>
                                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                                {item}
                              </List.Item>
                            )}
                          />
                        }
                        type="warning"
                        showIcon
                      />
                    </Card>
                  )}
                </>
              ) : null}
            </Panel>
          </Collapse>

          {/* 空状态 */}
          {!report && (
            <Card>
              <div style={{ textAlign: 'center', padding: 60 }}>
                <BarChartOutlined style={{ fontSize: 80, color: '#d9d9d9' }} />
                <Title level={4} type="secondary" style={{ marginTop: 16 }}>
                  请在左侧指标库中选择一个项目
                </Title>
                <Text type="secondary">
                  从指标库下拉选一个项目，系统将自动：
                  <br />
                  1. 与指标库其他项目做业态/结构/地区/层高匹配
                  <br />
                  2. 应用高度/结构/地区修正
                  <br />
                  3. 生成详细对比分析报告
                </Text>
              </div>
            </Card>
          )}
        </Col>
      </Row>

      {/* 使用说明 */}
      <Card title="使用说明" style={{ marginTop: 24 }}>
        <Collapse>
          <Panel header="修正系数说明" key="correction">
            <Row gutter={16}>
              <Col span={8}>
                <Card title="高度修正" size="small">
                  <table style={{ width: '100%', fontSize: 12 }}>
                    <tr><td>≤30m</td><td>1.00</td><td>标准层</td></tr>
                    <tr><td>30-60m</td><td>1.03</td><td>增加垂直运输</td></tr>
                    <tr><td>60-100m</td><td>1.08</td><td>显著增加</td></tr>
                    <tr><td>大于100m</td><td>1.15</td><td>超高层</td></tr>
                  </table>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="结构修正" size="small">
                  <table style={{ width: '100%', fontSize: 12 }}>
                    <tr><td>框架结构</td><td>1.00</td></tr>
                    <tr><td>框剪结构</td><td>钢筋1.15</td></tr>
                    <tr><td>剪力墙结构</td><td>钢筋1.25</td></tr>
                    <tr><td>框架核心筒</td><td>钢筋1.20</td></tr>
                  </table>
                </Card>
              </Col>
              <Col span={8}>
                <Card title="地区修正" size="small">
                  <table style={{ width: '100%', fontSize: 12 }}>
                    <tr><td>一线城市</td><td>1.00</td></tr>
                    <tr><td>二线城市</td><td>0.92</td></tr>
                    <tr><td>三线城市</td><td>0.85</td></tr>
                    <tr><td>四线城市</td><td>0.78</td></tr>
                  </table>
                </Card>
              </Col>
            </Row>
          </Panel>
          <Panel header="匹配算法" key="match">
            <p>系统按以下权重计算匹配分数：</p>
            <ul>
              <li>业态类型匹配 (30%)</li>
              <li>结构形式匹配 (25%)</li>
              <li>地区匹配 (20%)</li>
              <li>层高匹配 (25%)</li>
            </ul>
            <p>分数 ≥80分：推荐使用 | 60-80分：可参考 | 小于60分：慎用</p>
          </Panel>
          <Panel header="报告用途" key="usage">
            <p>1. <strong>新项目估算</strong>：基于历史指标快速估算新项目造价</p>
            <p>2. <strong>成本对标</strong>：对比分析项目成本与行业水平的差异</p>
            <p>3. <strong>风险预警</strong>：识别异常指标，提前预警潜在风险</p>
            <p>4. <strong>决策支持</strong>：为投资决策提供数据支撑</p>
          </Panel>
        </Collapse>
      </Card>
    </div>
  );
}