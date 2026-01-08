from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = 'sqlite:///db/aibot.db'
    REDIS_URL: str = 'redis://localhost:6379/0'
    
    TELEGRAM_API_ID: Optional[int]
    TELEGRAM_API_HASH: Optional[str]
    TELEGRAM_SESSION_NAME: str = 'aibot_session'
    TELEGRAM_CHANNEL_USERNAME: Optional[str]
    
    OPENAI_API_KEY: Optional[str]
    OPENAI_MODEL: str = 'gpt-4o-mini'
    
    CELERY_BROKER_URL: str = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND: str = 'redis://localhost:6379/0'
    
    PARSE_INTERVAL_MINUTES: int = 30
    
    DEBUG: bool = True
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True
        
settings = Settings()