import { Card, Form, Input, Select, Switch, Button, Space, Divider, message, Tabs, Tag, Alert } from 'antd'
import { SaveOutlined, SyncOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'

const LOCAL_API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Settings() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [credentialsStatus, setCredentialsStatus] = useState<any>(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    fetchCredentialsStatus()
  }, [])

  const fetchCredentialsStatus = async () => {
    try {
      const response = await fetch(`${LOCAL_API}/api/yantai-prices/credentials`)
      const data = await response.json()
      setCredentialsStatus(data)
    } catch (error) {
      console.error('获取凭据状态失败:', error)
    }
  }

  const handleSave = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('设置已保存')
    }, 1000)
  }

  const handleUpdateCredentials = async (values: any) => {
    setUpdating(true)
    try {
      const response = await fetch(`${LOCAL_API}/api/yantai-prices/update-credentials`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: values.username,
          password: values.password
        })
      })
      const data = await response.json()

      if (data.success) {
        message.success('凭据已更新')
        fetchCredentialsStatus()
      } else {
        message.error(data.message || '更新失败')
      }
    } catch (error) {
      console.error('更新凭据失败:', error)
      message.error('更新凭据失败')
    }
    setUpdating(false)
  }

  return (
    <div>
      <h2>系统设置</h2>

      <Tabs
        items={[
          {
            key: 'general',
            label: '常规设置',
            children: (
              <Card title="常规设置" style={{ maxWidth: 600 }}>
                <Form layout="vertical" form={form}>
                  <Form.Item label="系统名称">
                    <Input defaultValue="TaskPlatform" />
                  </Form.Item>
                  <Form.Item label="时区">
                    <Select defaultValue="Asia/Shanghai">
                      <Select.Option value="Asia/Shanghai">中国标准时间 (UTC+8)</Select.Option>
                      <Select.Option value="UTC">UTC</Select.Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label="语言">
                    <Select defaultValue="zh-CN">
                      <Select.Option value="zh-CN">简体中文</Select.Option>
                      <Select.Option value="en-US">English</Select.Option>
                    </Select>
                  </Form.Item>
                  <Divider />
                  <Space>
                    <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave}>
                      保存设置
                    </Button>
                  </Space>
                </Form>
              </Card>
            ),
          },
          {
            key: 'sync',
            label: '数据同步',
            children: (
              <Card title="云端同步设置" style={{ maxWidth: 600 }}>
                <Form layout="vertical">
                  <Form.Item label="Supabase 项目 URL">
                    <Input placeholder="https://xxxx.supabase.co" />
                  </Form.Item>
                  <Form.Item label="API Key">
                    <Input.Password placeholder="请输入 API Key" />
                  </Form.Item>
                  <Form.Item label="同步模式">
                    <Select defaultValue="realtime">
                      <Select.Option value="realtime">实时同步 (WebSocket)</Select.Option>
                      <Select.Option value="polling">轮询同步 (30秒)</Select.Option>
                      <Select.Option value="manual">手动同步</Select.Option>
                    </Select>
                  </Form.Item>
                  <Form.Item label="自动同步">
                    <Switch defaultChecked />
                  </Form.Item>
                  <Divider />
                  <Space>
                    <Button type="primary" icon={<SyncOutlined />} onClick={() => message.info('同步中...')}>
                      测试连接
                    </Button>
                    <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                      保存
                    </Button>
                  </Space>
                </Form>
              </Card>
            ),
          },
          {
            key: 'scraper',
            label: '抓取设置',
            children: (
              <Card title="价格抓取设置" style={{ maxWidth: 600 }}>
                <Form layout="vertical">
                  <Form.Item label="默认抓取间隔（分钟）">
                    <Space>
                      <Input defaultValue="1440" />
                      <Tag>24小时 = 1440分钟</Tag>
                    </Space>
                  </Form.Item>
                  <Form.Item label="超时时间（秒）">
                    <Input defaultValue="30" />
                  </Form.Item>
                  <Form.Item label="失败重试次数">
                    <Input defaultValue="3" />
                  </Form.Item>
                  <Form.Item label="自动抓取">
                    <Switch defaultChecked />
                  </Form.Item>
                  <Divider />
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                    保存设置
                  </Button>
                </Form>
              </Card>
            ),
          },
          {
            key: 'credentials',
            label: '账号设置',
            children: (
              <Card
                title={
                  <Space>
                    <SafetyCertificateOutlined />
                    <span>我的钢铁网账号</span>
                  </Space>
                }
                style={{ maxWidth: 600 }}
              >
                <Alert
                  message="账号信息仅用于登录我的钢铁网抓取价格数据"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                {credentialsStatus && (
                  <Alert
                    message={`当前用户名: ${credentialsStatus.username || '未设置'}`}
                    type="success"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}

                <Form layout="vertical" onFinish={handleUpdateCredentials}>
                  <Form.Item
                    label="用户名"
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input placeholder="请输入我的钢铁网用户名" />
                  </Form.Item>

                  <Form.Item
                    label="密码"
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password placeholder="请输入我的钢铁网密码" />
                  </Form.Item>

                  <Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit" loading={updating}>
                        更新凭据
                      </Button>
                      <Button onClick={() => fetchCredentialsStatus()}>
                        刷新状态
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>

                <Divider />

                <Form layout="vertical">
                  <Form.Item label="价格URL（可自动获取）">
                    <Input defaultValue="https://jiancai.mysteel.com/m/26051410/25B3355C6617BD3C.html" disabled />
                    <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                      URL会自动从首页获取，无需手动填写
                    </div>
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
          {
            key: 'users',
            label: '用户管理',
            children: (
              <Card title="用户管理" style={{ maxWidth: 600 }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div>
                      <div style={{ fontWeight: 'bold' }}>管理员</div>
                      <div style={{ color: '#666' }}>admin@example.com</div>
                    </div>
                    <Tag color="blue">管理员</Tag>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                    <div>
                      <div style={{ fontWeight: 'bold' }}>用户A</div>
                      <div style={{ color: '#666' }}>user1@example.com</div>
                    </div>
                    <Tag>成员</Tag>
                  </div>
                  <Button type="dashed" block>+ 添加用户</Button>
                </Space>
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}