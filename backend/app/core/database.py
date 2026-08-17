import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base

# Task 1c: SQLite Lite Mode logic
db_mode = os.getenv("DB_MODE", "sqlite")

if db_mode == "postgres":
    db_url = settings.DATABASE_URL
else:
    # Force SQLite async driver
    db_url = "sqlite+aiosqlite:///./database/app.db"
    
engine = create_async_engine(db_url, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
