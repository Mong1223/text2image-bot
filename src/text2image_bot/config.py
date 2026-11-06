"""Настройки приложения. Читаются из переменных окружения и файла .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    """Настройки сервиса инференса (FastAPI)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SERVICE_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    # a1111 — Stable Diffusion web UI (AUTOMATIC1111), dummy — заглушка без GPU
    backend: Literal["a1111", "dummy"] = "a1111"
    a1111_url: str = "http://127.0.0.1:7860"
    a1111_timeout: float = 300.0
    default_steps: int = Field(20, ge=1, le=150)
    default_sampler: str = "Euler a"


class BotSettings(BaseSettings):
    """Настройки Telegram-бота (aiogram)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BOT_", extra="ignore")

    token: SecretStr
    service_url: str = "http://127.0.0.1:8000"
    request_timeout: float = 300.0


@lru_cache
def get_service_settings() -> ServiceSettings:
    return ServiceSettings()


@lru_cache
def get_bot_settings() -> BotSettings:
    return BotSettings()
