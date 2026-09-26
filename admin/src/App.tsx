import { BrowserRouter, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Spin } from 'antd';
import {
  AlertOutlined,
  CalendarOutlined,
  DashboardOutlined,
  EnvironmentOutlined,
  LogoutOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { AuthProvider, useAuth } from './auth';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import EmployeesPage from './pages/EmployeesPage';
import LocationsPage from './pages/LocationsPage';
import SchedulePage from './pages/SchedulePage';
import AlertsPage from './pages/AlertsPage';

const { Header, Sider, Content } = Layout;

function Protected({ children }: { children: React.ReactNode }) {
  const { username, loading } = useAuth();
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }
  if (!username) return <Navigate to="/login" replace />;
  return children;
}

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { username, logout } = useAuth();

  const selected = location.pathname === '/' ? '/' : `/${location.pathname.split('/')[1]}`;

  return (
    <Layout className="app-shell">
      <Sider breakpoint="lg" collapsedWidth={72} className="app-sider" width={240}>
        <div className="brand">
          AI Watcher
          <small>контроль смен</small>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selected]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/', icon: <DashboardOutlined />, label: 'Дашборд' },
            { key: '/employees', icon: <TeamOutlined />, label: 'Сотрудники' },
            { key: '/locations', icon: <EnvironmentOutlined />, label: 'Точки' },
            { key: '/schedule', icon: <CalendarOutlined />, label: 'График' },
            { key: '/alerts', icon: <AlertOutlined />, label: 'Алерты' },
          ]}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: 'transparent',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            gap: 16,
            paddingInline: 24,
          }}
        >
          <span style={{ color: '#5d6b66' }}>{username}</span>
          <a
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            <LogoutOutlined /> Выйти
          </a>
        </Header>
        <Content className="app-content">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/employees" element={<EmployeesPage />} />
            <Route path="/locations" element={<LocationsPage />} />
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              <Protected>
                <Shell />
              </Protected>
            }
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
