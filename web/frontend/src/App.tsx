import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Layout } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/AppLayout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import Materials from './pages/Materials'
import PriceMonitor from './pages/PriceMonitor'
import Adjustment from './pages/Adjustment'
import AdjustmentRuleConfig from './pages/AdjustmentRuleConfig'
import Indicators from './pages/Indicators'
import Settings from './pages/Settings'
import CostReference from './pages/CostReference'

const theme = {
  token: {
    colorPrimary: '#16325C',
    colorSuccess: '#10B981',
    colorWarning: '#F59E0B',
    colorError: '#EF4444',
    colorInfo: '#4A86C8',
    borderRadius: 6,
    fontFamily: "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
  components: {
    Button: {
      primaryShadow: '0 2px 6px rgba(22, 50, 92, 0.15)',
    },
    Card: {
      headerBg: 'linear-gradient(135deg, #FAFBFC 0%, #F5F7FA 100%)',
    },
    Table: {
      headerBg: '#EEF2F7',
      headerColor: '#16325C',
      rowHoverBg: 'rgba(74, 134, 200, 0.08)',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(74, 134, 200, 0.3)',
      darkItemHoverBg: 'rgba(74, 134, 200, 0.2)',
    },
  },
}

export default function App() {
  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <AppLayout>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/materials" element={<Materials />} />
              <Route path="/prices" element={<PriceMonitor />} />
              <Route path="/adjustments" element={<Adjustment />} />
              <Route path="/adjustments/rules" element={<AdjustmentRuleConfig />} />
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/cost-reference" element={<CostReference />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </AppLayout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  )
}