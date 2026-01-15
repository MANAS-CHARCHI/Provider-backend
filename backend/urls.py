from fastapi import APIRouter
from apps.users.urls import router as users_router
from apps.send_email.urls import router as email_router
from apps.projects.urls import router as projects_router

api_v1_router = APIRouter()

api_v1_router.include_router(users_router, prefix="/users", tags=["Users"])
api_v1_router.include_router(email_router, prefix="/email", tags=["Email"])
api_v1_router.include_router(projects_router, prefix="/projects", tags=["Projects"])

root_router = APIRouter()
root_router.include_router(api_v1_router, prefix="/api/v1")