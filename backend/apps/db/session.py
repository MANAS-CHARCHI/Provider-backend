from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from database import DATABASE_URL

# 1. Create engine
engine = create_async_engine(DATABASE_URL, echo=False)

# 2. Create async session factory
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)

