from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models import (
    Alert,
    AlertType,
    Employee,
    ScheduleSlot,
    ShiftSession,
    ShiftStatus,
)
from app.services.geo import is_within_radius


def now_local() -> datetime:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None)


def combine_local(work_date: date, work_time: time) -> datetime:
    return datetime.combine(work_date, work_time)


def get_employee_by_telegram(db: Session, telegram_id: int) -> Employee | None:
    return db.query(Employee).filter(Employee.telegram_id == telegram_id, Employee.is_active.is_(True)).first()


def get_today_slot(db: Session, employee_id: int, at: datetime | None = None) -> ScheduleSlot | None:
    moment = at or now_local()
    return (
        db.query(ScheduleSlot)
        .filter(ScheduleSlot.employee_id == employee_id, ScheduleSlot.work_date == moment.date())
        .order_by(ScheduleSlot.start_time.asc())
        .first()
    )


def get_active_shift(db: Session, employee_id: int) -> ShiftSession | None:
    return (
        db.query(ShiftSession)
        .filter(ShiftSession.employee_id == employee_id, ShiftSession.status == ShiftStatus.ACTIVE)
        .order_by(ShiftSession.started_at.desc())
        .first()
    )


def start_shift(
    db: Session,
    employee: Employee,
    latitude: float,
    longitude: float,
) -> tuple[ShiftSession | None, str]:
    moment = now_local()
    slot = get_today_slot(db, employee.id, moment)
    if slot is None:
        return None, "На сегодня нет смены в графике."

    existing = db.query(ShiftSession).filter(ShiftSession.schedule_slot_id == slot.id).first()
    if existing is not None:
        if existing.status == ShiftStatus.ACTIVE:
            return None, "Смена уже начата."
        return None, "Смена по этому слоту уже закрыта."

    location = slot.location
    ok, distance = is_within_radius(
        latitude,
        longitude,
        location.latitude,
        location.longitude,
        location.radius_meters,
    )
    if not ok:
        alert = Alert(
            type=AlertType.GEO_FAIL,
            employee_id=employee.id,
            schedule_slot_id=slot.id,
            message=(
                f"{employee.alias}: попытка check-in вне точки «{location.name}» "
                f"({distance:.0f} м, лимит {location.radius_meters} м)."
            ),
        )
        db.add(alert)
        db.commit()
        return None, (
            f"Вы слишком далеко от точки «{location.name}». "
            f"Расстояние ≈ {distance:.0f} м (нужно ≤ {location.radius_meters} м)."
        )

    scheduled_start = combine_local(slot.work_date, slot.start_time)
    scheduled_end = combine_local(slot.work_date, slot.end_time)
    if moment > scheduled_end:
        return None, "Время смены по графику уже закончилось."

    late_minutes = max(0, int((moment - scheduled_start).total_seconds() // 60))
    if late_minutes > 0:
        db.add(
            Alert(
                type=AlertType.LATE,
                employee_id=employee.id,
                schedule_slot_id=slot.id,
                message=f"{employee.alias}: опоздание на {late_minutes} мин.",
            )
        )

    shift = ShiftSession(
        employee_id=employee.id,
        schedule_slot_id=slot.id,
        status=ShiftStatus.ACTIVE,
        started_at=moment,
        scheduled_end_at=scheduled_end,
        check_in_lat=latitude,
        check_in_lon=longitude,
        check_in_distance_m=distance,
    )
    db.add(shift)
    db.commit()
    db.refresh(shift)

    remaining = scheduled_end - moment
    hours, rem = divmod(int(remaining.total_seconds()), 3600)
    minutes = rem // 60
    return (
        shift,
        (
            f"Смена начата на точке «{location.name}».\n"
            f"До конца по графику: {hours:02d}:{minutes:02d} "
            f"(до {slot.end_time.strftime('%H:%M')})."
        ),
    )


def finish_shift_early(db: Session, employee: Employee) -> tuple[ShiftSession | None, str]:
    shift = get_active_shift(db, employee.id)
    if shift is None:
        return None, "Активной смены нет."

    moment = now_local()
    shift.ended_at = moment
    shift.status = ShiftStatus.EARLY_LEAVE
    db.add(
        Alert(
            type=AlertType.EARLY_LEAVE,
            employee_id=employee.id,
            schedule_slot_id=shift.schedule_slot_id,
            message=f"{employee.alias}: ранний уход в {moment.strftime('%H:%M')}.",
        )
    )
    db.commit()
    db.refresh(shift)
    return shift, f"Смена завершена досрочно в {moment.strftime('%H:%M')}."


def auto_close_expired_shifts(db: Session) -> list[ShiftSession]:
    moment = now_local()
    shifts = (
        db.query(ShiftSession)
        .filter(ShiftSession.status == ShiftStatus.ACTIVE, ShiftSession.scheduled_end_at <= moment)
        .all()
    )
    for shift in shifts:
        shift.status = ShiftStatus.COMPLETED
        shift.ended_at = shift.scheduled_end_at
    if shifts:
        db.commit()
    return shifts


def slots_needing_reminder(db: Session) -> list[ScheduleSlot]:
    settings = get_settings()
    moment = now_local()
    window_end = moment + timedelta(minutes=settings.reminder_minutes_before)
    slots = (
        db.query(ScheduleSlot)
        .filter(
            ScheduleSlot.work_date == moment.date(),
            ScheduleSlot.reminder_sent.is_(False),
        )
        .all()
    )
    result: list[ScheduleSlot] = []
    for slot in slots:
        start_at = combine_local(slot.work_date, slot.start_time)
        if moment <= start_at <= window_end:
            result.append(slot)
    return result


def slots_missing_checkin_for_morning(db: Session) -> list[ScheduleSlot]:
    """Слоты, которые уже должны были начаться, но check-in не сделан."""
    moment = now_local()
    slots = (
        db.query(ScheduleSlot)
        .filter(
            ScheduleSlot.work_date == moment.date(),
            ScheduleSlot.morning_checked.is_(False),
        )
        .all()
    )
    missing: list[ScheduleSlot] = []
    touched = False
    for slot in slots:
        start_at = combine_local(slot.work_date, slot.start_time)
        if start_at > moment:
            continue
        if slot.shift is not None:
            slot.morning_checked = True
            touched = True
            continue
        missing.append(slot)
    if touched:
        db.commit()
    return missing


def mark_reminder_sent(db: Session, slot: ScheduleSlot) -> None:
    slot.reminder_sent = True
    db.commit()


def mark_morning_checked(db: Session, slot: ScheduleSlot, create_alert: bool = True) -> None:
    slot.morning_checked = True
    if create_alert and slot.shift is None:
        db.add(
            Alert(
                type=AlertType.NO_CHECKIN,
                employee_id=slot.employee_id,
                schedule_slot_id=slot.id,
                message=(
                    f"{slot.employee.alias}: нет check-in на смену "
                    f"{slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')} "
                    f"({slot.location.name})."
                ),
            )
        )
    db.commit()


def format_shift_timer(shift: ShiftSession) -> str:
    moment = now_local()
    remaining = shift.scheduled_end_at - moment
    if remaining.total_seconds() <= 0:
        return "00:00"
    hours, rem = divmod(int(remaining.total_seconds()), 3600)
    minutes = rem // 60
    seconds = rem % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
