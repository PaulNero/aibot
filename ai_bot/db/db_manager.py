from collections.abc import AsyncGenerator, Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from ai_bot.config import settings
from ai_bot.db.models import Base

### URLs
sync_url = settings.DATABASE_URL

def get_async_url():
    
    if sync_url.startswith('sqlite://'):
        async_url = sync_url.replace('sqlite://', 'sqlite+aiosqlite://')
    if sync_url.startswith('psycopg://'):
        async_url = sync_url.replace('psycopg://', 'asyncpg://')
    return async_url

### Engines
async_engine = create_async_engine(get_async_url(), echo=settings.DEBUG)

# for Alembic and Celery
sync_engine = create_engine(sync_url, echo=settings.DEBUG)


### Factories
async_session_factory = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

sync_session_factory = sessionmaker(sync_engine)


###
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

def get_db_sync() -> Generator[Session]:
    session = sync_session_factory()
    try: 
        yield session
    finally:
        session.close()
        
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)