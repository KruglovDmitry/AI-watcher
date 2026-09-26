import { Button, Form, Input, message } from 'antd';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

export default function LoginPage() {
  const { login, username, loading } = useAuth();
  const navigate = useNavigate();

  if (!loading && username) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>AI Watcher</h1>
        <p>Админ-панель контроля смен сотрудников</p>
        <Form
          layout="vertical"
          onFinish={async (values) => {
            try {
              await login(values.username, values.password);
              message.success('Вход выполнен');
              navigate('/');
            } catch (error) {
              message.error(error instanceof Error ? error.message : 'Ошибка входа');
            }
          }}
        >
          <Form.Item name="username" label="Логин" rules={[{ required: true }]}>
            <Input size="large" autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
            <Input.Password size="large" autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" size="large" block>
            Войти
          </Button>
        </Form>
      </div>
    </div>
  );
}
