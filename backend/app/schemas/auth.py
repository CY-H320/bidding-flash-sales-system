# app/schemas/auth.py
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """User registration schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=3)  # Using str instead of EmailStr to avoid email-validator dependency
    password: str = Field(..., min_length=6)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user1",
                "email": "user1@example.com",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """User login schema"""
    username: str
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "username": "user1",
                "password": "securepassword123"
            }
        }


class UserResponse(BaseModel):
    """User response schema"""
    user_id: str
    username: str
    email: str
    token: str
    weight: float
    is_admin: bool

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "user1",
                "email": "user1@example.com",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "weight": 1.5,
                "is_admin": False
            }
        }


class Token(BaseModel):
    """Token response schema"""
    access_token: str
    token_type: str = "bearer"
