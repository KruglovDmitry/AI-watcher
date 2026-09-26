import { useEffect, useState } from 'react';
import { Button, Form, Input, Modal, Space, Switch, Table, Tag, Typography, message } from 'antd';
import { api, type Employee } from '../api';

export default function EmployeesPage() {
  const [items, setItems] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async () => {
    setLoading(true);
    try {
      setItems(await api.employees());
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
        <h2 style={{ margin: 0 }}>Сотрудники</h2>
        <Button type="primary" onClick={() => setOpen(true)}>
          Добавить
        </Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={items}
        columns={[
          { title: 'Алиас', dataIndex: 'alias' },
          {
            title: 'Telegram',
            render: (_, row) =>
              row.telegram_id ? (
                <span>
                  {row.telegram_full_name || '—'}
                  {row.telegram_username ? ` (@${row.telegram_username})` : ''}
                </span>
              ) : (
                <Tag>не привязан</Tag>
              ),
          },
          {
            title: 'Код /start',
            dataIndex: 'invite_code',
            render: (code: string) => (
              <Typography.Text copyable={{ text: `/start ${code}` }}>
                <code>{code}</code>
              </Typography.Text>
            ),
          },
          {
            title: 'Активен',
            dataIndex: 'is_active',
            render: (value: boolean, row) => (
              <Switch
                checked={value}
                onChange={async (checked) => {
                  await api.updateEmployee(row.id, { is_active: checked });
                  await load();
                }}
              />
            ),
          },
          {
            title: 'Действия',
            render: (_, row) => (
              <Space>
                <Button
                  size="small"
                  onClick={async () => {
                    const alias = window.prompt('Новый алиас', row.alias);
                    if (!alias) return;
                    await api.updateEmployee(row.id, { alias });
                    await load();
                  }}
                >
                  Переименовать
                </Button>
                <Button
                  size="small"
                  danger
                  onClick={async () => {
                    await api.regenerateInvite(row.id);
                    message.success('Код обновлён, Telegram отвязан');
                    await load();
                  }}
                >
                  Новый код
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title="Новый сотрудник"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText="Создать"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            await api.createEmployee(values.alias);
            message.success('Сотрудник создан');
            setOpen(false);
            form.resetFields();
            await load();
          }}
        >
          <Form.Item
            name="alias"
            label="Алиас (как видит админ)"
            rules={[{ required: true, message: 'Укажите имя' }]}
          >
            <Input placeholder="Иван — точка А" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
