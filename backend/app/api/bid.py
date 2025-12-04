# app/api/bid.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from typing import List
from uuid import UUID
from sqlalchemy import select

# Use your teammate's existing imports
from app.core.database import get_async_db
from app.core.redis import get_redis
from app.services.bidding_service import (
    check_session_active,
    process_new_bid,
)
from app.schemas.bid import (
    BidCreate,
    BidResponse,
    LeaderboardResponse,
    LeaderboardEntry,
)
from app.models.user import User
from app.models.bid import BiddingSession, BiddingSessionBid
from app.models.product import BiddingProduct
from app.api.auth import get_current_user

# Import WebSocket broadcast function
try:
    from app.api.websocket import broadcast_leaderboard_update
    has_websocket = True
except ImportError:
    has_websocket = False

router = APIRouter()


@router.post("/bid", response_model=BidResponse)
async def submit_bid(
    bid_data: BidCreate,
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_async_db),
):
    """Submit or update a bid"""
    
    # Check if session is active
    is_active, error_message = await check_session_active(
        redis=redis,
        session_id=bid_data.session_id,
        db=db
    )
    
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Get upset_price
    result = await db.execute(
        select(BiddingSession.upset_price).where(
            BiddingSession.id == bid_data.session_id
        )
    )
    upset_price = result.scalar_one_or_none()
    
    if upset_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if bid_data.price < upset_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid must be at least ${upset_price}"
        )
    
    # Process bid using your teammate's service
    try:
        result = await process_new_bid(
            user_id=current_user.id,
            session_id=bid_data.session_id,
            bid_price=bid_data.price,
            redis=redis,
            db=db,
        )
        
        # Store in database
        bid_result = await db.execute(
            select(BiddingSessionBid).where(
                BiddingSessionBid.session_id == bid_data.session_id,
                BiddingSessionBid.user_id == current_user.id
            )
        )
        existing_bid = bid_result.scalar_one_or_none()
        
        if existing_bid:
            existing_bid.bid_price = bid_data.price
            existing_bid.bid_score = result["score"]
        else:
            new_bid = BiddingSessionBid(
                session_id=bid_data.session_id,
                user_id=current_user.id,
                bid_price=bid_data.price,
                bid_score=result["score"]
            )
            db.add(new_bid)
        
        await db.commit()

        # Broadcast leaderboard update via WebSocket
        if has_websocket:
            try:
                await broadcast_leaderboard_update(str(bid_data.session_id), redis, db)
            except Exception as ws_error:
                print(f"WebSocket broadcast error: {ws_error}")

        return BidResponse(
            status="accepted",
            score=round(result["score"], 2),
            rank=result["rank"],
            current_price=bid_data.price,
            message="Bid submitted successfully"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/leaderboard/{session_id}", response_model=LeaderboardResponse)
async def get_leaderboard(
    session_id: UUID,
    limit: int = 10,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_async_db),
):
    """Get leaderboard from Redis"""
    
    ranking_key = f"ranking:{session_id}"
    
    top_bidders = await redis.zrevrange(
        ranking_key,
        0,
        limit - 1,
        withscores=True
    )
    
    if not top_bidders:
        return LeaderboardResponse(
            session_id=str(session_id),
            leaderboard=[]
        )
    
    result = await db.execute(
        select(BiddingSession.inventory).where(
            BiddingSession.id == session_id
        )
    )
    inventory = result.scalar_one_or_none()
    
    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    leaderboard = []
    
    for rank, (user_id_str, score) in enumerate(top_bidders, start=1):
        user_id = UUID(user_id_str)
        
        user_result = await db.execute(
            select(User.username).where(User.id == user_id)
        )
        username = user_result.scalar_one_or_none()
        
        bid_key = f"bid:{session_id}:{user_id}"
        bid_data = await redis.hgetall(bid_key)
        
        price = float(bid_data.get("price", 0)) if bid_data else 0
        
        leaderboard.append(
            LeaderboardEntry(
                user_id=str(user_id),
                username=username or f"User {user_id}",
                price=price,
                score=round(score, 2),
                rank=rank,
                is_winner=(rank <= inventory)
            )
        )
    
    return LeaderboardResponse(
        session_id=str(session_id),
        leaderboard=leaderboard
    )


@router.get("/sessions/active")
async def get_active_sessions(
    db: AsyncSession = Depends(get_async_db),
):
    """Get all active sessions for frontend"""
    
    result = await db.execute(
        select(
            BiddingSession.id.label("session_id"),
            BiddingProduct.id.label("product_id"),
            BiddingProduct.name,
            BiddingProduct.description,
            BiddingSession.upset_price,
            BiddingSession.inventory,
            BiddingSession.alpha,
            BiddingSession.beta,
            BiddingSession.gamma,
            BiddingSession.start_time,
            BiddingSession.end_time,
            BiddingSession.is_active,
        )
        .join(BiddingProduct, BiddingSession.product_id == BiddingProduct.id)
        .where(BiddingSession.is_active == True)
    )
    
    sessions = []
    for row in result:
        sessions.append({
            "session_id": str(row.session_id),
            "product_id": str(row.product_id),
            "name": row.name,
            "description": row.description,
            "base_price": row.upset_price,
            "inventory": row.inventory,
            "alpha": row.alpha,
            "beta": row.beta,
            "gamma": row.gamma,
            "start_time": row.start_time.isoformat(),
            "end_time": row.end_time.isoformat(),
            "status": "active"
        })
    
    return sessions