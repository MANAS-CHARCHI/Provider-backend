from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Response, Request
from sqlalchemy import select, delete, update, or_
from sqlalchemy.orm import selectinload
from .models import Users, TokenBlacklist, Invitation, UserRole, Activations, UserReview, Activity
from .schemas import UserCreate, UserLogin, InvitationCreate, UserProfileResponse, UserReviewBody, UserUpdate
from datetime import datetime, timedelta, timezone
import os
from fastapi.responses import RedirectResponse
import jwt
from config import settings
from apps.users.security import hash_password, verify_password
import uuid
import secrets
from apps.send_email.tasks import send_email_task
from apps.users.dependency import get_current_user


def create_access_token(
    subject: str,
    user_id: str,
    role: str,
    expires_delta: timedelta
):
    payload = {
        "sub": subject,
        "id": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + expires_delta
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def create_refresh_token(
    subject: str,
    user_id: str,
    role: str,
    expires_delta: timedelta
):
    payload = {
        "sub": subject,
        "id": user_id,
        "role": role,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + expires_delta
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)

async def create_user_view(user: UserCreate, db: AsyncSession, invitation_token: Optional[str] = None):
    if invitation_token:
        # Validate invitation token
        result = await db.execute(
            select(Invitation).where(
                Invitation.token == invitation_token,
                Invitation.expires_at > datetime.now(timezone.utc)
            )
        )
        invitation = result.scalar_one_or_none()
        if not invitation or invitation.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Invalid or expired invitation token")
        user.email=invitation.email
        assigned_role=invitation.role

    existing_user_query= select(Users).where(Users.email == user.email)
    result = await db.execute(existing_user_query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    if invitation_token:
        db_user = Users(email=user.email, password=hash_password(user.password), role=assigned_role, invited_by=invitation.creator_id, is_active=True)
        db_user._skip_activation = True  # Custom attribute to skip activation email
    else:
        db_user = Users(email=user.email, password=hash_password(user.password))
        db_user._skip_activation = False  # Custom attribute to indicate activation email should be sent
    db.add(db_user)
    if invitation_token:
        await db.delete(invitation)
    await db.commit()
    await db.refresh(db_user)
    # get actiavtein token from Activations
    get_activation_token=await db.execute(select(Activations).where(Activations.user_id==db_user.id))
    activation_token=get_activation_token.scalar_one_or_none()
    if activation_token and not getattr(db_user, "_skip_activation", False):
        send_email_task.delay(db_user.email, activation_token.activation_code)
        
    return db_user

async def get_users_view(db: AsyncSession, request: Request):

    user_email = request.state.user_email
    try:
        result = await db.execute(select(Users).where(Users.email == user_email))
        db_user = result.scalar_one_or_none()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error")
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

async def create_user_review_view(db: AsyncSession, request: Request, body: UserReviewBody):
    review = UserReview(
        user_id=request.state.user_id,
        review=body.review,
        consent=body.consent,
    )
    db.add(review)
    # Log the activity
    log = Activity(
        user_id=request.state.user_id,
        action="USER_REVIEW_ADDED, Review is: " + str(review.review),
    )
    db.add(log)
    await db.commit()
    await db.refresh(review)
    return {
        "reviewer": request.state.user_email,
        "review": review.review,
        "consent": review.consent,
    }
async def get_user_reviews_view(db: AsyncSession, request: Request):
    user_id = getattr(request.state, "user_id", None)

    # Base query: always join users (we always return reviewer info)
    stmt = (
        select(UserReview, Users)
        .join(Users, Users.id == UserReview.user_id)
    )

    # Visibility rules
    if user_id:
        # Public reviews OR user's own reviews
        stmt = stmt.where(
            or_(
                UserReview.consent == True,
                UserReview.user_id == user_id,
            )
        )
    else:
        # Only public reviews
        stmt = stmt.where(
            UserReview.consent == True
        )

    stmt = stmt.order_by(UserReview.id.desc())

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "review_id": review.id,
            "review": review.review,
            "consent": review.consent,
            "reviewer": {
                "id": str(user.id),
                "full_name": user.full_name,
                "linkedin": user.linkedin,
                "github": user.github,
                "twitter": user.twitter,
                "website": user.website,
            },
        }
        for review, user in rows
    ]

async def delete_user_review_view(
    review_id: int,
    db: AsyncSession,
    request: Request,
):
    user_email = request.state.user_email
    result = await db.execute(
        select(Users).where(Users.email == user_email)
    )
    current_user = result.scalar_one_or_none()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    result = await db.execute(
        select(UserReview).where(UserReview.id == review_id)
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # authorization:
    # owner OR admin
    if review.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to delete this review",
        )
    # Log the activity
    log = Activity(
        user_id=request.state.user_id,
        action="USER_REVIEW_DELETE, Review was: "+review.review,
    )
    db.add(log)
    await db.delete(review)
    await db.commit()

    return {"detail": "Review deleted successfully"}

async def login_user_view(user: UserLogin, response: Response, db: AsyncSession):
    result = await db.execute(select(Users).where(Users.email == user.email))
    db_user = result.scalar_one_or_none()
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="User is not active, Please check your email to activate your account")
    if db_user and verify_password(user.password, db_user.password):
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=db_user.email, user_id=str(db_user.id), role=db_user.role, expires_delta=access_token_expires
        )
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            subject=db_user.email, user_id=str(db_user.id), role=db_user.role, expires_delta=refresh_token_expires
        )

        # insert jti into TokenBlacklist table
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)
        token_blacklist_entry = TokenBlacklist(
            jti=jti,
            user_id=db_user.id,
            expires_at=expires_at
        )
        db.add(token_blacklist_entry)
        await db.commit()

        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=3600)
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=7*24*3600)
        return {"email": db_user.email}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

async def activate_user_view(user_email: str, activation_code: str, db: AsyncSession):
    user_result = await db.execute(
        select(Users).where(Users.email == user_email).options(selectinload(Users.activations))
    )
    db_user = user_result.scalar_one_or_none()
    
    # Use standard HTTP Status Codes
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.is_active:
        return {"status": "already_active", "message": "User is already active"}

    activation = db_user.activations
    if not activation or activation.is_used or str(activation.activation_code) != str(activation_code):
        raise HTTPException(status_code=400, detail="Invalid or used token")

    db_user.is_active = True
    db_user.activations.is_used = True

    # Log the activity
    log = Activity(
        user_id=db_user.id,
        action="USER_ACTIVATED",
    )
    db.add(log)
    await db.commit()
    
    # Return a success object instead of a 302/303 redirect
    return {"status": "success", "message": "Account activated"}

async def refresh_token_view(db: AsyncSession, request: Request, response: Response):
    # This function assumes the refresh token is sent via cookies
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        old_jti = payload.get("jti")
        user_email = payload.get("sub")
        user_id = payload.get("id")
        user_role = payload.get("role") 
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Check if jti is in TokenBlacklist
    new_refresh_token = create_refresh_token(
            subject=user_email, user_id=str(user_id), role=user_role, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    new_payload = jwt.decode(new_refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    new_jti = new_payload.get("jti")
    new_exp = datetime.fromtimestamp(new_payload.get("exp"), tz=timezone.utc)

    # Attempt to update the row and if exist return ID
    statement = (
        update(TokenBlacklist)
        .where(TokenBlacklist.jti == old_jti)
        .values(jti=new_jti, expires_at=new_exp)
        .returning(TokenBlacklist.id)
    )
    result = await db.execute(statement)
    updated_id = result.scalar_one_or_none()

    if updated_id is None:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or has been revoked")
    try:
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update refresh token")
    
    new_access_token = create_access_token(
        subject=user_email, user_id=user_id, role=user_role, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    response.set_cookie(key="access_token", value=new_access_token, httponly=True, secure=False, samesite="lax")
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, secure=False, samesite="lax")
    return {"message": "Access token refreshed"}

async def logout_user_view(db: AsyncSession, request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        jti = payload.get("jti")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    # Delete the token from TokenBlacklist
    statement = (
        delete(TokenBlacklist)
        .where(TokenBlacklist.jti == jti)
    )
    await db.execute(statement)
    # Log the activity
    log = Activity(
        user_id=request.state.user_id,
        action="USER_LOGOUT",
    )
    db.add(log)
    await db.commit()
    
    # Clear cookies
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    
    return {"message": "Logged out successfully"}

async def invite_user_view(body: InvitationCreate, db: AsyncSession, request: Request):
    token = generate_secure_token()
    new_invite = Invitation(
        email=body.email,
        role=body.role,
        creator_id=request.state.user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_invite)
    await db.commit()
    # TODO: Send invitation email with the token link
    verification_link= f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/register?invitation_token={token}"
    print(f"Invitation Link is : {verification_link}")

    return {"message": "Invitation sent successfully"}

async def get_all_user_view(db: AsyncSession, request: Request):
    stmt = (
        select(Users)
        .options(selectinload(Users.projects)) # Assuming a relationship is defined
        .order_by(Users.created_at.desc())
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "project_count": len(user.projects),
            "projects": [
                {"id": p.id, "title": p.name} 
                for p in user.projects
            ],
        }
        for user in users
    ]

async def update_user_view(
    db: AsyncSession,
    request: Request,
    body: UserUpdate,
):
    result = await db.execute(
        select(Users).where(Users.id == request.state.user_id)
    )
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_user, field, value)
    # Log the activity
    log = Activity(
        user_id=request.state.user_id,
        action="USER_UPDATE",
    )
    db.add(log)
    try:
        await db.commit()
        await db.refresh(db_user)
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database update failed")

    return db_user

async def get_all_activity_view(db: AsyncSession, request: Request):
    # Get all activities for the user
    activities = await db.execute(select(Activity).options(selectinload(Activity.user)).order_by(Activity.timestamp.desc()))
    activities = activities.scalars().all()

    return [{
            "activity_id": a.id,
            "timestamp": a.timestamp,
            "user_email": a.user.email,
            "user_full_name": a.user.full_name,
            "task": a.action
        }
        for a in activities]