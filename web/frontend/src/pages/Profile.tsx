/**
 * 个人中心 - 展示当前用户信息 + 修改密码
 */
import { useState, useEffect } from 'react'
import { Card, Descriptions, Form, Input, Button, Tag, Space, message } from 'antd'
import { KeyOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getUserInfo, changePassword, getAccount, logout } from '../auth'

interface UserInfoShape {
  account?: string
  position?: string
  permissions?: string
  is_admin?: boolean
  online_count?: number
}

export default function Profile() {
  const navigate = useNavigate()
  const [userInfo, setUserInfo] = useState<UserInfoShape | null>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    loadUserInfo()
  }, [])

  const loadUserInfo = async () => {
    try {
      const info = await getUserInfo()
      setUserInfo(info)
    } catch {
      message.warning('用户信息获取失败，展示本地记录')
    }
  }

  const handleChangePassword = async (values: { old_password: string; new_password: string; confirm: string }) => {
    if (values.new_password !== values.confirm) {
      message.error('两次输入的新密码不一致')
      return
    }
    setLoading(true)
    try {
      await changePassword(values.old_password, values.new_password)
      message.success('密码修改成功')
      form.resetFields()
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail || '修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 16 }}>个人中心</h2>

      <Card title="账号信息" style={{ marginBottom: 16 }}>
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="账号">{userInfo?.account || getAccount() || '-'}</Descriptions.Item>
          <Descriptions.Item label="职位">{userInfo?.position || '-'}</Descriptions.Item>
          <Descriptions.Item label="权限">{userInfo?.permissions || '-'}</Descriptions.Item>
          <Descriptions.Item label="角色">
            {userInfo?.is_admin ? <Tag color="red">管理员</Tag> : <Tag color="blue">普通用户</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="当前账号在线数">{userInfo?.online_count ?? '-'}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 16 }}>
          <Button onClick={() => navigate('/settings')}>系统设置</Button>
          <Button danger onClick={async () => { await logout(); navigate('/login') }}>退出登录</Button>
        </Space>
      </Card>

      <Card title="修改密码">
        <Form form={form} layout="vertical" onFinish={handleChangePassword} style={{ maxWidth: 400 }}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: '请输入原密码' }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="原密码" />
          </Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 4, message: '密码至少4位' }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="新密码" />
          </Form.Item>
          <Form.Item name="confirm" label="确认新密码" rules={[{ required: true, message: '请再次输入新密码' }]}>
            <Input.Password prefix={<KeyOutlined />} placeholder="确认新密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>修改密码</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
