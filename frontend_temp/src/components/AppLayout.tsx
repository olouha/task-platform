import { Layout, Menu, Avatar, Dropdown, Badge, Tooltip } from 'antd'
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
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
} from '@ant-design/icons'
import { useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import AIChatWindow from './AIChatWindow'

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
    { key: '/cost-reference', icon: <CalculatorOutlined />, label: '造价参考价' },
    { key: '/adjustments/rules', icon: <SettingOutlined />, label: '规则配置' },
    { key: '/indicators', icon: <LineChartOutlined />, label: '指标库' },
    { key: '/indicator-report', icon: <LineChartOutlined />, label: '指标分析报告' },
    { key: '/data-manager', icon: <SyncOutlined />, label: '数据管理' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  const syncData = () => {
    setSyncing(true)
    setTimeout(() => setSyncing(false), 2000)
  }

  return (
    <Layout className="app-layout">
      <Sider
        className="app-sidebar"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={220}
        collapsedWidth={64}
      >
        {/* Logo 区域 - 白底圆角方形框内logo */}
        <div className="sidebar-logo">
          {collapsed ? (
            <div style={{
              width: 44,
              height: 44,
              borderRadius: 10,
              background: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 4,
              boxShadow: '0 4px 15px rgba(74, 134, 200, 0.4)',
            }}>
              <img
                src="/logo.jpg"
                alt="Logo"
                style={{
                  width: '100%',
                  height: '100%',
                  borderRadius: 6,
                  objectFit: 'cover',
                }}
              />
            </div>
          ) : (
            <div style={{
              height: 44,
              borderRadius: 8,
              background: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 4,
            }}>
              <img
                src="/logo.jpg"
                alt="Logo"
                style={{
                  height: '100%',
                  borderRadius: 6,
                  objectFit: 'contain',
                }}
              />
            </div>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          theme="dark"
        />

        {/* 折叠按钮 - 科技风格 */}
        <div
          className="sidebar-collapse-trigger"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </div>
      </Sider>

      <Layout>
        {/* 顶部状态栏 - 科技渐变 */}
        <Header className="app-header">
          <div className="header-title">
            {collapsed && (
              <div style={{
                width: 44,
                height: 44,
                borderRadius: 10,
                background: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 4,
                marginRight: 12,
              }}>
                <img
                  src="/logo.jpg"
                  alt="Logo"
                  style={{
                    width: '100%',
                    height: '100%',
                    borderRadius: 6,
                    objectFit: 'cover',
                  }}
                />
              </div>
            )}
            <div style={{
              height: 36,
              borderRadius: 6,
              background: '#fff',
              display: 'flex',
              alignItems: 'center',
              padding: '0 10px',
              marginRight: 10,
            }}>
              <img
                src="/logo.jpg"
                alt="Logo"
                style={{
                  height: 28,
                  borderRadius: 4,
                  objectFit: 'contain',
                }}
              />
            </div>
            <img
              src="/knigHts_logo_small.png"
              alt="KnigHts"
              style={{
                height: 18,
                display: 'inline-block',
                verticalAlign: 'middle',
                filter: 'brightness(0) invert(1)',
              }}
            />
          </div>

          <div className="header-actions">
            {/* 同步状态 */}
            <div className="sync-status">
              <span className="sync-dot" />
              <span>数据已同步</span>
            </div>

            {/* 同步按钮 */}
            <Tooltip title="同步数据">
              <button className="header-btn" onClick={syncData}>
                <SyncOutlined spin={syncing} />
              </button>
            </Tooltip>

            {/* AI 助手按钮 */}
            <AIChatWindow position="header" />

            {/* 通知 */}
            <Tooltip title="通知中心">
              <Badge count={3} size="small" offset={[-2, 2]}>
                <button className="header-btn">
                  <BellOutlined />
                </button>
              </Badge>
            </Tooltip>

            {/* 用户信息 */}
            <Dropdown
              menu={{
                items: [
                  { key: 'profile', label: '个人中心' },
                  { key: 'settings', label: '系统设置', onClick: () => navigate('/settings') },
                  { type: 'divider' },
                  { key: 'logout', label: '退出登录', danger: true }
                ]
              }}
              placement="bottomRight"
              trigger={['click']}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                cursor: 'pointer',
                padding: '6px 14px',
                borderRadius: 8,
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                transition: 'all 0.25s ease',
                backdropFilter: 'blur(10px)'
              }}>
                <Avatar
                  size={30}
                  icon={<UserOutlined />}
                  style={{
                    background: 'linear-gradient(135deg, #4A86C8 0%, #16325C 100%)',
                    boxShadow: '0 2px 8px rgba(74, 134, 200, 0.3)'
                  }}
                />
                <span style={{
                  color: 'white',
                  fontSize: 13,
                  fontWeight: 500,
                  letterSpacing: 0.3
                }}>管理员</span>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* 内容区域 */}
        <Content className="app-content">
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}