from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine with optimized connection pool for high concurrency
# Balanced configuration: prevents "too many clients" while handling load
# WebSocket connections use on-demand sessions (short-lived)
# Background tasks create sessions per operation cycle
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL logging for performance
    future=True,
    pool_pre_ping=True,  # Check connection health before use
    pool_size=30,  # Core pool connections (balance between availability and limits)
    max_overflow=70,  # Additional connections for burst (total max = 100)
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_timeout=20,  # Wait max 20 seconds for a connection (increased to handle spikes)
    pool_use_lifo=True,  # Use LIFO to reuse recent connections (better for connection health)
    connect_args={
        "server_settings": {
            "timezone": "UTC",  # Force PostgreSQL to use UTC timezone
            "application_name": "bidding_system",
        },
        "command_timeout": 30,  # Command timeout in seconds
        "timeout": 10,  # Connection timeout in seconds
    },
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
