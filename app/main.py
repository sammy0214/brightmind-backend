from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import init_models
from app.routers import auth, children, dashboard, sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().auto_create_tables:  # MVP convenience; use Alembic migrations in prod
        await init_models()
    yield


app = FastAPI(title="BrightMind API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(children.router)
app.include_router(sessions.router)
app.include_router(dashboard.router)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "region": get_settings().region}
