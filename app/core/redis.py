from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings


class RedisClient:
    """Redis client manager class"""

    def __init__(self):
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis"""
        if self._pool is None:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            self._client = Redis(connection_pool=self._pool)

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    def get_client(self) -> Redis:
        """Get Redis client instance"""
        if self._client is None:
            raise RuntimeError("Redis client is not connected. Call connect() first.")
        return self._client

    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return await self._client.ping()
        except Exception:
            return False


redis_client = RedisClient()


async def get_redis() -> Redis:
    """FastAPI Dependency: Provide Redis client"""
    return redis_client.get_client()


class RedisService:
    """Redis service class, provides common Redis operations"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Optional[str]:
        """Get cache value"""
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: int = 3600) -> bool:
        """Set cache value"""
        return await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """Delete cache"""
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        return await self.redis.exists(key) > 0

    async def increment(self, key: str) -> int:
        """Increment counter"""
        return await self.redis.incr(key)

    async def decrement(self, key: str) -> int:
        """Decrement counter"""
        return await self.redis.decr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time"""
        return await self.redis.expire(key, seconds)

    # TODO(sks): add bidding flash sale system methods (e.g. init_stock, get_stock, get_ranking, etc)
