#!/usr/bin/env python3
"""Initialize database tables and Redis connection."""
import asyncio
from app.core.database import init_db
from app.core.redis import redis_client


async def main():
    """Initialize database and test Redis connection."""
    print("Initializing database...")
    try:
        await init_db()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return

    print("\nTesting Redis connection...")
    try:
        await redis_client.connect()
        if await redis_client.ping():
            print("✅ Redis connection successful!")
        else:
            print("❌ Redis ping failed")
        await redis_client.disconnect()
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
