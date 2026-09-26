import { createRoot } from 'react-dom/client';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <ConfigProvider
    locale={ruRU}
    theme={{
      token: {
        colorPrimary: '#1f6f5b',
        borderRadius: 8,
        fontFamily: '"Manrope", "Segoe UI", sans-serif',
      },
    }}
  >
    <App />
  </ConfigProvider>,
);
