from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from . import views, schemas
from apps.users.decorators import login_required, role_required
from typing import Optional, List

router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
async def create_user(
    user: schemas.UserCreate, 
    invitation_token: Optional[str]= None,
    db: AsyncSession = Depends(get_db)
):
    return await views.create_user_view(user, db, invitation_token)

@router.post("/activate/{user_email}/{activation_code}", response_model=dict)
async def activate_user(
    user_email: str, 
    activation_code: str, 
    db: AsyncSession = Depends(get_db)
):
    return await views.activate_user_view(user_email, activation_code, db)

@router.post("/login", response_model=schemas.UserLoginResponse)
async def login_user(
    user: schemas.UserLogin, 
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    return await views.login_user_view(user, response, db)

@router.get("/info", response_model=schemas.UserProfileResponse)
@login_required
async def get_users(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.get_users_view(db, request)

@router.get("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await views.refresh_token_view(db, request, response)

@router.post("/update", response_model=schemas.UserResponse)
@login_required
async def update_user(
    body: schemas.UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.update_user_view(db, request, body)


@router.post("/logout", response_model=dict)
@login_required
async def logout_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await views.logout_user_view(db, request, response)

@router.post("/review", response_model=dict)
@login_required
async def review_user(
    body: schemas.UserReviewBody,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.create_user_review_view(db, request, body)

@router.get("/review", response_model=list[schemas.UserReviewResponse])
async def get_reviews(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await views.get_user_reviews_view(db, request)

@router.delete("/review/{review_id}", response_model=dict)
@login_required
async def delete_review(
    review_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await views.delete_user_review_view(review_id, db, request)


@router.post("/admin/invite", response_model=dict)
@login_required
@role_required(["admin"])
async def invite_user(
    body: schemas.InvitationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.invite_user_view(body, db, request)

@router.get("/admin/users", response_model=List[dict])
@login_required
@role_required(["admin"])
async def get_all_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.get_all_user_view(db, request)

@router.get("/admin/activity", response_model=list[dict])
@login_required
@role_required(["admin"])
async def get_all_activity(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    return await views.get_all_activity_view(db, request)
