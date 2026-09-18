from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.error_handlers import register_exception_handlers


app = FastAPI(
    title="Attendance AI Agent API",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "attendance-ai-agent",
    }


app.include_router(
    api_router,
    prefix="/api/v1",
)

register_exception_handlers(app)