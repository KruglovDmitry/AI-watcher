import { useEffect, useState } from 'react';
import { Button, Form, Input, InputNumber, Modal, Space, Switch, Table, message } from 'antd';
import { api, type Location } from '../api';
import MapPicker from '../components/MapPicker';

export default function LocationsPage() {
  const [items, setItems] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Location | null>(null);
  const [form] = Form.useForm();
  const latitude = Form.useWatch('latitude', form);
  const longitude = Form.useWatch('longitude', form);
  const radiusMeters = Form.useWatch('radius_meters', form);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await api.locations());
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ radius_meters: 500, is_active: true });
    setOpen(true);
  };

  const openEdit = (location: Location) => {
    setEditing(location);
    form.setFieldsValue(location);
    setOpen(true);
  };

  return (
    <div className="page-card">
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Точки</h2>
        <Button type="primary" onClick={openCreate}>
          Добавить точку
        </Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={items}
        columns={[
          { title: 'Название', dataIndex: 'name' },
          { title: 'Адрес', dataIndex: 'address', render: (v) => v || '—' },
          {
            title: 'Координаты',
            render: (_, row) => `${row.latitude.toFixed(5)}, ${row.longitude.toFixed(5)}`,
          },
          { title: 'Радиус, м', dataIndex: 'radius_meters' },
          {
            title: 'Активна',
            dataIndex: 'is_active',
            render: (v: boolean, row) => (
              <Switch
                checked={v}
                onChange={async (checked) => {
                  await api.updateLocation(row.id, { is_active: checked });
                  await load();
                }}
              />
            ),
          },
          {
            title: '',
            render: (_, row) => (
              <Space>
                <Button size="small" onClick={() => openEdit(row)}>
                  Изменить
                </Button>
                <Button
                  danger
                  size="small"
                  onClick={async () => {
                    await api.deleteLocation(row.id);
                    await load();
                  }}
                >
                  Удалить
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Modal
        title={editing ? 'Редактировать точку' : 'Новая точка'}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText={editing ? 'Сохранить' : 'Создать'}
        width={720}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ radius_meters: 500, is_active: true }}
          onFinish={async (values) => {
            if (editing) {
              await api.updateLocation(editing.id, values);
              message.success('Точка обновлена');
            } else {
              await api.createLocation(values);
              message.success('Точка создана');
            }
            setOpen(false);
            form.resetFields();
            setEditing(null);
            await load();
          }}
        >
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="address" label="Адрес">
            <Input placeholder="Можно заполнить поиском на карте" />
          </Form.Item>

          <Form.Item label="Карта" required>
            <MapPicker
              latitude={latitude}
              longitude={longitude}
              radiusMeters={radiusMeters}
              onChange={({ latitude: lat, longitude: lng, address }) => {
                form.setFieldsValue({
                  latitude: Number(lat.toFixed(6)),
                  longitude: Number(lng.toFixed(6)),
                  ...(address ? { address } : {}),
                });
              }}
            />
          </Form.Item>

          <Space style={{ width: '100%' }} size="middle">
            <Form.Item
              name="latitude"
              label="Широта"
              rules={[{ required: true, message: 'Укажите точку на карте' }]}
              style={{ flex: 1, marginBottom: 12 }}
            >
              <InputNumber style={{ width: '100%' }} step={0.000001} />
            </Form.Item>
            <Form.Item
              name="longitude"
              label="Долгота"
              rules={[{ required: true, message: 'Укажите точку на карте' }]}
              style={{ flex: 1, marginBottom: 12 }}
            >
              <InputNumber style={{ width: '100%' }} step={0.000001} />
            </Form.Item>
            <Form.Item
              name="radius_meters"
              label="Радиус (м)"
              rules={[{ required: true }]}
              style={{ width: 140, marginBottom: 12 }}
            >
              <InputNumber style={{ width: '100%' }} min={50} max={5000} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
