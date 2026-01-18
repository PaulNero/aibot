"""AI News Bot API - FastAPI приложение для управления ботом генерации новостей."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_bot.db.db_manager import init_db, async_engine
from ai_bot.api.endpoints import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    await init_db()
    yield
    await async_engine.dispose()


app = FastAPI(
    title='AI News Bot API',
    description='API для управления AI-ботом генерации постов для Telegram',
    version='1.0.0',
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")




@app.get("/")
def read_root():
    """Корневой эндпоинт API."""
    return {
        "message": "AI News Bot API",
        "docs": "/docs",
        "version": "1.0.0"
    }

