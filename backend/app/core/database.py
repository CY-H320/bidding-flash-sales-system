from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create non-blocking session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """All ORM models base class"""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency: Provide database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db to match usage in other files"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database, create all tables"""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models import (  # noqa: F401
            BiddingProduct,
            BiddingSession,
            BiddingSessionRanking,
            User,
        )

        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connection"""
    await engine.dispose()
