from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = (
    ROOT_DIR / ".env",
    Path(".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(path) for path in ENV_FILES if path.exists()] or ".env",
        extra="ignore",
    )
    app_name: str = "AI Watcher"
    env: str = "development"
    secret_key: str = "change-me-in-production"
    jwt_access_expires_minutes: int = 60 * 12

    postgres_user: str = "watcher"
    postgres_password: str = "watcher"
    postgres_db: str = "watcher"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    connection_string: str | None = None

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    telegram_bot_token: str = ""
    admin_telegram_chat_id: str | None = None
    telegram_proxy_url: str | None = None

    default_geo_radius_m: int = 500
    reminder_minutes_before: int = 15
    morning_check_hour: int = 10
    morning_check_minute: int = 0
    timezone: str = "Europe/Moscow"

    admin_username: str = "admin"
    admin_password: str = "admin"

    @property
    def database_url(self) -> str:
        if self.connection_string:
            return self.connection_string
        from urllib.parse import quote_plus

        password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
