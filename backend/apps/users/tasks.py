from celery import shared_task
from datetime import datetime, timezone
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from .models import TokenBlacklist
import asyncio


async def _remove_tokens_logic():
    """
    Periodically deletes tokens from the blacklist that have already expired.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Create a delete statement for tokens where expires_at < now
            statement = (
                delete(TokenBlacklist)
                .where(TokenBlacklist.created_at < datetime.now(timezone.utc))
            )
            
            # Execute the deletion
            result = await db.execute(statement)
            await db.commit()
            return f"Removed {result.rowcount} expired tokens."
        except Exception as e:
            await db.rollback()
            raise e

# @shared_task
# def remove_blacklisted_token_task():
#     """Synchronous Celery task that runs the async logic."""
#     return asyncio.run(_remove_tokens_logic())