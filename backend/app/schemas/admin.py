# app/schemas/admin.py
from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    """Schema for creating a product"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Limited Edition Sneakers",
                "description": "Nike Air Jordan 1 Retro High"
            }
        }


class SessionCreate(BaseModel):
    """Schema for creating a bidding session"""
    product_id: str
    upset_price: float = Field(..., gt=0)
    inventory: int = Field(..., gt=0)
    alpha: float = Field(0.5, ge=0)
    beta: float = Field(1000.0, ge=0)
    gamma: float = Field(2.0, ge=0)
    duration_minutes: int = Field(60, gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "uuid-here",
                "upset_price": 200.0,
                "inventory": 5,
                "alpha": 0.5,
                "beta": 1000.0,
                "gamma": 2.0,
                "duration_minutes": 60
            }
        }


class CombinedCreate(BaseModel):
    """Schema for creating product and session together"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    upset_price: float = Field(..., gt=0)
    inventory: int = Field(..., gt=0)
    alpha: float = Field(0.5, ge=0)
    beta: float = Field(1000.0, ge=0)
    gamma: float = Field(2.0, ge=0)
    duration_minutes: int = Field(60, gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Limited Edition Sneakers",
                "description": "Nike Air Jordan 1",
                "upset_price": 200.0,
                "inventory": 5,
                "alpha": 0.5,
                "beta": 1000.0,
                "gamma": 2.0,
                "duration_minutes": 60
            }
        }
