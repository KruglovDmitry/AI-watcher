import { useEffect, useState } from 'react';
import { Button, DatePicker, Form, Modal, Select, Space, Table, TimePicker, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type Employee, type Location, type Schedule } from '../api';

export default function SchedulePage() {
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [items, setItems] = useState<Schedule[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();

  const load = async (value: Dayjs) => {
    setLoading(true);
    try {
      const [schedules, emps, locs] = await Promise.all([
        api.schedules(value.format('YYYY-MM-DD')),
        api.employees(),
        api.locations(),
      ]);
      setItems(schedules);
      setEmployees(emps.filter((e) => e.is_active));
      setLocations(locs.filter((l) => l.is_active));
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(date);
  }, [date]);

  return (
    <div className="page-card">
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }} wrap>
        <Space>
          <h2 style={{ margin: 0 }}>График</h2>
          <DatePicker value={date} onChange={(v) => v && setDate(v)} allowClear={false} />
        </Space>
        <Button type="primary" onClick={() => setOpen(true)}>
          Добавить смену
        </Button>
      </Space>

      <Table
        loading={loading}
        rowKey="id"
        dataSource={items}
        columns={[
          { title: 'Сотрудник', dataIndex: 'employee_alias' },
          { title: 'Точка', dataIndex: 'location_name' },
          {
            title: 'Время',
            render: (_, row) =>
              `${String(row.start_time).slice(0, 5)}–${String(row.end_time).slice(0, 5)}`,
          },
          {
            title: 'Смена',
            render: (_, row) => (row.has_shift ? row.shift_status || 'есть' : 'нет check-in'),
          },
          {
            title: '',
            render: (_, row) => (
              <Button
                danger
                size="small"
                onClick={async () => {
                  await api.deleteSchedule(row.id);
                  await load(date);
                }}
              >
                Удалить
              </Button>
            ),
          },
        ]}
      />

      <Modal
        title="Новая смена"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText="Создать"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            work_date: date,
            time_range: [dayjs('10:00', 'HH:mm'), dayjs('18:00', 'HH:mm')],
          }}
          onFinish={async (values) => {
            await api.createSchedule({
              employee_id: values.employee_id,
              location_id: values.location_id,
              work_date: values.work_date.format('YYYY-MM-DD'),
              start_time: values.time_range[0].format('HH:mm:ss'),
              end_time: values.time_range[1].format('HH:mm:ss'),
            });
            message.success('Смена добавлена');
            setOpen(false);
            form.resetFields();
            await load(date);
          }}
        >
          <Form.Item name="employee_id" label="Сотрудник" rules={[{ required: true }]}>
            <Select
              options={employees.map((e) => ({ value: e.id, label: e.alias }))}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="location_id" label="Точка" rules={[{ required: true }]}>
            <Select
              options={locations.map((l) => ({ value: l.id, label: l.name }))}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="work_date" label="Дата" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="time_range" label="Время смены" rules={[{ required: true }]}>
            <TimePicker.RangePicker format="HH:mm" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
