from fastapi import APIRouter
from app.api.v1.routes.campaigns import router as campaigns_router
from app.api.v1.routes.classes import router as classes_router
from app.api.v1.routes.students import router as students_router
from app.api.v1.routes.attendance import router as attendance_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.attendance_import import router as attendance_import_router
from app.api.v1.routes.student_import import router as student_import_router
from app.api.v1.routes.calls import router as calls_router
from app.api.v1.routes.followups import router as followups_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.leaves import router as leaves_router
from app.api.v1.routes.student_parents import router as student_parents_router
from app.api.v1.routes.parents import router as parents_router
from app.api.v1.routes.scopes import router as scopes_router
from app.api.v1.routes.reports import router as reports_router
from app.api.v1.routes.ml_analytics import router as ml_analytics_router
from app.api.v1.routes.voice_agent_api import router as voice_agent_router

api_router = APIRouter()

# Classes & Students
api_router.include_router(classes_router)
api_router.include_router(students_router)

# Attendance
api_router.include_router(attendance_router)

# Users & Auth
api_router.include_router(users_router)
api_router.include_router(auth_router)

# Imports & Campaigns
api_router.include_router(attendance_import_router)
api_router.include_router(student_import_router)
api_router.include_router(campaigns_router)
api_router.include_router(calls_router)
api_router.include_router(followups_router)

# Dashboard & Leaves
api_router.include_router(dashboard_router)
api_router.include_router(leaves_router)
api_router.include_router(parents_router)
api_router.include_router(student_parents_router)
api_router.include_router(scopes_router)

# 2026 AI / ML & Voice Agent Integrations
api_router.include_router(ml_analytics_router)
api_router.include_router(reports_router)
api_router.include_router(voice_agent_router)
