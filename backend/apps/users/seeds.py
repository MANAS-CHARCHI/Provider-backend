from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Users, UserRole
from .security import hash_password
import os

DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")


async def create_default_admin(db: AsyncSession):
    admin = await db.scalar(
        select(Users).where(Users.email == DEFAULT_ADMIN_EMAIL)
    )
    if admin:
        return

    admin_user = Users(
        email=DEFAULT_ADMIN_EMAIL,
        password=hash_password(DEFAULT_ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )

    # Skip activation hook
    admin_user._skip_activation = True

    db.add(admin_user)
    await db.commit()

