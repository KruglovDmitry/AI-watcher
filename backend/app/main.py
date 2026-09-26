from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import ensure_default_admin
from app.api.routes import router
from app.bot.telegram_bot import build_telegram_app
from app.config import get_settings
from app.database.engine import SessionLocal, engine
from app.database.models import Base
from app.jobs.scheduler import WatcherScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("watcher")


async def start_bot_with_retries(bot_app, state: dict, max_attempts: int = 12) -> None:
    """Фоновый запуск Telegram: не блокирует API."""
    delay = 3.0
    for attempt in range(1, max_attempts + 1):
        try:
            await bot_app.initialize()
            await bot_app.start()
            poll_task = asyncio.create_task(bot_app.updater.start_polling(drop_pending_updates=True))
            state["poll_task"] = poll_task
            state["bot_ready"] = True
            logger.info("Telegram bot polling started (attempt %s)", attempt)
            return
        except Exception:
            logger.exception(
                "Не удалось запустить Telegram-бота (попытка %s/%s). Повтор через %.0f сек",
                attempt,
                max_attempts,
                delay,
            )
            try:
                if getattr(bot_app, "running", False):
                    await bot_app.stop()
                if getattr(bot_app, "initialized", False):
                    await bot_app.shutdown()
            except Exception:
                logger.exception("Ошибка при откате инициализации бота")
            if attempt == max_attempts:
                state["bot_ready"] = False
                logger.error("Telegram-бот не запущен. API и админка работают без бота.")
                return
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 45.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()

    bot_app = build_telegram_app()
    scheduler = WatcherScheduler(bot_app)
    bot_state: dict = {"poll_task": None, "bot_ready": False}
    bot_task = None

    if bot_app is not None:
        bot_task = asyncio.create_task(start_bot_with_retries(bot_app, bot_state))

    scheduler.start()
    app.state.bot_app = bot_app
    app.state.scheduler = scheduler
    app.state.bot_state = bot_state
    app.state.bot_task = bot_task

    yield

    scheduler.shutdown()
    if bot_task is not None and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

    poll_task = bot_state.get("poll_task")
    if bot_app is not None and getattr(bot_app, "running", False):
        try:
            if bot_app.updater and bot_app.updater.running:
                await bot_app.updater.stop()
            if poll_task is not None:
                poll_task.cancel()
                try:
                    await poll_task
                except asyncio.CancelledError:
                    pass
            await bot_app.stop()
            await bot_app.shutdown()
        except Exception:
            logger.exception("Ошибка при остановке Telegram-бота")
    logger.info("Shutdown complete (%s)", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/health")
    def health() -> dict:
        bot_state = getattr(app.state, "bot_state", {}) or {}
        return {
            "status": "ok",
            "bot_ready": bool(bot_state.get("bot_ready")),
        }

    return app


app = create_app()
