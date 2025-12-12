# app/tasks/batch_persist.py
"""Background task for batch persisting bids from Redis to PostgreSQL."""

import asyncio
import traceback
from datetime import datetime, timezone
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.models.bid import BiddingSessionBid
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


def _safe_decode(value) -> str:
    """
    Safely decode value regardless of whether it's bytes or str.

    Args:
        value: Value to decode (bytes or str)

    Returns:
        Decoded string
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


async def _persist_session_bids(
    session_id: UUID,
    bid_keys: list,
    redis: Redis,
    db: AsyncSession,
) -> int:
    """
    Persist all bids for a session using batch UPSERT.

    Returns:
        Number of bids persisted
    """
    if not bid_keys:
        return 0

    # Fetch all bid metadata
    bid_values = []

    for key in bid_keys:
        metadata = await redis.hgetall(key)
        if not metadata:
            continue

        try:
            # Get values with flexible key access (bytes or str)
            user_id = metadata.get(b"user_id") or metadata.get("user_id")
            bid_price = metadata.get(b"bid_price") or metadata.get("bid_price")
            bid_score = metadata.get(b"bid_score") or metadata.get("bid_score")
            updated_at = metadata.get(b"updated_at") or metadata.get("updated_at")

            bid_values.append(
                {
                    "session_id": session_id,
                    "user_id": UUID(_safe_decode(user_id)),
                    "bid_price": float(_safe_decode(bid_price)),
                    "bid_score": float(_safe_decode(bid_score)),
                    "created_at": datetime.now(timezone.utc),  # First insert
                    "updated_at": datetime.fromisoformat(_safe_decode(updated_at)),
                }
            )
        except Exception as e:
            print(f"⚠️  Skipping invalid bid metadata: {e}")
            continue

    if not bid_values:
        return 0

    # Batch UPSERT to PostgreSQL
    try:
        stmt = insert(BiddingSessionBid).values(bid_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["session_id", "user_id"],
            set_={
                "bid_price": stmt.excluded.bid_price,
                "bid_score": stmt.excluded.bid_score,
                "updated_at": stmt.excluded.updated_at,
            },
        )

        await db.execute(stmt)
        await db.commit()

        return len(bid_values)

    except Exception as e:
        await db.rollback()
        print(f"❌ Database error persisting {len(bid_values)} bids: {e}")
        raise


async def force_persist_session(
    session_id: UUID,
    redis: Redis,
    db: AsyncSession,
) -> int:
    """
    Force immediate persistence of all bids for a session.
    Used when session ends to ensure data integrity.

    Returns:
        Number of bids persisted
    """
    pattern = f"bid_metadata:{session_id}:*"
    cursor = 0
    bid_keys = []

    # Scan for all bid metadata keys
    while True:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
        bid_keys.extend(keys)
        if cursor == 0:
            break

    if not bid_keys:
        return 0

    # Persist all bids
    persisted_count = await _persist_session_bids(
        session_id=session_id,
        bid_keys=bid_keys,
        redis=redis,
        db=db,
    )

    # Clean up
    await redis.delete(*bid_keys)
    await redis.srem("dirty_sessions", str(session_id))

    print(f"🔒 Force persisted {persisted_count} bids for session {session_id}")

    return persisted_count


async def start_batch_persist_background_task(batch_interval: int = 5):
    """
    Start the batch persist background task.
    Should be called on application startup.

    Args:
        batch_interval: Seconds between batch operations (default: 5)
    """
    redis = redis_client.get_client()

    print(f"🚀 Batch persist task started (interval: {batch_interval}s)")

    while True:
        try:
            await asyncio.sleep(batch_interval)

            # Create a new DB session for each batch operation
            async with AsyncSessionLocal() as db:
                # Get all sessions with dirty (unpersisted) bids
                dirty_sessions_key = "dirty_sessions"
                dirty_sessions = await redis.smembers(dirty_sessions_key)

                if not dirty_sessions:
                    continue

                total_persisted = 0

                for session_id_bytes in dirty_sessions:
                    session_id = _safe_decode(session_id_bytes)

                    try:
                        # Get all bid metadata for this session
                        pattern = f"bid_metadata:{session_id}:*"
                        cursor = 0
                        bid_keys = []

                        # Scan for all bid metadata keys
                        while True:
                            cursor, keys = await redis.scan(
                                cursor=cursor, match=pattern, count=100
                            )
                            bid_keys.extend(keys)
                            if cursor == 0:
                                break

                        if not bid_keys:
                            # No bids to persist, remove from dirty set
                            await redis.srem(dirty_sessions_key, session_id)
                            continue

                        # Batch persist all bids for this session
                        persisted_count = await _persist_session_bids(
                            session_id=UUID(session_id),
                            bid_keys=bid_keys,
                            redis=redis,
                            db=db,
                        )

                        total_persisted += persisted_count

                        # Remove session from dirty set
                        await redis.srem(dirty_sessions_key, session_id)

                        # Clean up bid metadata keys after successful persistence
                        if bid_keys:
                            await redis.delete(*bid_keys)

                    except Exception as e:
                        print(f"❌ Error persisting session {session_id}: {e}")
                        print(f"📋 Traceback:\n{traceback.format_exc()}")
                        continue

                if total_persisted > 0:
                    print(
                        f"✅ Batch persisted {total_persisted} bids across {len(dirty_sessions)} sessions"
                    )

        except asyncio.TimeoutError:
            print("⚠️  Database connection timeout in batch persist, waiting 10 seconds")
            await asyncio.sleep(10)  # Wait longer for database to recover
        except Exception as e:
            error_msg = str(e)
            if (
                "QueuePool limit" in error_msg
                or "connection timed out" in error_msg
                or "TimeoutError" in error_msg
                or "too many clients" in error_msg
            ):
                print(f"⚠️  Connection pool exhausted, waiting 10 seconds: {e}")
                await asyncio.sleep(10)  # Wait longer if pool is exhausted
            else:
                print(f"❌ Error in batch persist task: {e}")
                print(f"📋 Traceback:\n{traceback.format_exc()}")
                await asyncio.sleep(5)  # Avoid tight loop on error
