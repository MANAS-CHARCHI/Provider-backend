from datetime import datetime
import enum
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    event,
    insert,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

import uuid_utils
from apps.db.base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.projects.models import Project


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"
    GUEST = "guest"


class Users(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid_utils.uuid7,
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String, nullable=True)

    password: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.USER,
        nullable=False,
    )

    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    location: Mapped[str | None] = mapped_column(String, nullable=True)

    linkedin: Mapped[str | None] = mapped_column(String, nullable=True)

    github: Mapped[str | None] = mapped_column(String, nullable=True)

    twitter: Mapped[str | None] = mapped_column(String, nullable=True)

    website: Mapped[str | None] = mapped_column(String, nullable=True)

    activations: Mapped["Activations"] = relationship(
        "Activations",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="creator",
    )

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="owner",
    )

    reviews: Mapped[list["UserReview"]] = relationship(
        "UserReview",
        back_populates="user",
        cascade="all, delete-orphan",
    )

class Activity(Base):
    __tablename__ = "activities"

    id = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )    
    action = mapped_column(String)
    timestamp = mapped_column(DateTime, default=func.now())

    user = relationship("Users")

class Activations(Base):
    __tablename__ = "activations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    activation_code: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["Users"] = relationship(
        "Users",
        back_populates="activations",
    )


@event.listens_for(Users, "after_insert")
def create_activation_token(mapper, connection, target):
    if getattr(target, "_skip_activation", False):
        return

    stmt = insert(Activations.__table__).values(
        user_id=target.id,
        activation_code=str(uuid.uuid4()),
    )
    connection.execute(stmt)


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    user: Mapped["Users"] = relationship("Users")

class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)

    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    creator: Mapped["Users"] = relationship(
        "Users",
        back_populates="invitations",
    )

class UserReview(Base):
    __tablename__ = "user_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    review: Mapped[str] = mapped_column(String(255), nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    user: Mapped[Users] = relationship(
        "Users",
        back_populates="reviews",
    )