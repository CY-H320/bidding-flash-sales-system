# app/api/auth.py
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def cache_user_in_redis(redis: Redis, user: User) -> None:
    """
    Cache user data in Redis for fast lookup.
    TTL: 24 hours (same as JWT expiration)
    """
    user_cache_key = f"user:{user.id}"
    await redis.hset(
        user_cache_key,
        mapping={
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "weight": str(user.weight),
            "is_admin": "1" if user.is_admin else "0",
        },
    )
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

    # Try Redis cache first
    user_cache_key = f"user:{token_data.user_id}"
    cached_user = await redis.hgetall(user_cache_key)

    if cached_user:
        # Reconstruct User object from cache
        # Get values with flexible key access (bytes or str)
        user_id = cached_user.get(b"id") or cached_user.get("id")
        username = cached_user.get(b"username") or cached_user.get("username")
        email = cached_user.get(b"email") or cached_user.get("email")
        weight = cached_user.get(b"weight") or cached_user.get("weight")
        is_admin = cached_user.get(b"is_admin") or cached_user.get("is_admin")

        user = User(
            id=UUID(_safe_decode(user_id)),
            username=_safe_decode(username),
            email=_safe_decode(email),
            weight=float(_safe_decode(weight)),
            is_admin=_safe_decode(is_admin) == "1",
            password="",  # Not needed for authentication
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return user

    # Fallback: Reconstruct minimal User from JWT (no DB query!)
    # This happens if cache expired but JWT is still valid
    user = User(
        id=token_data.user_id,
        username=token_data.username,
        email="",  # Not critical for bidding
        weight=1.0,  # Default weight if cache miss
        is_admin=False,
        password="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return user


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
