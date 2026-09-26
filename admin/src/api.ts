const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export type Employee = {
  id: number;
  alias: string;
  telegram_id: number | null;
  telegram_username: string | null;
  telegram_full_name: string | null;
  invite_code: string;
  is_active: boolean;
  created_at: string;
};

export type Location = {
  id: number;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
  radius_meters: number;
  is_active: boolean;
};

export type Schedule = {
  id: number;
  employee_id: number;
  employee_alias: string;
  location_id: number;
  location_name: string;
  work_date: string;
  start_time: string;
  end_time: string;
  has_shift: boolean;
  shift_status: string | null;
};

export type AlertItem = {
  id: number;
  type: string;
  employee_id: number | null;
  schedule_slot_id: number | null;
  message: string;
  is_read: boolean;
  created_at: string;
};

export type DashboardStats = {
  date: string;
  total_scheduled: number;
  on_shift: number;
  completed: number;
  early_leave: number;
  missed_or_late: number;
  not_started: number;
  unread_alerts: number;
  employees: Array<{
    employee_id: number;
    alias: string;
    status: string;
    location_name: string | null;
    scheduled_start: string | null;
    scheduled_end: string | null;
    started_at: string | null;
    distance_m: number | null;
  }>;
};

function getToken(): string | null {
  return localStorage.getItem('watcher_token');
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('watcher_token', token);
  else localStorage.removeItem('watcher_token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    setToken(null);
    if (!window.location.pathname.includes('/login')) {
      window.location.href = '/login';
    }
    throw new Error('Требуется авторизация');
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'Ошибка запроса');
  }
  return data as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<{ access_token: string; username: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ id: number; username: string }>('/auth/me'),
  dashboard: (date?: string) =>
    request<DashboardStats>(`/dashboard${date ? `?work_date=${date}` : ''}`),
  employees: () => request<Employee[]>('/employees'),
  createEmployee: (alias: string) =>
    request<Employee>('/employees', { method: 'POST', body: JSON.stringify({ alias }) }),
  updateEmployee: (id: number, payload: Partial<Pick<Employee, 'alias' | 'is_active'>>) =>
    request<Employee>(`/employees/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  regenerateInvite: (id: number) =>
    request<Employee>(`/employees/${id}/regenerate-invite`, { method: 'POST' }),
  locations: () => request<Location[]>('/locations'),
  createLocation: (payload: Omit<Location, 'id'>) =>
    request<Location>('/locations', { method: 'POST', body: JSON.stringify(payload) }),
  updateLocation: (id: number, payload: Partial<Location>) =>
    request<Location>(`/locations/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteLocation: (id: number) => request<void>(`/locations/${id}`, { method: 'DELETE' }),
  schedules: (workDate?: string) =>
    request<Schedule[]>(`/schedules${workDate ? `?work_date=${workDate}` : ''}`),
  createSchedule: (payload: {
    employee_id: number;
    location_id: number;
    work_date: string;
    start_time: string;
    end_time: string;
  }) => request<Schedule>('/schedules', { method: 'POST', body: JSON.stringify(payload) }),
  deleteSchedule: (id: number) => request<void>(`/schedules/${id}`, { method: 'DELETE' }),
  alerts: (unreadOnly = false) =>
    request<AlertItem[]>(`/alerts?unread_only=${unreadOnly}`),
  markAlertRead: (id: number) => request<AlertItem>(`/alerts/${id}/read`, { method: 'POST' }),
};
