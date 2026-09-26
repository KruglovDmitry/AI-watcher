from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from app.api.auth import create_access_token, get_current_admin, verify_password
from app.api.schemas import (
    AlertOut,
    DashboardEmployeeStat,
    DashboardStats,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    LoginRequest,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
    TokenResponse,
)
from app.database.engine import get_db
from app.database.models import AdminUser, Alert, Employee, Location, ScheduleSlot, ShiftStatus
from app.services.shift import combine_local, now_local

router = APIRouter(prefix="/api")


def schedule_to_out(slot: ScheduleSlot) -> ScheduleOut:
    shift_status = slot.shift.status.value if slot.shift else None
    return ScheduleOut(
        id=slot.id,
        employee_id=slot.employee_id,
        employee_alias=slot.employee.alias,
        location_id=slot.location_id,
        location_name=slot.location.name,
        work_date=slot.work_date,
        start_time=slot.start_time,
        end_time=slot.end_time,
        has_shift=slot.shift is not None,
        shift_status=shift_status,
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь отключён")
    return TokenResponse(access_token=create_access_token(user), username=user.username)


@router.get("/auth/me")
def me(admin: AdminUser = Depends(get_current_admin)) -> dict:
    return {"id": admin.id, "username": admin.username}


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[Employee]:
    return db.query(Employee).order_by(Employee.alias.asc()).all()


@router.post("/employees", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Employee:
    employee = Employee(alias=payload.alias.strip())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    data = payload.model_dump(exclude_unset=True)
    if "alias" in data and data["alias"] is not None:
        data["alias"] = data["alias"].strip()
    for key, value in data.items():
        setattr(employee, key, value)
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/employees/{employee_id}/regenerate-invite", response_model=EmployeeOut)
def regenerate_invite(
    employee_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Employee:
    import secrets

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    employee.invite_code = secrets.token_hex(4).upper()
    employee.telegram_id = None
    employee.telegram_username = None
    employee.telegram_full_name = None
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/locations", response_model=list[LocationOut])
def list_locations(
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[Location]:
    return db.query(Location).order_by(Location.name.asc()).all()


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Location:
    location = Location(**payload.model_dump())
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.patch("/locations/{location_id}", response_model=LocationOut)
def update_location(
    location_id: int,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Location:
    location = db.query(Location).filter(Location.id == location_id).first()
    if location is None:
        raise HTTPException(status_code=404, detail="Точка не найдена")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return location


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Response:
    location = db.query(Location).filter(Location.id == location_id).first()
    if location is None:
        raise HTTPException(status_code=404, detail="Точка не найдена")
    db.delete(location)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/schedules", response_model=list[ScheduleOut])
def list_schedules(
    work_date: date | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[ScheduleOut]:
    query = db.query(ScheduleSlot).options(
        joinedload(ScheduleSlot.employee),
        joinedload(ScheduleSlot.location),
        joinedload(ScheduleSlot.shift),
    )
    if work_date is not None:
        query = query.filter(ScheduleSlot.work_date == work_date)
    if employee_id is not None:
        query = query.filter(ScheduleSlot.employee_id == employee_id)
    slots = query.order_by(ScheduleSlot.work_date.asc(), ScheduleSlot.start_time.asc()).all()
    return [schedule_to_out(slot) for slot in slots]


@router.post("/schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> ScheduleOut:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="Время окончания должно быть позже начала")
    employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
    location = db.query(Location).filter(Location.id == payload.location_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if location is None:
        raise HTTPException(status_code=404, detail="Точка не найдена")

    slot = ScheduleSlot(**payload.model_dump())
    db.add(slot)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Слот на это время уже существует") from exc
    db.refresh(slot)
    slot = (
        db.query(ScheduleSlot)
        .options(joinedload(ScheduleSlot.employee), joinedload(ScheduleSlot.location), joinedload(ScheduleSlot.shift))
        .filter(ScheduleSlot.id == slot.id)
        .one()
    )
    return schedule_to_out(slot)


@router.patch("/schedules/{slot_id}", response_model=ScheduleOut)
def update_schedule(
    slot_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> ScheduleOut:
    slot = (
        db.query(ScheduleSlot)
        .options(joinedload(ScheduleSlot.employee), joinedload(ScheduleSlot.location), joinedload(ScheduleSlot.shift))
        .filter(ScheduleSlot.id == slot_id)
        .first()
    )
    if slot is None:
        raise HTTPException(status_code=404, detail="Слот не найден")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(slot, key, value)
    if slot.end_time <= slot.start_time:
        raise HTTPException(status_code=400, detail="Время окончания должно быть позже начала")
    db.commit()
    db.refresh(slot)
    return schedule_to_out(slot)


@router.delete("/schedules/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    slot_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> Response:
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == slot_id).first()
    if slot is None:
        raise HTTPException(status_code=404, detail="Слот не найден")
    db.delete(slot)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    unread_only: bool = False,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> list[AlertOut]:
    query = db.query(Alert).order_by(Alert.created_at.desc())
    if unread_only:
        query = query.filter(Alert.is_read.is_(False))
    alerts = query.limit(limit).all()
    return [
        AlertOut(
            id=a.id,
            type=a.type.value,
            employee_id=a.employee_id,
            schedule_slot_id=a.schedule_slot_id,
            message=a.message,
            is_read=a.is_read,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/read", response_model=AlertOut)
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> AlertOut:
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert is None:
        raise HTTPException(status_code=404, detail="Алерт не найден")
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return AlertOut(
        id=alert.id,
        type=alert.type.value,
        employee_id=alert.employee_id,
        schedule_slot_id=alert.schedule_slot_id,
        message=alert.message,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    work_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _: AdminUser = Depends(get_current_admin),
) -> DashboardStats:
    target = work_date or now_local().date()
    slots = (
        db.query(ScheduleSlot)
        .options(joinedload(ScheduleSlot.employee), joinedload(ScheduleSlot.location), joinedload(ScheduleSlot.shift))
        .filter(ScheduleSlot.work_date == target)
        .order_by(ScheduleSlot.start_time.asc())
        .all()
    )

    on_shift = completed = early_leave = missed_or_late = not_started = 0
    employees: list[DashboardEmployeeStat] = []
    moment = now_local()

    for slot in slots:
        shift = slot.shift
        status_label = "not_started"
        started_at = None
        distance = None

        if shift is None:
            start_at = combine_local(slot.work_date, slot.start_time)
            if moment > start_at:
                status_label = "late"
                missed_or_late += 1
            else:
                not_started += 1
        else:
            started_at = shift.started_at.isoformat(sep=" ", timespec="minutes")
            distance = shift.check_in_distance_m
            if shift.status == ShiftStatus.ACTIVE:
                status_label = "on_shift"
                on_shift += 1
            elif shift.status == ShiftStatus.COMPLETED:
                status_label = "completed"
                completed += 1
            elif shift.status == ShiftStatus.EARLY_LEAVE:
                status_label = "early_leave"
                early_leave += 1
            elif shift.status == ShiftStatus.MISSED:
                status_label = "missed"
                missed_or_late += 1

        employees.append(
            DashboardEmployeeStat(
                employee_id=slot.employee_id,
                alias=slot.employee.alias,
                status=status_label,
                location_name=slot.location.name,
                scheduled_start=slot.start_time.strftime("%H:%M"),
                scheduled_end=slot.end_time.strftime("%H:%M"),
                started_at=started_at,
                distance_m=distance,
            )
        )

    unread = db.query(Alert).filter(Alert.is_read.is_(False)).count()
    return DashboardStats(
        date=target,
        total_scheduled=len(slots),
        on_shift=on_shift,
        completed=completed,
        early_leave=early_leave,
        missed_or_late=missed_or_late,
        not_started=not_started,
        unread_alerts=unread,
        employees=employees,
    )

