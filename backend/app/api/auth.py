# app/api/auth.py
import asyncio
import time
from datetime import datetime
from typing import Any, Mapping
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_db
from app.core.jwt import create_access_token, decode_access_token
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister, UserResponse

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class InMemoryTokenCache:
    """Per-process token cache that shields Redis during bursts."""

    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._store: dict[str, tuple[float, dict[str, str]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, token: str) -> dict[str, str] | None:
        now = time.monotonic()
        async with self._lock:
            record = self._store.get(token)
            if not record:
                return None
            expires_at, payload = record
            if expires_at <= now:
                self._store.pop(token, None)
                return None
            return payload

    async def set(self, token: str, payload: dict[str, str]) -> None:
        expiry = time.monotonic() + self._ttl
        async with self._lock:
            if self._max_entries > 0 and len(self._store) >= self._max_entries:
                # Drop the entry that expires soonest to keep memory bounded.
                stale_token = min(self._store.items(), key=lambda item: item[1][0])[0]
                self._store.pop(stale_token, None)
            self._store[token] = (expiry, payload)


token_cache = InMemoryTokenCache(
    ttl_seconds=settings.AUTH_CACHE_TTL_SECONDS,
    max_entries=settings.AUTH_CACHE_MAX_ENTRIES,
)


def _safe_decode(value) -> str:
    """
    Safely decode value regardless of whether it's bytes or str.

    Args:
        value: Value to decode (bytes or str)

    Returns:
        Decoded string
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def _normalize_payload(payload: Mapping[Any, Any]) -> dict[str, str]:
    """Convert redis/local cache payload values to plain strings."""
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(key, bytes):
            normalized_key = key.decode("utf-8")
        else:
            normalized_key = str(key)
        normalized[normalized_key] = _safe_decode(value)
    return normalized


def _user_from_payload(payload: Mapping[str, str]) -> User:
    return User(
        id=UUID(payload.get("id", uuid4().hex)),
        username=payload.get("username", ""),
        email=payload.get("email", ""),
        weight=float(payload.get("weight", "1.0")),
        is_admin=payload.get("is_admin", "0") == "1",
        password="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _serialize_user(user: User) -> dict[str, str]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "weight": str(user.weight),
        "is_admin": "1" if user.is_admin else "0",
    }


async def cache_user_in_redis(redis: Redis, user: User) -> None:
    """
    Cache user data in Redis for fast lookup.
    TTL: 24 hours (same as JWT expiration)
    """
    user_cache_key = f"user:{user.id}"
    await redis.hset(user_cache_key, mapping=_serialize_user(user))
    # Expire after 24 hours (same as JWT)
    await redis.expire(user_cache_key, 60 * 60 * 24)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    ⚡ HIGH PERFORMANCE: Get current user from JWT + Redis cache.
    ZERO PostgreSQL queries for authentication!

    Flow:
    1. Decode JWT token (no DB, just signature verification)
    2. Try Redis cache first (< 1ms)
    3. Return User object reconstructed from JWT + cache

    This eliminates the biggest bottleneck in high-concurrency bid requests.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode JWT token (no database query)
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception

    local_cache_hit = await token_cache.get(token)
    if local_cache_hit:
        return _user_from_payload(local_cache_hit)

    # Try Redis cache next
    user_cache_key = f"user:{token_data.user_id}"
    cached_user = await redis.hgetall(user_cache_key)

    if cached_user:
        normalized = _normalize_payload(cached_user)
        await token_cache.set(token, normalized)
        return _user_from_payload(normalized)

    # Fallback: Reconstruct minimal User from JWT (no DB query!)
    # This happens if cache expired but JWT is still valid
    fallback_payload = {
        "id": str(token_data.user_id),
        "username": token_data.username or "",
        "email": "",
        "weight": "1.0",
        "is_admin": "0",
    }
    await token_cache.set(token, fallback_payload)
    return _user_from_payload(fallback_payload)


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_async_db)):
    """
    Register a new user.

    Request body:
    {
        "username": "user1",
        "email": "user1@test.com",
        "password": "test123",
        "is_admin": true
    }
    """

    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        id=uuid4(),
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
        is_admin=user_data.is_admin,
        weight=1.0 + (hash(user_data.username) % 100) / 100,  # Random weight 1.0-2.0
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create JWT token with username embedded
    access_token = create_access_token(
        user_id=new_user.id,
        username=new_user.username,
    )

    return {
        "user_id": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "token": access_token,
        "weight": new_user.weight,
        "is_admin": new_user.is_admin,
    }


@router.post("/login", response_model=UserResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_async_db),
    redis: Redis = Depends(get_redis),
):
    """
    Login user and return JWT token.
    Also caches user data in Redis for fast authentication.

    Request body:
    {
        "username": "user1",
        "password": "test123"
    }
    """

    # Find user by username
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token with username embedded
    access_token = create_access_token(
        user_id=user.id,
        username=user.username,
    )

    # Cache user in Redis for fast subsequent authentication
    await cache_user_in_redis(redis, user)
    await token_cache.set(access_token, _serialize_user(user))

    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "token": access_token,
        "weight": user.weight,
        "is_admin": user.is_admin,
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user information.
    Requires authentication.
    """
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "weight": current_user.weight,
        "is_admin": current_user.is_admin,
    }
