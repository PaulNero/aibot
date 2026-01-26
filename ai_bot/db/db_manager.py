from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from ai_bot.config import settings
from ai_bot.db.models import Base

sync_url = settings.DATABASE_URL


def get_async_url() -> str:
    """
    Преобразует синхронный URL БД в асинхронный.
    
    Returns:
        Асинхронный URL для SQLAlchemy
    """
    if sync_url.startswith('sqlite://'):
        async_url = sync_url.replace('sqlite://', 'sqlite+aiosqlite://')
    elif sync_url.startswith('postgresql+psycopg://'):
        async_url = sync_url.replace('postgresql+psycopg://', 'postgresql+asyncpg://')
    else:
        async_url = sync_url
    return async_url


async_engine = create_async_engine(get_async_url(), echo=settings.DEBUG)
sync_engine = create_engine(sync_url, echo=settings.DEBUG)

async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
sync_session_factory = sessionmaker(sync_engine)


async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """
    Генератор асинхронной сессии БД для FastAPI.
    
    Yields:
        Асинхронная сессия SQLAlchemy
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


def get_db_sync() -> Generator[Session]:
    """
    Генератор синхронной сессии БД для Celery.
    
    Yields:
        Синхронная сессия SQLAlchemy
    """
    session = sync_session_factory()
    try:
        yield session
    finally:
        session.close()


async def init_db():
    """Инициализирует схему базы данных (создает таблицы)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)