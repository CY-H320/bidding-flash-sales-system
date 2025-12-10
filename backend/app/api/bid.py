# app/api/bid.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user

# Use your teammate's existing imports
from app.core.database import get_async_db
from app.core.redis import get_redis
from app.models.bid import BiddingSession, BiddingSessionBid
from app.models.product import BiddingProduct
from app.models.user import User
from app.schemas.bid import (
    BidCreate,
    BidResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)
from app.services.bidding_service import (
    check_session_active,
    process_new_bid,
)

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
        redis=redis, session_id=bid_data.session_id, db=db
    )

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
        )

    # Get upset_price from Redis cache (performance optimization)
    cache_key = f"session:upset_price:{bid_data.session_id}"
    cached_upset_price = await redis.get(cache_key)

    if cached_upset_price:
        upset_price = float(cached_upset_price)
    else:
        result = await db.execute(
            select(BiddingSession.upset_price).where(
                BiddingSession.id == bid_data.session_id
            )
        )
        upset_price = result.scalar_one_or_none()
        if upset_price:
            # Cache for 2 hours
            await redis.set(cache_key, str(upset_price), ex=7200)

    if upset_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if bid_data.price < upset_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bid must be at least ${upset_price}",
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

        # ⚡ HIGH PERFORMANCE: Defer PostgreSQL write to batch task
        # Mark this session as having dirty (unpersisted) data
        # Background task will batch persist every 5-10 seconds
        dirty_sessions_key = "dirty_sessions"
        await redis.sadd(dirty_sessions_key, str(bid_data.session_id))

        # Store bid metadata in Redis for batch persistence
        # This allows the background task to reconstruct the UPSERT
        bid_metadata_key = f"bid_metadata:{bid_data.session_id}:{current_user.id}"
        await redis.hset(
            bid_metadata_key,
            mapping={
                "user_id": str(current_user.id),
                "bid_price": str(bid_data.price),
                "bid_score": str(result["score"]),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        # Expire after 1 hour (safety cleanup)
        await redis.expire(bid_metadata_key, 3600)

        # WebSocket broadcast DISABLED for performance
        # Broadcasting on every bid causes leaderboard glitching
        # Clients should poll leaderboard or use a background task
        # if has_websocket:
        #     try:
        #         await broadcast_leaderboard_update(str(bid_data.session_id), redis, db)
        #     except Exception as ws_error:
        #         pass

        return BidResponse(
            status="accepted",
            score=round(result["score"], 2),
            rank=result["rank"],
            current_price=bid_data.price,
            message="Bid submitted successfully",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/leaderboard/{session_id}", response_model=LeaderboardResponse)
async def get_leaderboard(
    session_id: UUID,
    page: int = 1,
    page_size: int = 50,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_async_db),
):
    """Get leaderboard from Redis with pagination (50 per page)"""

    # Validate page parameters
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 50

    ranking_key = f"ranking:{session_id}"

    # Get total count of bidders
    total_count = await redis.zcard(ranking_key)

    if total_count == 0:
        # Fallback to DB if Redis is empty
        count_result = await db.execute(
            select(BiddingSessionBid).where(BiddingSessionBid.session_id == session_id)
        )
        total_count = len(count_result.all())

        if total_count == 0:
            total_pages = 1
            return LeaderboardResponse(
                session_id=str(session_id),
                leaderboard=[],
                highest_bid=None,
                threshold_score=None,
                page=page,
                page_size=page_size,
                total_count=0,
                total_pages=0,
            )

        # Calculate pagination from DB
        offset = (page - 1) * page_size
        result = await db.execute(
            select(BiddingSessionBid, User.username)
            .join(User, BiddingSessionBid.user_id == User.id)
            .where(BiddingSessionBid.session_id == session_id)
            .order_by(BiddingSessionBid.bid_score.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = result.all()

        # Get inventory for winner calculation
        inv_result = await db.execute(
            select(BiddingSession.inventory).where(BiddingSession.id == session_id)
        )
        inventory = inv_result.scalar_one_or_none() or 0

        leaderboard = []
        for rank, (bid, username) in enumerate(rows, start=offset + 1):
            leaderboard.append(
                LeaderboardEntry(
                    user_id=str(bid.user_id),
                    username=username,
                    price=bid.bid_price,
                    score=round(bid.bid_score, 2),
                    rank=rank,
                    is_winner=(rank <= inventory),
                )
            )

        # Calculate highest bid and threshold score (always from all bidders, not just page)
        all_bids_result = await db.execute(
            select(BiddingSessionBid)
            .where(BiddingSessionBid.session_id == session_id)
            .order_by(BiddingSessionBid.bid_score.desc())
        )
        all_bids = all_bids_result.scalars().all()
        highest_bid = max([bid.bid_price for bid in all_bids]) if all_bids else None
        if len(all_bids) < inventory:
            threshold_score = all_bids[-1].bid_score if all_bids else None
        else:
            threshold_score = all_bids[inventory - 1].bid_score

        total_pages = (total_count + page_size - 1) // page_size

        return LeaderboardResponse(
            session_id=str(session_id),
            leaderboard=leaderboard,
            highest_bid=highest_bid,
            threshold_score=round(threshold_score, 2) if threshold_score else None,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    # Use Redis for pagination
    # Calculate offset and fetch data for this page
    offset = (page - 1) * page_size
    top_bidders = await redis.zrevrange(
        ranking_key, offset, offset + page_size - 1, withscores=True
    )

    result = await db.execute(
        select(BiddingSession.inventory).where(BiddingSession.id == session_id)
    )
    inventory = result.scalar_one_or_none()

    if inventory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # ✅ FIX: Fetch all usernames in a single query (eliminates N+1 problem)
    user_ids = [UUID(user_id_str) for user_id_str, _ in top_bidders]

    if user_ids:
        user_result = await db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        user_map = {row.id: row.username for row in user_result}
    else:
        user_map = {}

    leaderboard = []

    for rank, (user_id_str, score) in enumerate(top_bidders, start=offset + 1):
        user_id = UUID(user_id_str)

        # ✅ Get username from pre-fetched map instead of individual query
        username = user_map.get(user_id, f"User {user_id}")

        bid_key = f"bid:{session_id}:{user_id}"
        bid_data = await redis.hgetall(bid_key)

        price = float(bid_data.get("price", 0)) if bid_data else 0

        leaderboard.append(
            LeaderboardEntry(
                user_id=str(user_id),
                username=username,
                price=price,
                score=round(score, 2),
                rank=rank,
                is_winner=(rank <= inventory),
            )
        )

    # Calculate highest bid and threshold score (from full ranking, not just page)
    # Get top entries to find highest bid and threshold
    all_top_bidders = await redis.zrevrange(ranking_key, 0, -1, withscores=True)
    highest_bid = None
    threshold_score = None

    if all_top_bidders:
        highest_bid_entry = all_top_bidders[0]
        user_id_str = highest_bid_entry[0]
        bid_key = f"bid:{session_id}:{user_id_str}"
        bid_data = await redis.hgetall(bid_key)
        highest_bid = float(bid_data.get("price", 0)) if bid_data else None

        # Threshold score: if fewer bidders than inventory, use last bidder; else use Kth
        if len(all_top_bidders) < inventory:
            threshold_score = all_top_bidders[-1][1]
        else:
            threshold_score = all_top_bidders[inventory - 1][1]

    total_pages = (total_count + page_size - 1) // page_size

    return LeaderboardResponse(
        session_id=str(session_id),
        leaderboard=leaderboard,
        highest_bid=highest_bid,
        threshold_score=round(threshold_score, 2) if threshold_score else None,
        page=page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
    )


@router.get("/sessions")
async def get_all_sessions_endpoint(
    db: AsyncSession = Depends(get_async_db),
):
    """Get all sessions (active and ended) for frontend"""

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
        .order_by(BiddingSession.start_time.desc())
    )

    sessions = []
    # Use UTC datetime for comparison
    now = datetime.now(timezone.utc)

    for row in result:
        # Determine status based on is_active flag and end_time
        # Ensure timezone-aware for comparison
        end_time = row.end_time
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        is_ended = not row.is_active or now > end_time

        sessions.append(
            {
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
                "is_active": row.is_active,
                "status": "ended" if is_ended else "active",
            }
        )

    return sessions


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
        .where(BiddingSession.is_active)
    )

    sessions = []
    for row in result:
        sessions.append(
            {
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
                "status": "active",
            }
        )

    return sessions


@router.get("/results/{session_id}")
async def get_session_results(
    session_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """Get final results for a completed session"""
    from app.models.bid import BiddingSessionRanking

    # Get session info
    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Get all rankings for this session
    ranking_result = await db.execute(
        select(BiddingSessionRanking)
        .where(BiddingSessionRanking.session_id == session_id)
        .order_by(BiddingSessionRanking.ranking)
    )
    rankings = ranking_result.scalars().all()

    # Get user information for each ranking
    winners = []
    for ranking in rankings:
        user_result = await db.execute(select(User).where(User.id == ranking.user_id))
        user = user_result.scalar_one_or_none()

        entry = {
            "rank": ranking.ranking,
            "user_id": str(ranking.user_id),
            "username": user.username if user else "Unknown",
            "bid_price": ranking.bid_price,
            "bid_score": ranking.bid_score,
            "is_winner": ranking.is_winner,
        }

        if ranking.is_winner:
            winners.append(entry)

    return {
        "session_id": str(session.id),
        "product_id": str(session.product_id),
        "inventory": session.inventory,
        "final_price": session.final_price,
        "is_active": session.is_active,
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "total_bidders": len(rankings),
        "total_winners": len(winners),
        "winners": winners,
        "all_rankings": [
            {
                "rank": r.ranking,
                "user_id": str(r.user_id),
                "bid_price": r.bid_price,
                "bid_score": r.bid_score,
                "is_winner": r.is_winner,
            }
            for r in rankings
        ],
    }
