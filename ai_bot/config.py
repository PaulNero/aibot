"""Настройки приложения."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Глобальные настройки приложения.
    
    Все настройки загружаются из переменных окружения или .env файла.
    Использует Pydantic Settings для валидации и типизации.
    """
    DATABASE_URL: str = 'sqlite:///db/aibot.db'
    REDIS_URL: str = 'redis://localhost:6379/0'
    
    # Telegram Application API (для Telethon) - получить на https://my.telegram.org/
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_SESSION_NAME: str = 'aibot_session'
    PHONE_NUMBER: Optional[str] = None

    # Telegram Bot API токены (получить у @BotFather)
    TELEGRAM_PUBLISHER_BOT_TOKEN: Optional[str] = None  # Бот для публикации постов
    TELEGRAM_ADMIN_BOT_TOKEN: Optional[str] = None      # Бот для администрирования

    # Telegram канал для публикации (username канала, например @channel_name)
    TELEGRAM_CHANNEL_USERNAME: Optional[str] = None

    # Список админов (ID пользователей Telegram, разделенные запятой)
    TELEGRAM_ADMIN_USER_IDS: Optional[str] = None

    # Обратная совместимость (устаревшие названия)
    @property
    def TELEGRAM_BOT_TOKEN(self) -> Optional[str]:
        """Устаревшее свойство для обратной совместимости."""
        return self.TELEGRAM_PUBLISHER_BOT_TOKEN

    OPENAI_API_KEY: Optional[str]
    OPENAI_MODEL: str = 'gpt-4o-mini'

    # Альтернативные AI провайдеры
    OLLAMA_BASE_URL: str = 'http://localhost:11434'  # Для локальной Ollama
    OLLAMA_MODEL: str = 'llama3.2'  # Модель для Ollama
    USE_LOCAL_LLM: bool = False  # Включить локальную LLM вместо OpenAI

    # Бесплатные альтернативы
    HUGGINGFACE_API_KEY: Optional[str] = None  # Для Hugging Face Inference API
    TOGETHER_API_KEY: Optional[str] = None  # Для Together AI (есть free tier)

    PROXY_URL: str
    
    CELERY_BROKER_URL: str = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND: str = 'redis://localhost:6379/0'
    
    PARSE_INTERVAL_MINUTES: int = 30  # Парсим каждые 30 минут, чтобы не забанили
    
    DEBUG: bool = True
    
    model_config = SettingsConfigDict(
        env_file = '.env',
        env_file_encoding = 'utf-8',
        case_sensitive = True,
        extra = 'ignore'
    )
    
settings = Settings()