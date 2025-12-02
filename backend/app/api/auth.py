# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from uuid import uuid4

from app.core.database import get_async_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, UserResponse

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    Use this in protected endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Register a new user.

    Request body:
    {
        "username": "user1",
        "email": "user1@test.com",
        "password": "test123"
    }
    """

    # Check if username exists
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        id=uuid4(),
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
        is_admin=False,
        weight=1.0 + (hash(user_data.username) % 100) / 100,  # Random weight 1.0-2.0
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return {
        "user_id": str(new_user.id),
        "username": new_user.username,
        "email": new_user.email,
        "token": access_token,
        "weight": new_user.weight,
        "is_admin": new_user.is_admin
    }


@router.post("/login", response_model=UserResponse)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Login user and return JWT token.

    Request body:
    {
        "username": "user1",
        "password": "test123"
    }
    """

    # Find user by username
    result = await db.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "user_id": str(user.id),
        "username": user.username,
        "email": user.email,
        "token": access_token,
        "weight": user.weight,
        "is_admin": user.is_admin
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
        "is_admin": current_user.is_admin
    }