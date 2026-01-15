
from fastapi import FastAPI
from celery import Celery
from celery.schedules import crontab
from urls import root_router
import os
import jwt
from apps.users.seeds import create_default_admin
from apps.db.session import async_session
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# Allow CORS from all origins
origins = os.getenv("ALLOWED_FRONTEND_ORIGINS", "http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Create Admin after project startup
@app.on_event("startup")
async def startup_event():
    async with async_session() as db:
        await create_default_admin(db)

celery_app = Celery(
    "worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.autodiscover_tasks(['apps.send_email', 'apps.users', 'apps.projects'], related_name='tasks')

# Configure Celery to use JSON serialization
celery_app.conf.update(
    # TTL: Results are removed from Redis after 5 min
    result_expires=360,
    timezone="UTC",
    enable_utc=True,
    # beat_schedule={
    #     "remove-expired-blacklisted-tokens-midnight": {
    #         "task": "apps.users.tasks.remove_blacklisted_token_task",
    #         "schedule": crontab(hour=12, minute=0),  # 12:00 AM
    #     },
    # },
    task_acks_late=True,

    task_serializer="json",
    result_serializer="json",
    accept_content=["json"]
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Connect the central routing system
app.include_router(root_router)