from fastapi import FastAPI

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