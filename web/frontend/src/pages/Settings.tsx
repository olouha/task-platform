import { Card, Form, Input, Select, Switch, Button, Space, Divider, message, Tabs, Alert, Tag } from 'antd'
import { SaveOutlined, SyncOutlined, SafetyCertificateOutlined, SettingOutlined, CloudOutlined, DatabaseOutlined, UserOutlined, KeyOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { yantaiRebarApi } from '../services/api'
import { changePassword as apiChangePassword, getUserInfo } from '../auth'
import PageHeader from '../components/PageHeader'

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

export default function Settings() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [credentialsStatus, setCredentialsStatus] = useState<any>(null)
  const [updating, setUpdating] = useState(false)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    fetchCredentialsStatus()
    fetchUserInfo()
  }, [])

  const fetchCredentialsStatus = async () => {
    try {
      const data = await yantaiRebarApi.getCredentialsStatus()
      setCredentialsStatus(data)
    } catch (error) {
      console.error('获取凭据状态失败:', error)
    }
  }

  const fetchUserInfo = async () => {
    try {
      const data = await getUserInfo()
      setUserInfo(data)
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }

  const handleSave = () => {
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      message.success('设置已保存')
    }, 1000)
  }

  const handleChangePassword = async (values: { old_password: string, new_password: string }) => {
    if (values.new_password.length < 4) {
      message.error('新密码至少4位')
      return
    }
    setChangingPassword(true)
    try {
      await apiChangePassword(values.old_password, values.new_password)
      message.success('密码修改成功')
      passwordForm.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '密码修改失败')
    } finally {
      setChangingPassword(false)
    }
  }

  const handleUpdateCredentials = async (values: any) => {
    setUpdating(true)
    try {
      const data = await yantaiRebarApi.updateCredentials(values.username, values.password)

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
      {/* 页面标题 - 科技风格 */}
      <PageHeader
        title="系统设置"
        subtitle="配置系统参数与账号信息"
      />

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: 24 }}>
        <TechStatCard
          title="系统版本"
          value="v1.0"
          icon={<DatabaseOutlined />}
          color="#16325C"
          suffix="当前版本"
        />
        <TechStatCard
          title="数据连接"
          value="正常"
          icon={<CloudOutlined />}
          color="#10B981"
          suffix="服务在线"
        />
        <TechStatCard
          title="账号状态"
          value={credentialsStatus?.username ? '已配置' : '未配置'}
          icon={<SafetyCertificateOutlined />}
          color={credentialsStatus?.username ? '#10B981' : '#F59E0B'}
          suffix={credentialsStatus?.username || '需要配置'}
        />
      </div>

      {/* 设置内容 */}
      <div className="data-section">
        <div className="data-section-header">
          <div className="data-section-title">
            <SettingOutlined />
            <span>系统配置</span>
          </div>
        </div>
        <div className="data-section-body">
          <Tabs
            items={[
              {
                key: 'profile',
                label: '个人中心',
                children: (
                  <Card style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}>
                    <div style={{ marginBottom: 24 }}>
                      <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>当前账号信息</div>
                      <div style={{ display: 'flex', gap: 24 }}>
                        <div>
                          <div style={{ fontSize: 12, color: '#999' }}>账号</div>
                          <div style={{ fontSize: 16, fontWeight: 500, color: '#333' }}>{userInfo?.account || '-'}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: 12, color: '#999' }}>职位</div>
                          <div style={{ fontSize: 16, fontWeight: 500, color: '#333' }}>{userInfo?.position || '-'}</div>
                        </div>
                      </div>
                    </div>
                    <Divider>修改密码</Divider>
                    <Form layout="vertical" form={passwordForm} onFinish={handleChangePassword}>
                      <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
                        <Input.Password placeholder="请输入原密码" />
                      </Form.Item>
                      <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 4, message: '密码至少4位' }]}>
                        <Input.Password placeholder="请输入新密码（至少4位）" />
                      </Form.Item>
                      <Form.Item>
                        <Button type="primary" icon={<KeyOutlined />} htmlType="submit" loading={changingPassword}>
                          修改密码
                        </Button>
                      </Form.Item>
                    </Form>
                  </Card>
                ),
              },
              {
                key: 'general',
                label: '常规设置',
                children: (
                  <Card style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}>
                    <Form layout="vertical" form={form}>
                      <Form.Item label="系统名称">
                        <Input defaultValue="Knights" />
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
                      <Button type="primary" icon={<SaveOutlined />} loading={loading} onClick={handleSave}>
                        保存设置
                      </Button>
                    </Form>
                  </Card>
                ),
              },
              {
                key: 'sync',
                label: '数据同步',
                children: (
                  <Card style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}>
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
                  <Card style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}>
                    <Form layout="vertical">
                      <Form.Item label="默认抓取间隔（分钟）">
                        <Space>
                          <Input defaultValue="1440" style={{ width: 120 }} />
                          <Tag color="#4A86C8">24小时 = 1440分钟</Tag>
                        </Space>
                      </Form.Item>
                      <Form.Item label="超时时间（秒）">
                        <Input defaultValue="30" style={{ width: 120 }} />
                      </Form.Item>
                      <Form.Item label="失败重试次数">
                        <Input defaultValue="3" style={{ width: 120 }} />
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
                    style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}
                    title={<span><SafetyCertificateOutlined style={{ color: '#4A86C8' }} /> 我的钢铁网账号</span>}
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
                  <Card style={{ maxWidth: 600, border: '1px solid #E8EBF0' }}>
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #E8EBF0' }}>
                        <div>
                          <div style={{ fontWeight: 'bold', color: '#333' }}>管理员</div>
                          <div style={{ color: '#666' }}>admin@example.com</div>
                        </div>
                        <Tag style={{ background: '#16325C', color: 'white', border: 'none' }}>管理员</Tag>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #E8EBF0' }}>
                        <div>
                          <div style={{ fontWeight: 'bold', color: '#333' }}>用户A</div>
                          <div style={{ color: '#666' }}>user1@example.com</div>
                        </div>
                        <Tag>成员</Tag>
                      </div>
                      <Button type="dashed" block icon={<UserOutlined />}>添加用户</Button>
                    </Space>
                  </Card>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  )
}