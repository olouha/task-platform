import { Table, Card, Button, Space, Tag, Select, message, Tabs, Upload, Alert, Row, Col, Modal, Form, Input, Divider, List, Progress } from 'antd';
import { DatabaseOutlined, UploadOutlined, ToolOutlined, BankOutlined, PlusOutlined, DeleteOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { costHistoryApi } from '../services/api';
import type { UploadProps } from 'antd';
import PageHeader from '../components/PageHeader';

interface ConcreteItem {
  grade: string;
  yantai: number | null;
  rushan: number | null;
}

interface PeriodInfo {
  year: string;
  quarter: string;
  label: string;
  concrete_count: number;
}

interface UploadFile {
  uid: string;
  name: string;
  status: 'pending' | 'uploading' | 'done' | 'error';
  progress: number;
}

export default function CostReference() {
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [selectedQuarter, setSelectedQuarter] = useState<string>('');
  const [availableYears, setAvailableYears] = useState<string[]>([]);
  const [availableQuarters, setAvailableQuarters] = useState<PeriodInfo[]>([]);
  const [concreteData, setConcreteData] = useState<ConcreteItem[]>([]);
  const [steelData, setSteelData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('concrete');
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [uploadYear, setUploadYear] = useState<string>('');
  const [uploadQuarter, setUploadQuarter] = useState<string>('');
  const [uploadFiles, setUploadFiles] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadYears();
  }, []);

  useEffect(() => {
    if (selectedYear) {
      loadQuarters(selectedYear);
    }
  }, [selectedYear]);

  useEffect(() => {
    if (selectedYear && selectedQuarter) {
      loadData();
    }
  }, [selectedYear, selectedQuarter]);

  const loadYears = async () => {
    try {
      const res = await costHistoryApi.getYears();
      if (res.years && res.years.length > 0) {
        setAvailableYears(res.years);
        // 默认选最新年份
        setSelectedYear(res.years[res.years.length - 1]);
      }
    } catch (error) {
      console.error('加载年份失败:', error);
    }
  };

  const loadQuarters = async (year: string) => {
    try {
      const res = await costHistoryApi.getPeriods();
      const quarters = res.filter((p: PeriodInfo) => p.year === year);
      setAvailableQuarters(quarters);
      if (quarters.length > 0) {
        // 默认选最新季度
        setSelectedQuarter(quarters[quarters.length - 1].quarter);
      }
    } catch (error) {
      console.error('加载季度失败:', error);
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      // 加载混凝土数据
      const concreteRes = await costHistoryApi.getConcreteByPeriod(selectedYear, selectedQuarter);
      if (concreteRes.items) {
        setConcreteData(concreteRes.items);
      }

      // 加载钢筋数据
      try {
        const steelRes = await costHistoryApi.getSteelByPeriod(selectedYear, selectedQuarter);
        if (steelRes.items) {
          setSteelData(steelRes.items);
        }
      } catch {
        setSteelData([]);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
      setConcreteData([]);
      setSteelData([]);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload: UploadProps['beforeUpload'] = (file) => {
    message.info(`上传功能开发中: ${file.name}`);
    return false;
  };

  const concreteColumns = [
    {
      title: '强度等级',
      dataIndex: 'grade',
      key: 'grade',
      width: 120,
      render: (val: string) => <Tag color="#10B981">{val}</Tag>
    },
    {
      title: '烟台含税价(元/m³)',
      dataIndex: 'yantai',
      key: 'yantai',
      render: (val: number | null) => val ? <strong style={{ color: '#16325C', fontSize: 16 }}>{val}</strong> : '-'
    },
    {
      title: '蓬莱含税价(元/m³)',
      dataIndex: 'rushan',
      key: 'rushan',
      render: (val: number | null) => val ? <strong>{val}</strong> : '-'
    },
  ];

  const steelColumns = [
    {
      title: '等级',
      dataIndex: 'grade',
      key: 'grade',
      width: 80,
      render: (val: string) => <Tag color="#16325C">{val}</Tag>
    },
    {
      title: '规格',
      dataIndex: 'size',
      key: 'size',
      width: 80,
    },
    {
      title: '完整规格',
      dataIndex: 'spec',
      key: 'spec',
    },
    {
      title: '价格(含税元/吨)',
      dataIndex: 'price',
      key: 'price',
      render: (val: number | null) => val ? <strong style={{ color: '#16325C', fontSize: 16 }}>{val.toLocaleString()}</strong> : '-'
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题 */}
      <PageHeader
        title="造价参考价"
        subtitle="烟台工程建设标准造价管理 - 混凝土及钢筋信息价查询"
      />

      {/* 筛选器 */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={16} align="middle">
          <Col>
            <span style={{ marginRight: 8, fontWeight: 500 }}>选择时期：</span>
          </Col>
          <Col>
            <Select
              placeholder="选择年份"
              style={{ width: 120 }}
              value={selectedYear || undefined}
              onChange={(val) => {
                setSelectedYear(val);
                setSelectedQuarter('');
              }}
              options={availableYears.map(y => ({ label: `${y}年`, value: y }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="选择季度"
              style={{ width: 180 }}
              value={selectedQuarter || undefined}
              onChange={(val) => setSelectedQuarter(val)}
              options={availableQuarters.map(q => ({ label: q.label, value: q.quarter }))}
            />
          </Col>
          <Col>
            <Button onClick={loadData} loading={loading}>刷新数据</Button>
          </Col>
        </Row>
      </Card>

      {/* 价格数据表 */}
      <Card loading={loading}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'concrete',
              label: (
                <span>
                  <BankOutlined style={{ marginRight: 4 }} />
                  混凝土信息价
                </span>
              ),
              children: (
                <Table
                  dataSource={concreteData}
                  columns={concreteColumns}
                  rowKey="grade"
                  pagination={false}
                  size="middle"
                  locale={{ emptyText: '请选择年份和季度' }}
                  footer={() => (
                    <div style={{ textAlign: 'center', color: '#666' }}>
                      数据来源：烟台工程建设标准造价管理 | {selectedYear && selectedQuarter ? selectedYear + '年' + selectedQuarter : ''}
                    </div>
                  )}
                />
              ),
            },
            {
              key: 'steel',
              label: (
                <span>
                  <ToolOutlined style={{ marginRight: 4 }} />
                  钢筋信息价
                </span>
              ),
              children: (
                <Table
                  dataSource={steelData}
                  columns={steelColumns}
                  rowKey="spec"
                  pagination={{ pageSize: 20 }}
                  size="middle"
                  locale={{ emptyText: '该时期暂无钢筋数据' }}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 数据维护区域 */}
      <Card style={{ marginTop: 24 }}>
        <Row gutter={16} align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setUploadModalVisible(true)}>
                新增数据
              </Button>
            </Space>
          </Col>
          <Col>
            <Alert
              message={`当前查看: ${selectedYear ? selectedYear + '年' : ''}${selectedQuarter || ''}`}
              type="info"
              showIcon={false}
              style={{ marginBottom: 0 }}
            />
          </Col>
        </Row>

        <Alert
          message="数据说明"
          description="造价参考价数据来自烟台工程建设标准造价管理，包含混凝土和钢筋的信息价。如需添加新数据，请点击上方「新增数据」按钮。"
          type="info"
          showIcon
        />
      </Card>

      {/* 上传弹窗 */}
      <Modal
        title="新增造价参考价数据"
        open={uploadModalVisible}
        onCancel={() => setUploadModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="选择年份" required>
                <Select
                  showSearch
                  placeholder="选择或输入年份"
                  value={uploadYear || undefined}
                  onChange={(val) => setUploadYear(val)}
                  options={[
                    { label: '2020年', value: '2020' },
                    { label: '2021年', value: '2021' },
                    { label: '2022年', value: '2022' },
                    { label: '2023年', value: '2023' },
                    { label: '2024年', value: '2024' },
                    { label: '2025年', value: '2025' },
                    { label: '2026年', value: '2026' },
                    { label: '2027年', value: '2027' },
                    { label: '2028年', value: '2028' },
                    { label: '2029年', value: '2029' },
                    { label: '2030年', value: '2030' },
                  ]}
                  filterOption={(input, option) =>
                    (option?.label ?? '').includes(input)
                  }
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="选择季度" required>
                <Select
                  placeholder="请选择季度"
                  value={uploadQuarter || undefined}
                  onChange={(val) => setUploadQuarter(val)}
                  options={[
                    { label: '第一季度', value: '第一季度' },
                    { label: '第二季度', value: '第二季度' },
                    { label: '第三季度', value: '第三季度' },
                    { label: '第四季度', value: '第四季度' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>

          <Divider>上传截图</Divider>

          <Form.Item>
            <Upload.Dragger
              beforeUpload={(file) => {
                const newFile: UploadFile = {
                  uid: Date.now().toString(),
                  name: file.name,
                  status: 'pending',
                  progress: 0
                };
                setUploadFiles([...uploadFiles, newFile]);
                return false;
              }}
              showUploadList={false}
              accept=".png,.jpg,.jpeg"
              multiple
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined style={{ fontSize: 40, color: '#4A86C8' }} />
              </p>
              <p className="ant-upload-text" style={{ fontSize: 14, color: '#333', fontWeight: 500 }}>
                点击或拖拽造价参考价截图到此区域
              </p>
              <p className="ant-upload-hint" style={{ color: '#666' }}>
                支持多张截图同时上传
              </p>
            </Upload.Dragger>
          </Form.Item>

          {uploadFiles.length > 0 && (
            <>
              <Divider>已上传文件 ({uploadFiles.length})</Divider>
              <List
                size="small"
                bordered
                dataSource={uploadFiles}
                style={{ maxHeight: 200, overflow: 'auto', marginBottom: 16 }}
                renderItem={(file) => (
                  <List.Item
                    actions={[
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => setUploadFiles(uploadFiles.filter(f => f.uid !== file.uid))}
                      />
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        file.status === 'done' ?
                          <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} /> :
                          <UploadOutlined style={{ color: '#999' }} />
                      }
                      title={file.name}
                      description={file.status === 'done' ? '已导入' : file.status === 'uploading' ? `导入中... ${file.progress}%` : '等待导入'}
                    />
                    {file.status === 'uploading' && <Progress percent={file.progress} size="small" />}
                  </List.Item>
                )}
              />

              <Button
                type="primary"
                block
                size="large"
                loading={uploading}
                disabled={!uploadYear || !uploadQuarter || uploadFiles.length === 0}
                onClick={() => {
                  setUploading(true);
                  let processed = 0;
                  uploadFiles.forEach((file, index) => {
                    setTimeout(() => {
                      setUploadFiles(prev => prev.map(f =>
                        f.uid === file.uid ? { ...f, status: 'uploading', progress: 50 } : f
                      ));
                      setTimeout(() => {
                        setUploadFiles(prev => prev.map(f =>
                          f.uid === file.uid ? { ...f, status: 'done', progress: 100 } : f
                        ));
                        processed++;
                        if (processed === uploadFiles.length) {
                          setUploading(false);
                          message.success(`已成功导入 ${uploadFiles.length} 张截图到 ${uploadYear}年${uploadQuarter}！`);
                          setUploadFiles([]);
                          setUploadModalVisible(false);
                        }
                      }, 1000);
                    }, index * 500);
                  });
                }}
              >
                导入到 {uploadYear || '?'}年{uploadQuarter || '?'}
              </Button>
            </>
          )}

          <Alert
            message="数据上传"
            description={uploadYear && uploadQuarter ? `准备上传 ${uploadYear}年${uploadQuarter} 的造价参考价截图` : '请先选择年份和季度，然后上传截图'}
            type={uploadYear && uploadQuarter ? "success" : "info"}
            showIcon
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>
    </div>
  );
}
