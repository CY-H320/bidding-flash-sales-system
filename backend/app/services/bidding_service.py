import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
from app.models.bid import BiddingSession, BiddingSessionBid, BiddingSessionRanking
from app.models.user import User
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_session_active(
    redis: Redis,
    session_id: UUID,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """Check if bidding session exists and is active."""
    # ✅ Check Redis cache first to avoid DB query on every bid
    cache_key = f"session:active:{session_id}"
    cached_status = await redis.get(cache_key)

    if cached_status:
        if cached_status == "active":
            return True, None
        else:
            # Cached error message
            return False, cached_status

    # Cache miss - query database
    result = await db.execute(
        select(
            BiddingSession.start_time, BiddingSession.end_time, BiddingSession.is_active
        ).where(BiddingSession.id == session_id)
    )
    row = result.first()

    if not row:
        # Cache the error for 60 seconds
        await redis.set(cache_key, "Bidding session not found", ex=60)
        return False, "Bidding session not found"

    start_time, end_time, is_active = row

    if not is_active:
        # Cache inactive status for 60 seconds
        await redis.set(cache_key, "Bidding session is not active", ex=60)
        return False, "Bidding session is not active"

    # Ensure both times are timezone-aware UTC
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)

    # Always use UTC for comparison
    now = datetime.now(timezone.utc)

    if now < start_time:
        # Cache "not started" for 30 seconds (might start soon)
        await redis.set(cache_key, "Bidding session has not started yet", ex=30)
        return False, "Bidding session has not started yet"
    elif now > end_time:
        # Cache "ended" for 5 minutes (won't change)
        await redis.set(cache_key, "Bidding session has ended", ex=300)
        return False, "Bidding session has ended"

    # ✅ Active session - cache for 10 seconds
    await redis.set(cache_key, "active", ex=10)
    return True, None


async def get_session_params_from_cache(
    redis: Redis,
    session_id: UUID,
    db: AsyncSession,
) -> tuple[float, float, float, datetime]:
    """Get session parameters from cache or DB."""
    cache_key = f"session:params:{session_id}"

    cached = await redis.hgetall(cache_key)

    if cached and len(cached) >= 4:
        return (
            float(cached["alpha"]),
            float(cached["beta"]),
            float(cached["gamma"]),
            datetime.fromisoformat(cached["start_time"]),
        )

    result = await db.execute(
        select(
            BiddingSession.alpha,
            BiddingSession.beta,
            BiddingSession.gamma,
            BiddingSession.start_time,
            BiddingSession.end_time,
        ).where(BiddingSession.id == session_id)
    )
    row = result.first()

    if not row:
        raise ValueError(f"Session {session_id} not found")

    alpha, beta, gamma, start_time, end_time = row

    await redis.hset(
        cache_key,
        mapping={
            "alpha": str(alpha),
            "beta": str(beta),
            "gamma": str(gamma),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )
    await redis.expire(cache_key, settings.REDIS_CACHE_EXPIRE)

    return alpha, beta, gamma, start_time


async def get_user_weight_from_cache(
    redis: Redis,
    user_id: UUID,
    db: AsyncSession,
) -> float:
    """Get user weight from cache or DB."""
    cache_key = f"user:weight:{user_id}"

    cached_weight = await redis.get(cache_key)

    if cached_weight:
        return float(cached_weight)

    result = await db.execute(select(User.weight).where(User.id == user_id))
    weight = result.scalar_one_or_none()

    if weight is None:
        raise ValueError(f"User {user_id} not found")

    await redis.set(cache_key, str(weight), ex=settings.REDIS_CACHE_EXPIRE)

    return weight


def calculate_bid_score(
    price: float,
    response_time_seconds: float,
    weight: float,
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """Calculate bid score: α * P + β / (T + 1) + γ * W"""
    score = alpha * price + beta / (response_time_seconds + 1) + gamma * weight
    return score


async def process_new_bid(
    user_id: UUID,
    session_id: UUID,
    bid_price: float,
    redis: Redis,
    db: AsyncSession,
) -> dict:
    """Process a new bid: calculate score and store in Redis ZSET."""
    # Use UTC time for consistency
    bid_timestamp = datetime.now(timezone.utc)

    # Fetch session parameters and user weight in parallel
    (alpha, beta, gamma, start_time), weight = await asyncio.gather(
        get_session_params_from_cache(redis, session_id, db),
        get_user_weight_from_cache(redis, user_id, db),
    )

    # Ensure both timestamps are timezone-aware UTC for subtraction
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    response_time = (bid_timestamp - start_time).total_seconds()

    score = calculate_bid_score(
        price=bid_price,
        response_time_seconds=response_time,
        weight=weight,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
    )

    ranking_key = f"ranking:{session_id}"
    bid_key = f"bid:{session_id}:{user_id}"

    pipe = redis.pipeline()
    pipe.zadd(ranking_key, {str(user_id): score})
    pipe.hset(
        bid_key,
        mapping={
            "price": str(bid_price),
            "score": str(score),
            "response_time": str(response_time),
            "timestamp": bid_timestamp.isoformat(),
        },
    )
    pipe.expire(ranking_key, settings.REDIS_CACHE_EXPIRE)
    pipe.expire(bid_key, settings.REDIS_CACHE_EXPIRE)
    await pipe.execute()

    rank = await redis.zrevrank(ranking_key, str(user_id))
    rank = rank + 1 if rank is not None else None

    return {
        "score": score,
        "rank": rank,
        "response_time": response_time,
        "timestamp": bid_timestamp.isoformat(),
    }


async def finalize_session_results(
    session_id: UUID,
    redis: Redis,
    db: AsyncSession,
) -> dict:
    """
    Finalize session results when bidding ends.
    - Calculates final price based on inventory
    - Saves final rankings and winners to database
    - Updates session.final_price
    """
    # Get session details
    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        return {"status": "error", "message": "Session not found"}

    inventory = session.inventory

    # Get all bids from database sorted by score (descending)
    bid_result = await db.execute(
        select(BiddingSessionBid).where(BiddingSessionBid.session_id == session_id)
    )
    all_bids = bid_result.scalars().all()

    # Sort by score descending
    sorted_bids = sorted(all_bids, key=lambda b: b.bid_score, reverse=True)

    # Determine winners and final price
    final_price = None
    if sorted_bids:
        # Final price is the Kth (inventory) bid's price
        # If fewer bids than inventory, use the lowest bid price
        if len(sorted_bids) >= inventory:
            final_price = sorted_bids[inventory - 1].bid_price
        else:
            final_price = sorted_bids[-1].bid_price

    # Clear old rankings for this session (if any)
    delete_result = await db.execute(
        select(BiddingSessionRanking).where(
            BiddingSessionRanking.session_id == session_id
        )
    )
    for ranking in delete_result.scalars().all():
        await db.delete(ranking)

    # Create final ranking records
    now = datetime.now(timezone.utc)
    winners_count = 0

    for rank, bid in enumerate(sorted_bids, start=1):
        is_winner = rank <= inventory
        if is_winner:
            winners_count += 1

        ranking_record = BiddingSessionRanking(
            session_id=session_id,
            user_id=bid.user_id,
            ranking=rank,
            bid_price=bid.bid_price,
            bid_score=bid.bid_score,
            is_winner=is_winner,
            created_at=now,
            updated_at=now,
        )
        db.add(ranking_record)

    # Update session with final price
    session.final_price = final_price
    session.updated_at = now

    await db.commit()

    return {
        "status": "success",
        "final_price": final_price,
        "total_bidders": len(sorted_bids),
        "winners_count": winners_count,
        "rankings_saved": len(sorted_bids),
    }
