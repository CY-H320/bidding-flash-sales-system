from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine with optimized connection pool for high concurrency
# When using PgBouncer: Keep more connections since PgBouncer manages the real pool
# When not using PgBouncer: Conservative settings to prevent connection exhaustion
if settings.USE_PGBOUNCER:
    # PgBouncer mode: More aggressive pooling since PgBouncer handles the backend
    pool_config = {
        "pool_size": 50,  # More connections to PgBouncer (cheap)
        "max_overflow": 100,  # Allow bursts (total = 150 to PgBouncer)
        "pool_recycle": 300,  # PgBouncer handles recycling, so relax here
        "pool_timeout": 30,  # More patient since PgBouncer is fast
        "pool_pre_ping": False,  # PgBouncer handles connection health
    }
else:
    # Direct mode: Conservative settings to protect PostgreSQL
    pool_config = {
        "pool_size": 20,  # Fewer direct connections to PostgreSQL
        "max_overflow": 30,  # Limited overflow (total = 50)
        "pool_recycle": 120,  # Aggressive recycling to prevent leaks
        "pool_timeout": 10,  # Fail fast if pool exhausted
        "pool_pre_ping": True,  # Check connection health
    }

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disable SQL logging for performance
    future=True,
    pool_use_lifo=True,  # Use LIFO to reuse recent connections
    connect_args={
        "server_settings": {
            "timezone": "UTC",  # Force PostgreSQL to use UTC timezone
            "application_name": "bidding_system",
        },
        "command_timeout": 30,  # Command timeout
        "statement_cache_size": 0,  # Prepared statement cache size
        "timeout": 15,  # Connection establishment timeout
    },
    **pool_config,
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
