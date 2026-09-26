from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class EmployeeCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=150)


class EmployeeUpdate(BaseModel):
    alias: str | None = Field(default=None, min_length=1, max_length=150)
    is_active: bool | None = None


class EmployeeOut(BaseModel):
    id: int
    alias: str
    telegram_id: int | None
    telegram_username: str | None
    telegram_full_name: str | None
    invite_code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationCreate(BaseModel):
    name: str
    address: str | None = None
    latitude: float
    longitude: float
    radius_meters: int = 500
    is_active: bool = True


class LocationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: int | None = None
    is_active: bool | None = None


class LocationOut(BaseModel):
    id: int
    name: str
    address: str | None
    latitude: float
    longitude: float
    radius_meters: int
    is_active: bool

    model_config = {"from_attributes": True}


class ScheduleCreate(BaseModel):
    employee_id: int
    location_id: int
    work_date: date
    start_time: time
    end_time: time


class ScheduleUpdate(BaseModel):
    location_id: int | None = None
    work_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None


class ScheduleOut(BaseModel):
    id: int
    employee_id: int
    employee_alias: str
    location_id: int
    location_name: str
    work_date: date
    start_time: time
    end_time: time
    has_shift: bool
    shift_status: str | None = None

    model_config = {"from_attributes": True}


class AlertOut(BaseModel):
    id: int
    type: str
    employee_id: int | None
    schedule_slot_id: int | None
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardEmployeeStat(BaseModel):
    employee_id: int
    alias: str
    status: str
    location_name: str | None = None
    scheduled_start: str | None = None
    scheduled_end: str | None = None
    started_at: str | None = None
    distance_m: float | None = None


class DashboardStats(BaseModel):
    date: date
    total_scheduled: int
    on_shift: int
    completed: int
    early_leave: int
    missed_or_late: int
    not_started: int
    unread_alerts: int
    employees: list[DashboardEmployeeStat]
