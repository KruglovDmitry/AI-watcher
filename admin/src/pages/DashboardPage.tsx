import { useEffect, useState } from 'react';
import { DatePicker, Space, Table, Tag, message } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { api, type DashboardStats } from '../api';

const statusMap: Record<string, { color: string; label: string }> = {
  on_shift: { color: 'green', label: 'На смене' },
  completed: { color: 'blue', label: 'Завершил' },
  early_leave: { color: 'orange', label: 'Ранний уход' },
  late: { color: 'red', label: 'Опоздание / нет check-in' },
  missed: { color: 'red', label: 'Пропуск' },
  not_started: { color: 'default', label: 'Ещё не начал' },
};

export default function DashboardPage() {
  const [date, setDate] = useState<Dayjs>(dayjs());
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async (value: Dayjs) => {
    setLoading(true);
    try {
      setStats(await api.dashboard(value.format('YYYY-MM-DD')));
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'Ошибка загрузки');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load(date);
  }, [date]);

  return (
    <div className="page-card">
      <Space style={{ marginBottom: 16 }} wrap>
        <h2 style={{ margin: 0 }}>Дашборд</h2>
        <DatePicker value={date} onChange={(v) => v && setDate(v)} allowClear={false} />
      </Space>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="label">В графике</div>
          <div className="value">{stats?.total_scheduled ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">На смене</div>
          <div className="value">{stats?.on_shift ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Завершили</div>
          <div className="value">{stats?.completed ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Ранний уход</div>
          <div className="value">{stats?.early_leave ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Проблемы</div>
          <div className="value">{stats?.missed_or_late ?? '—'}</div>
        </div>
        <div className="stat-tile">
          <div className="label">Непрочитанные алерты</div>
          <div className="value">{stats?.unread_alerts ?? '—'}</div>
        </div>
      </div>

      <Table
        loading={loading}
        rowKey={(row) => `${row.employee_id}-${row.scheduled_start}`}
        dataSource={stats?.employees || []}
        pagination={false}
        columns={[
          { title: 'Сотрудник', dataIndex: 'alias' },
          { title: 'Точка', dataIndex: 'location_name' },
          {
            title: 'График',
            render: (_, row) => `${row.scheduled_start}–${row.scheduled_end}`,
          },
          {
            title: 'Статус',
            dataIndex: 'status',
            render: (status: string) => {
              const meta = statusMap[status] || { color: 'default', label: status };
              return <Tag color={meta.color}>{meta.label}</Tag>;
            },
          },
          { title: 'Check-in', dataIndex: 'started_at', render: (v) => v || '—' },
          {
            title: 'Дистанция',
            dataIndex: 'distance_m',
            render: (v: number | null) => (v == null ? '—' : `${Math.round(v)} м`),
          },
        ]}
      />
    </div>
  );
}
