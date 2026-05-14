import { Layout, Menu, Avatar, Dropdown, Badge } from 'antd'
import {
  DashboardOutlined,
  ProjectOutlined,
  AppstoreOutlined,
  DollarOutlined,
  CalculatorOutlined,
  LineChartOutlined,
  SettingOutlined,
  UserOutlined,
  BellOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'

const { Header, Sider, Content } = Layout

interface AppLayoutProps {
  children: React.ReactNode
}

export default function AppLayout({ children }: AppLayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [syncing, setSyncing] = useState(false)

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/projects', icon: <ProjectOutlined />, label: '项目管理' },
    { key: '/materials', icon: <AppstoreOutlined />, label: '材料管理' },
    { key: '/prices', icon: <DollarOutlined />, label: '价格监控' },
    { key: '/adjustments', icon: <CalculatorOutlined />, label: '调差计算' },
    { key: '/indicators', icon: <LineChartOutlined />, label: '指标库' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  const syncData = () => {
    setSyncing(true)
    setTimeout(() => setSyncing(false), 2000)
  }

  return (
    <Layout>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{ borderRight: '1px solid #f0f0f0' }}
      >
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid #f0f0f0' }}>
          {collapsed ? (
            <span style={{ fontSize: 20, fontWeight: 'bold', color: '#1890ff' }}>TP</span>
          ) : (
            <span style={{ fontSize: 18, fontWeight: 'bold', color: '#1890ff' }}>TaskPlatform</span>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0, marginTop: 8 }}
        />
      </Sider>

      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0' }}>
          <div style={{ fontSize: 14, color: '#666' }}>
            工程调差计算系统
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Badge count={3}>
              <BellOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
            </Badge>

            <Badge dot>
              <SyncOutlined
                style={{ fontSize: 18, cursor: 'pointer', color: syncing ? '#1890ff' : '#666' }}
                spin={syncing}
                onClick={syncData}
              />
            </Badge>

            <Dropdown menu={{ items: [{ key: 'logout', label: '退出登录' }] }} placement="bottomRight">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} style={{ backgroundColor: '#1890ff' }} />
                <span>管理员</span>
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content style={{ padding: 24, minHeight: 'calc(100vh - 64px)', overflow: 'auto' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}