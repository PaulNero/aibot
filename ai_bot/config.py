"""Настройки приложения."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Глобальные настройки приложения."""
    DATABASE_URL: str = 'sqlite:///db/aibot.db'
    REDIS_URL: str = 'redis://localhost:6379/0'
    
    # Telegram Application API (для Telethon) - получить на https://my.telegram.org/
    TELEGRAM_API_ID: Optional[int]
    TELEGRAM_API_HASH: Optional[str]
    TELEGRAM_SESSION_NAME: str = 'aibot_session'

    # Telegram Bot API (альтернатива) - получить у @BotFather
    TELEGRAM_BOT_TOKEN: Optional[str]

    # Telegram Bot API токен (для публикации через бота)
    TELEGRAM_BOT_TOKEN: Optional[str]

    # Telegram канал для публикации (username канала, например @channel_name)
    TELEGRAM_CHANNEL_USERNAME: Optional[str]

    # Устаревшие названия для обратной совместимости (опциональные)
    TELERGAM_API_ID: Optional[int] = None  # TODO: Remove after migration
    TELERGAM_API_HASH: Optional[str] = None  # TODO: Remove after migration
    TELERGAM_SESSION_NAME: Optional[str] = None  # TODO: Remove after migration
    TELERGAM_CHANNEL_USERNAME: Optional[str] = None  # TODO: Remove after migration
    
    OPENAI_API_KEY: Optional[str]
    OPENAI_MODEL: str = 'gpt-4o-mini'
    PROXY_URL: str
    
    CELERY_BROKER_URL: str = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND: str = 'redis://localhost:6379/0'
    
    PARSE_INTERVAL_MINUTES: int = 1
    
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file = '.env',
        env_file_encoding = 'utf-8',
        case_sensitive = True,
        extra = 'ignore'
    )
    
settings = Settings()