from __future__ import annotations

import enum
import secrets
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ShiftStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EARLY_LEAVE = "early_leave"
    MISSED = "missed"


class AlertType(str, enum.Enum):
    NO_CHECKIN = "no_checkin"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    GEO_FAIL = "geo_fail"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(150), nullable=False, comment="Отображаемое имя для админа")
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invite_code: Mapped[str] = mapped_column(
        String(16),
        unique=True,
        nullable=False,
        default=lambda: secrets.token_hex(4).upper(),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    schedules: Mapped[list[ScheduleSlot]] = relationship(back_populates="employee")
    shifts: Mapped[list[ShiftSession]] = relationship(back_populates="employee")


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_meters: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    schedules: Mapped[list[ScheduleSlot]] = relationship(back_populates="location")


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        UniqueConstraint("employee_id", "work_date", "start_time", name="uq_employee_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    morning_checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="schedules")
    location: Mapped[Location] = relationship(back_populates="schedules")
    shift: Mapped[ShiftSession | None] = relationship(back_populates="schedule_slot", uselist=False)


class ShiftSession(Base):
    __tablename__ = "shift_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), nullable=False)
    schedule_slot_id: Mapped[int] = mapped_column(ForeignKey("schedule_slots.id"), unique=True, nullable=False)
    status: Mapped[ShiftStatus] = mapped_column(Enum(ShiftStatus), default=ShiftStatus.ACTIVE, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    check_in_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_in_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    employee: Mapped[Employee] = relationship(back_populates="shifts")
    schedule_slot: Mapped[ScheduleSlot] = relationship(back_populates="shift")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    schedule_slot_id: Mapped[int | None] = mapped_column(ForeignKey("schedule_slots.id"), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
