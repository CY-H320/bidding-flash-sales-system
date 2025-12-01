import asyncio
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bid import BiddingSession
from app.models.user import User


async def check_session_active(
    redis: Redis,
    session_id: UUID,
    db: AsyncSession,
) -> tuple[bool, str | None]:
    """Check if bidding session exists and is active."""
    cache_key = f"session:params:{session_id}"

    cached = await redis.hgetall(cache_key)

    if cached and "start_time" in cached and "end_time" in cached:
        try:
            start_time = datetime.fromisoformat(cached["start_time"])
            end_time = datetime.fromisoformat(cached["end_time"])
            now = datetime.utcnow()
            if now < start_time:
                return False, "Bidding session has not started yet"
            elif now > end_time:
                return False, "Bidding session has ended"
            else:
                return True, None

        except (KeyError, ValueError):
            pass

    result = await db.execute(
        select(
            BiddingSession.start_time, BiddingSession.end_time, BiddingSession.is_active
        ).where(BiddingSession.id == session_id)
    )
    row = result.first()

    if not row:
        return False, "Bidding session not found"

    start_time, end_time, is_active = row

    if not is_active:
        return False, "Bidding session is not active"

    now = datetime.utcnow()
    if now < start_time:
        return False, "Bidding session has not started yet"
    elif now > end_time:
        return False, "Bidding session has ended"

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
    bid_timestamp = datetime.utcnow()

    # Fetch session parameters and user weight in parallel
    (alpha, beta, gamma, start_time), weight = await asyncio.gather(
        get_session_params_from_cache(redis, session_id, db),
        get_user_weight_from_cache(redis, user_id, db),
    )

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
