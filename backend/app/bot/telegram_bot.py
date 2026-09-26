from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.bot.keyboards import main_keyboard
from app.config import get_settings
from app.database.engine import SessionLocal
from app.database.models import Employee
from app.services.shift import (
    finish_shift_early,
    format_shift_timer,
    get_active_shift,
    get_employee_by_telegram,
    get_today_slot,
    start_shift,
)

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return

    args = context.args or []
    db = SessionLocal()
    try:
        employee = get_employee_by_telegram(db, update.effective_user.id)
        if employee is None and args:
            code = args[0].strip().upper()
            employee = db.query(Employee).filter(Employee.invite_code == code, Employee.is_active.is_(True)).first()
            if employee is None:
                await update.message.reply_text("Код приглашения не найден. Обратитесь к администратору.")
                return
            if employee.telegram_id and employee.telegram_id != update.effective_user.id:
                await update.message.reply_text("Этот код уже привязан к другому Telegram-аккаунту.")
                return
            employee.telegram_id = update.effective_user.id
            employee.telegram_username = update.effective_user.username
            employee.telegram_full_name = update.effective_user.full_name
            db.commit()
            await update.message.reply_text(
                f"Готово! Вы привязаны как «{employee.alias}».\n"
                "Когда будете на точке — нажмите «Я на смене».",
                reply_markup=main_keyboard(),
            )
            return

        if employee is None:
            await update.message.reply_text(
                "Вы ещё не привязаны к системе.\n"
                "Администратор выдаст код — отправьте: /start КОД"
            )
            return

        await update.message.reply_text(
            f"С возвращением, {employee.alias}!",
            reply_markup=main_keyboard(),
        )
    finally:
        db.close()


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None:
        return
    db = SessionLocal()
    try:
        employee = get_employee_by_telegram(db, update.effective_user.id)
        if employee is None:
            await update.message.reply_text("Сначала привяжитесь через /start КОД")
            return
        shift = get_active_shift(db, employee.id)
        if shift:
            await update.message.reply_text(
                f"Смена активна.\nОсталось: {format_shift_timer(shift)}\n"
                f"Конец по графику: {shift.scheduled_end_at.strftime('%H:%M')}",
                reply_markup=main_keyboard(),
            )
            return
        slot = get_today_slot(db, employee.id)
        if slot is None:
            await update.message.reply_text("На сегодня смены нет.", reply_markup=main_keyboard())
            return
        await update.message.reply_text(
            f"Сегодня смена: {slot.start_time.strftime('%H:%M')}–{slot.end_time.strftime('%H:%M')}\n"
            f"Точка: {slot.location.name}",
            reply_markup=main_keyboard(),
        )
    finally:
        db.close()


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None or update.message.location is None:
        return
    location = update.message.location
    db = SessionLocal()
    try:
        employee = get_employee_by_telegram(db, update.effective_user.id)
        if employee is None:
            await update.message.reply_text("Сначала привяжитесь через /start КОД")
            return
        shift, message = start_shift(db, employee, location.latitude, location.longitude)
        await update.message.reply_text(message, reply_markup=main_keyboard())
        if shift is not None:
            logger.info("Shift started: employee=%s shift=%s", employee.id, shift.id)
    finally:
        db.close()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None or not update.message.text:
        return

    text = update.message.text.strip()
    if text == "Статус смены":
        await status_command(update, context)
        return

    if text == "Закончил работу":
        db = SessionLocal()
        try:
            employee = get_employee_by_telegram(db, update.effective_user.id)
            if employee is None:
                await update.message.reply_text("Сначала привяжитесь через /start КОД")
                return
            _, message = finish_shift_early(db, employee)
            await update.message.reply_text(message, reply_markup=main_keyboard())
        finally:
            db.close()
        return

    if text == "Я на смене":
        await update.message.reply_text(
            "Нажмите кнопку «Я на смене» ещё раз — Telegram запросит геолокацию.",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(
        "Используйте кнопки ниже или /status",
        reply_markup=main_keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram error: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Произошла ошибка. Попробуйте ещё раз.")


def build_telegram_app() -> Application | None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен")
        return None

    from telegram.request import HTTPXRequest

    request_kwargs = {
        "connect_timeout": 30.0,
        "read_timeout": 30.0,
        "write_timeout": 30.0,
        "pool_timeout": 30.0,
    }
    if settings.telegram_proxy_url:
        request_kwargs["proxy"] = settings.telegram_proxy_url
        logger.info("Telegram bot uses proxy")

    request = HTTPXRequest(**request_kwargs)
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .request(request)
        .get_updates_request(HTTPXRequest(**request_kwargs))
        .build()
    )
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_error_handler(error_handler)
    return application
