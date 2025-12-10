# app/core/jwt.py
"""JWT token utilities for high-performance authentication."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenData(BaseModel):
    """JWT Token payload data."""

    user_id: UUID
    username: str
    exp: datetime


# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


def create_access_token(user_id: UUID, username: str) -> str:
    """
    Create a JWT access token for a user.

    Args:
        user_id: User's UUID
        username: User's username

    Returns:
        JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "user_id": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id_str = payload.get("user_id")
        username = payload.get("username")
        exp = payload.get("exp")

        if user_id_str is None or username is None:
            return None

        # Convert exp timestamp to datetime
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)

        return TokenData(
            user_id=UUID(user_id_str),
            username=username,
            exp=exp_datetime,
        )

    except JWTError:
        return None
    except Exception:
        return None


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid without decoding full payload.

    Args:
        token: JWT token string

    Returns:
        True if valid, False otherwise
    """
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False
