from fastapi import APIRouter
from .tasks import send_email_task

router = APIRouter()

@router.post("/send-email")
async def trigger_email(email: str, token: str):
    # Trigger the task

    task=send_email_task.delay(email, token)
    return {"message": "Email task queued", "task_id": task.id}
