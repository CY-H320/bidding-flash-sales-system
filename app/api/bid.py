from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.schemas.bid import BidCreateSchema, BidResponseSchema
from app.services.bidding_service import (
    check_session_active,
    process_new_bid,
)

router = APIRouter(prefix="/bid", tags=["Bidding"])


@router.post("/", response_model=BidResponseSchema, status_code=status.HTTP_201_CREATED)
async def place_bid(
    body: BidCreateSchema,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    """Place a new bid in a bidding session."""
    try:
        is_active, error_msg = await check_session_active(redis, body.session_id, db)

        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg
            )

        result = await process_new_bid(
            user_id=body.user_id,
            session_id=body.session_id,
            bid_price=body.bid_price,
            redis=redis,
            db=db,
        )

        return BidResponseSchema(
            user_id=body.user_id,
            session_id=body.session_id,
            bid_price=body.bid_price,
            score=result["score"],
            rank=result["rank"],
            response_time=result["response_time"],
            timestamp=result["timestamp"],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bid: {str(e)}",
        )
