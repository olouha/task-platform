/**
 * 管理员用户管理页面
 * bangongshi01 账号登录后可访问
 */
import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Popconfirm, Space } from 'antd'
import { PlusOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons'
import { getAllUsersWithPassword, addUser, adminChangePassword, deleteUser, logout } from '../auth'
import './UserManagement.css'

interface User {
  account: string
  password: string
  position: string
  permissions: string
}

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [passwordModalVisible, setPasswordModalVisible] = useState(false)
  const [selectedUser, setSelectedUser] = useState<string>('')
  const [form] = Form.useForm()
  const [passwordForm] = Form.useForm()

  useEffect(() => {
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoading(true)
    try {
      const data = await getAllUsersWithPassword()
      setUsers(data)
    } catch (error: any) {
      message.error(error.response?.data?.detail || '获取用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAddUser = async (values: any) => {
    try {
      await addUser(values.account, values.password, values.position, values.permissions)
      message.success('用户添加成功')
      setModalVisible(false)
      form.resetFields()
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '添加失败')
    }
  }

  const handleChangePassword = async (values: { new_password: string }) => {
    try {
      await adminChangePassword(selectedUser, values.new_password)
      message.success('密码修改成功')
      setPasswordModalVisible(false)
      passwordForm.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '修改失败')
    }
  }

  const handleDeleteUser = async (account: string) => {
    try {
      await deleteUser(account)
      message.success('用户已删除')
      loadUsers()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const handleLogout = async () => {
    await logout()
    window.location.href = '/login'
  }

  const columns = [
    {
      title: '账号',
      dataIndex: 'account',
      key: 'account',
      width: 120,
    },
    {
      title: '密码',
      dataIndex: 'password',
      key: 'password',
      width: 100,
      render: (text: string) => '••••••',
    },
    {
      title: '职位',
      dataIndex: 'position',
      key: 'position',
      width: 100,
    },
    {
      title: '权限',
      dataIndex: 'permissions',
      key: 'permissions',
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<KeyOutlined />}
            onClick={() => {
              setSelectedUser(record.account)
              setPasswordModalVisible(true)
            }}
          >
            修改密码
          </Button>
          <Popconfirm
            title="确定删除此用户？"
            onConfirm={() => handleDeleteUser(record.account)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="user-management-page">
      <div className="page-header">
        <h2>用户管理</h2>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            新增用户
          </Button>
          <Button onClick={handleLogout}>退出登录</Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="account"
        loading={loading}
        pagination={false}
      />

      {/* 新增用户弹窗 */}
      <Modal
        title="新增用户"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleAddUser}>
          <Form.Item name="account" label="账号" rules={[{ required: true, message: '请输入账号' }]}>
            <Input placeholder="请输入账号" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }, { min: 4, message: '密码至少4位' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item name="position" label="职位" rules={[{ required: true, message: '请输入职位' }]}>
            <Input placeholder="如：开发人员" />
          </Form.Item>
          <Form.Item name="permissions" label="权限" rules={[{ required: true, message: '请选择权限' }]}>
            <Select placeholder="请选择权限">
              <Select.Option value="所有权限都打开">所有权限都打开</Select.Option>
              <Select.Option value="指标库指标上传后不允许删除">指标库指标上传后不允许删除</Select.Option>
              <Select.Option value="所有权限都打开，可以增加账号和管理权限">所有权限都打开，可以增加账号和管理权限</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">确定</Button>
              <Button onClick={() => setModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改密码弹窗 */}
      <Modal
        title={`修改 ${selectedUser} 的密码`}
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false)
          passwordForm.resetFields()
        }}
        footer={null}
      >
        <Form form={passwordForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, message: '请输入新密码' }, { min: 4, message: '密码至少4位' }]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">确定</Button>
              <Button onClick={() => setPasswordModalVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
