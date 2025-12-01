"""
Pydantic schemas for bidding operations.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class BidCreateSchema(BaseModel):
    """Schema for creating a new bid"""

    user_id: UUID = Field(..., description="User ID placing the bid")
    session_id: UUID = Field(..., description="Bidding session ID")
    bid_price: float = Field(..., gt=0, description="Bid price (must be positive)")

    model_config = {"from_attributes": True}


class BidResponseSchema(BaseModel):
    """Schema for bid response"""

    user_id: UUID
    session_id: UUID
    bid_price: float
    score: float = Field(..., description="Calculated bid score")
    rank: int | None = Field(None, description="Current rank in the session")
    response_time: float = Field(..., description="Response time in seconds")
    timestamp: str = Field(..., description="Bid timestamp (ISO format)")

    model_config = {"from_attributes": True}
