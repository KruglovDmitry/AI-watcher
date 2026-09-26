from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application

from app.config import get_settings
from app.database.engine import SessionLocal
from app.services.shift import (
    auto_close_expired_shifts,
    mark_morning_checked,
    mark_reminder_sent,
    slots_missing_checkin_for_morning,
    slots_needing_reminder,
)

logger = logging.getLogger(__name__)


class WatcherScheduler:
    def __init__(self, bot_app: Application | None) -> None:
        self.bot_app = bot_app
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(self.settings.timezone))

    async def _send(self, chat_id: int | str, text: str) -> None:
        if self.bot_app is None:
            return
        try:
            await self.bot_app.bot.send_message(chat_id=chat_id, text=text)
        except Exception:
            logger.exception("Failed to send telegram message to %s", chat_id)

    async def job_reminders(self) -> None:
        db = SessionLocal()
        try:
            slots = slots_needing_reminder(db)
            for slot in slots:
                employee = slot.employee
                if employee.telegram_id:
                    await self._send(
                        employee.telegram_id,
                        (
                            f"Напоминание: через {self.settings.reminder_minutes_before} мин "
                            f"смена на «{slot.location.name}» "
                            f"({slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}).\n"
                            "Когда будете на месте — нажмите «Я на смене»."
                        ),
                    )
                mark_reminder_sent(db, slot)
        finally:
            db.close()

    async def job_auto_close(self) -> None:
        db = SessionLocal()
        try:
            closed = auto_close_expired_shifts(db)
            for shift in closed:
                employee = shift.employee
                if employee.telegram_id:
                    await self._send(
                        employee.telegram_id,
                        "Рабочее время по графику закончилось. Смена закрыта автоматически.",
                    )
        finally:
            db.close()

    async def job_morning_check(self) -> None:
        db = SessionLocal()
        try:
            missing = slots_missing_checkin_for_morning(db)
            for slot in missing:
                mark_morning_checked(db, slot, create_alert=True)
                employee = slot.employee
                text = (
                    f"⚠ Нет check-in: {employee.alias} "
                    f"({slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}, "
                    f"{slot.location.name})"
                )
                if employee.telegram_id:
                    await self._send(
                        employee.telegram_id,
                        "Вы ещё не отметились на смене. Нажмите «Я на смене» на точке.",
                    )
                if self.settings.admin_telegram_chat_id:
                    await self._send(self.settings.admin_telegram_chat_id, text)
        finally:
            db.close()

    def start(self) -> None:
        self.scheduler.add_job(self.job_reminders, IntervalTrigger(minutes=1), id="reminders", replace_existing=True)
        self.scheduler.add_job(self.job_auto_close, IntervalTrigger(minutes=1), id="auto_close", replace_existing=True)
        self.scheduler.add_job(
            self.job_morning_check,
            CronTrigger(
                hour=self.settings.morning_check_hour,
                minute=self.settings.morning_check_minute,
            ),
            id="morning_check",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info(
            "Scheduler started (reminders/auto-close every 1m, morning check %02d:%02d)",
            self.settings.morning_check_hour,
            self.settings.morning_check_minute,
        )

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
