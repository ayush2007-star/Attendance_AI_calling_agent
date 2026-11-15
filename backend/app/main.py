from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.error_handlers import register_exception_handlers
from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from app.db.auto_seed import run_auto_seed
        run_auto_seed()
    except Exception as exc:
        logger.error("Auto-seed on startup failed: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment.lower() != "production" else None,
    redoc_url="/redoc" if settings.environment.lower() != "production" else None,
    openapi_url="/openapi.json" if settings.environment.lower() != "production" else None,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "attendance-ai-agent",
    }


@app.get("/ready")
def readiness_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}


app.include_router(
    api_router,
    prefix="/api/v1",
)

register_exception_handlers(app)
