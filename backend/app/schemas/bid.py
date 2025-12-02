# app/schemas/bid.py
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class BidCreate(BaseModel):
    """Request schema for submitting a bid"""
    session_id: UUID = Field(..., description="Bidding session ID")
    price: float = Field(..., gt=0, description="Bid price (must be positive)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "price": 250.0
            }
        }


class BidResponse(BaseModel):
    """Response schema after submitting a bid"""
    status: str = Field(..., description="Bid status (accepted/rejected)")
    score: float = Field(..., description="Calculated bid score")
    rank: Optional[int] = Field(None, description="Current rank in leaderboard")
    current_price: float = Field(..., description="Bid price")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "score": 1125.50,
                "rank": 3,
                "current_price": 250.0,
                "message": "Bid submitted successfully"
            }
        }


class LeaderboardEntry(BaseModel):
    """Single entry in the leaderboard"""
    user_id: str = Field(..., description="User UUID")
    username: str = Field(..., description="Username")
    price: float = Field(..., description="Bid price")
    score: float = Field(..., description="Bid score")
    rank: int = Field(..., description="Current rank (1 = first place)")
    is_winner: bool = Field(..., description="Whether user is in top K (winners)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "user1",
                "price": 350.0,
                "score": 1177.40,
                "rank": 1,
                "is_winner": True
            }
        }


class LeaderboardResponse(BaseModel):
    """Response schema for leaderboard"""
    session_id: str = Field(..., description="Bidding session ID")
    leaderboard: List[LeaderboardEntry] = Field(..., description="List of top bidders")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "leaderboard": [
                    {
                        "user_id": "user-uuid-1",
                        "username": "user1",
                        "price": 350.0,
                        "score": 1177.40,
                        "rank": 1,
                        "is_winner": True
                    }
                ]
            }
        }


class SessionInfo(BaseModel):
    """Information about a bidding session"""
    session_id: UUID
    product_id: UUID
    name: str
    description: Optional[str]
    base_price: float
    inventory: int
    alpha: float
    beta: float
    gamma: float
    start_time: datetime
    end_time: datetime
    status: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session-uuid",
                "product_id": "product-uuid",
                "name": "Limited Edition Sneakers",
                "description": "Nike Air Jordan 1",
                "base_price": 200.0,
                "inventory": 5,
                "alpha": 0.5,
                "beta": 1000.0,
                "gamma": 2.0,
                "start_time": "2024-12-02T10:00:00",
                "end_time": "2024-12-02T11:00:00",
                "status": "active"
            }
        }