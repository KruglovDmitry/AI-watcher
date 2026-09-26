import { useEffect, useState } from 'react';
import { Button, Space, Table, Tag, message } from 'antd';
import { api, type AlertItem } from '../api';

export default function AlertsPage() {
  const [items, setItems] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await api.alerts());
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return (
    <div className="page-card">
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Алерты</h2>
        <Button onClick={() => void load()}>Обновить</Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={items}
        columns={[
          {
            title: 'Тип',
            dataIndex: 'type',
            render: (type: string) => <Tag>{type}</Tag>,
          },
          { title: 'Сообщение', dataIndex: 'message' },
          {
            title: 'Время',
            dataIndex: 'created_at',
            render: (v: string) => new Date(v).toLocaleString('ru-RU'),
          },
          {
            title: 'Статус',
            dataIndex: 'is_read',
            render: (v: boolean, row) =>
              v ? (
                <Tag color="default">прочитано</Tag>
              ) : (
                <Button
                  size="small"
                  type="link"
                  onClick={async () => {
                    await api.markAlertRead(row.id);
                    await load();
                  }}
                >
                  отметить
                </Button>
              ),
          },
        ]}
      />
    </div>
  );
}
