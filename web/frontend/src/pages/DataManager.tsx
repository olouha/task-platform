import { Card, Button, Table, Space, Tag, Modal, Form, Select, Input, Upload, message, Statistic, Row, Col, Alert, Popconfirm, DatePicker, Divider, Progress } from 'antd'
import { DatabaseOutlined, DownloadOutlined, UploadOutlined, DeleteOutlined, SyncOutlined, FileExcelOutlined, SafetyOutlined, SaveOutlined, ClearOutlined, CloudUploadOutlined, CloudDownloadOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { dataManagerApi, config } from '../services/api'
import dayjs from 'dayjs'
import PageHeader from '../components/PageHeader'

const { RangePicker } = DatePicker

export default function DataManager() {
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [backups, setBackups] = useState<any[]>([])
  const [exportModalVisible, setExportModalVisible] = useState(false)
  const [exportForm] = Form.useForm()
  const [importModalVisible, setImportModalVisible] = useState(false)
  const [importFile, setImportFile] = useState<any>(null)
  const [importProgress, setImportProgress] = useState(0)

  useEffect(() => {
    loadStats()
    loadBackups()
  }, [])

  const loadStats = async () => {
    try {
      const data = await dataManagerApi.getStats()
      if (data.total_records !== undefined) {
        setStats(data)
      }
    } catch (error) {
      console.error('加载统计数据失败:', error)
    }
  }

  const loadBackups = async () => {
    try {
      const data = await dataManagerApi.getBackups()
      if (data.backups) {
        setBackups(data.backups)
      }
    } catch (error) {
      console.error('加载备份列表失败:', error)
    }
  }

  const handleExport = async () => {
    try {
      const values = await exportForm.validateFields()
      setLoading(true)

      const params: any = { format: values.format || 'xlsx' }
      if (values.dateRange && values.dateRange.length === 2) {
        params.start_date = values.dateRange[0].format('YYYY-MM-DD')
        params.end_date = values.dateRange[1].format('YYYY-MM-DD')
      }
      if (values.material) {
        params.material = values.material
      }

      const result = await dataManagerApi.exportData(params)

      if (result.success) {
        message.success(result.message)
        // 自动下载
        dataManagerApi.downloadFile(result.file_name)
      } else {
        message.error(result.message || '导出失败')
      }
    } catch (error) {
      console.error('导出失败:', error)
      message.error('导出失败')
    } finally {
      setLoading(false)
    }
  }

  const handleBackup = async () => {
    try {
      setLoading(true)
      const result = await dataManagerApi.backupDatabase()

      if (result.success) {
        message.success(result.message)
        loadBackups()
      } else {
        message.error(result.message || '备份失败')
      }
    } catch (error) {
      console.error('备份失败:', error)
      message.error('备份失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClean = async () => {
    try {
      setLoading(true)
      const result = await dataManagerApi.cleanData()

      if (result.success) {
        message.success(`清洗完成！删除了 ${result.removed_duplicates} 条重复记录`)
        loadStats()
      } else {
        message.error('清洗失败')
      }
    } catch (error) {
      console.error('清洗失败:', error)
      message.error('清洗失败')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!importFile) {
      message.warning('请先选择要导入的文件')
      return
    }

    try {
      setLoading(true)
      setImportProgress(30)

      // 这里应该上传文件到服务器，然后导入
      // 简化处理：假设文件已经在服务器上
      setImportProgress(60)

      // 实际导入需要先上传文件
      message.info('文件上传功能开发中，请使用服务器命令行导入')

      setImportProgress(100)
    } catch (error) {
      console.error('导入失败:', error)
      message.error('导入失败')
    } finally {
      setLoading(false)
      setImportProgress(0)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const backupColumns = [
    { title: '文件名', dataIndex: 'name', key: 'name' },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => formatFileSize(size)
    },
    {
      title: '创建时间',
      dataIndex: 'created',
      key: 'created',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm')
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => window.open(`${config.apiUrl}/data-manager/download/${record.name}`, '_blank')}
          >
            下载
          </Button>
        </Space>
      )
    }
  ]

  return (
    <div style={{ padding: 24 }}>
      <PageHeader
        title="数据管理"
        subtitle="钢筋价格数据的导出、备份、导入和清洗"
      />

      {/* 数据统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总记录数"
              value={stats?.total_records || 0}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="交易日数"
              value={stats?.total_dates || 0}
              prefix={<CalendarIcon />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="重复记录"
              value={stats?.duplicates || 0}
              prefix={<SyncOutlined />}
              valueStyle={{ color: stats?.duplicates > 0 ? '#faad14' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据日期范围"
              value={stats?.date_range?.start || '-'}
              suffix={`至 ${stats?.date_range?.end || '-'}`}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            size="large"
            block
            onClick={() => setExportModalVisible(true)}
          >
            导出数据
          </Button>
        </Col>
        <Col span={6}>
          <Button
            icon={<SaveOutlined />}
            size="large"
            block
            onClick={handleBackup}
            loading={loading}
          >
            备份数据库
          </Button>
        </Col>
        <Col span={6}>
          <Button
            icon={<ClearOutlined />}
            size="large"
            block
            onClick={() => {
              Modal.confirm({
                title: '确认清洗',
                content: `将删除 ${stats?.duplicates || 0} 条重复记录，此操作不可恢复！`,
                okText: '确认清洗',
                okType: 'danger',
                onOk: handleClean
              })
            }}
            loading={loading}
          >
            清洗数据
          </Button>
        </Col>
        <Col span={6}>
          <Button
            icon={<UploadOutlined />}
            size="large"
            block
            onClick={() => setImportModalVisible(true)}
          >
            导入数据
          </Button>
        </Col>
      </Row>

      {/* 备份列表 */}
      <Card
        title="备份文件列表"
        extra={<Button icon={<SyncOutlined />} onClick={loadBackups}>刷新</Button>}
      >
        {backups.length > 0 ? (
          <Table
            dataSource={backups}
            columns={backupColumns}
            rowKey="name"
            pagination={false}
            size="small"
          />
        ) : (
          <Alert message="暂无备份文件，点击「备份数据库」按钮创建备份" type="info" showIcon />
        )}
      </Card>

      {/* 导出弹窗 */}
      <Modal
        title="导出数据"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setExportModalVisible(false)}>取消</Button>,
          <Button key="export" type="primary" loading={loading} onClick={handleExport} icon={<DownloadOutlined />}>
            导出
          </Button>
        ]}
      >
        <Form form={exportForm} layout="vertical">
          <Form.Item label="导出格式" name="format" initialValue="xlsx">
            <Select
              options={[
                { label: 'Excel 文件 (.xlsx)', value: 'xlsx' },
                { label: 'CSV 文件 (.csv)', value: 'csv' }
              ]}
            />
          </Form.Item>

          <Form.Item label="日期范围（可选）" name="dateRange">
            <RangePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item label="品名筛选（可选）" name="material">
            <Select
              allowClear
              placeholder="选择品名"
              options={[
                { label: '螺纹钢', value: '螺纹钢' },
                { label: '高线', value: '高线' },
                { label: '盘螺', value: '盘螺' },
                { label: '圆钢', value: '圆钢' }
              ]}
            />
          </Form.Item>

          <Alert
            message="导出说明"
            description="导出的文件将包含所有符合筛选条件的钢筋价格数据，包括日期、品名、规格、品牌、价格等信息。"
            type="info"
            showIcon
          />
        </Form>
      </Modal>

      {/* 导入弹窗 */}
      <Modal
        title="导入数据"
        open={importModalVisible}
        onCancel={() => {
          setImportModalVisible(false)
          setImportFile(null)
          setImportProgress(0)
        }}
        footer={[
          <Button key="cancel" onClick={() => setImportModalVisible(false)}>取消</Button>,
          <Button
            key="import"
            type="primary"
            loading={loading}
            onClick={handleImport}
            disabled={!importFile}
            icon={<UploadOutlined />}
          >
            导入
          </Button>
        ]}
      >
        <Alert
          message="导入说明"
          description="支持导入 CSV 格式的价格数据文件。请确保文件包含正确的列名：日期、品名、规格、材质、品牌、价格。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Upload.Dragger
          accept=".csv"
          showUploadList={true}
          beforeUpload={(file) => {
            setImportFile(file)
            return false
          }}
          fileList={importFile ? [importFile as any] : []}
          onRemove={() => setImportFile(null)}
        >
          <p className="ant-upload-drag-icon">
            <CloudUploadOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">点击或拖拽上传 CSV 文件</p>
          <p className="ant-upload-hint">支持 .csv 格式文件</p>
        </Upload.Dragger>

        {importProgress > 0 && (
          <Progress percent={importProgress} style={{ marginTop: 16 }} />
        )}
      </Modal>
    </div>
  )
}

// 日历图标组件
function CalendarIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" style={{ marginRight: 8 }}>
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" fill="none" stroke="currentColor" strokeWidth="2"/>
      <line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" strokeWidth="2"/>
      <line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" strokeWidth="2"/>
      <line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" strokeWidth="2"/>
    </svg>
  )
}
