from contextlib import asynccontextmanager

from fastapi import FastAPI

from ai_bot.db.db_manager import init_db, async_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await async_engine.dispose()


app = FastAPI(
    title='AIBot',
    description='AIBot',
    version='0.0.1',
    lifespan=lifespan
)




@app.get("/")
def read_root():
    return {"message": "Hello World"}

