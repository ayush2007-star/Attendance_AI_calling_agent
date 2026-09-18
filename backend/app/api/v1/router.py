from fastapi import APIRouter
from app.api.v1.routes.campaigns import router as campaigns_router
from app.api.v1.routes.classes import router as classes_router
from app.api.v1.routes.students import router as students_router
from app.api.v1.routes.attendance import router as attendance_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.attendance_import import router as attendance_import_router
from app.api.v1.routes.calls import router as calls_router
from app.api.v1.routes.followups import router as followups_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.leaves import router as leaves_router

api_router = APIRouter()


api_router.include_router(
    classes_router,
)

api_router.include_router(
    students_router,
)

api_router.include_router(
    attendance_router,
)

api_router.include_router(
    users_router,
)
api_router.include_router(auth_router)

api_router.include_router(attendance_import_router)

api_router.include_router(campaigns_router)

api_router.include_router(calls_router)

api_router.include_router(followups_router)

api_router.include_router(dashboard_router)

api_router.include_router(leaves_router)

