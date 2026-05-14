import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider, Layout } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import AppLayout from './components/AppLayout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import Materials from './pages/Materials'
import PriceMonitor from './pages/PriceMonitor'
import Adjustment from './pages/Adjustment'
import Indicators from './pages/Indicators'
import Settings from './pages/Settings'

const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
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
              <Route path="/indicators" element={<Indicators />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </AppLayout>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  )
}