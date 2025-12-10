# app/tasks/session_monitor.py
"""Background task to monitor session status and broadcast updates."""

import asyncio
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.models.bid import BiddingSession
from app.services.bidding_service import finalize_session_results
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def check_and_update_session_status(db: AsyncSession) -> list[str]:
    """
    Check all active sessions and update their status based on current time.
    Returns list of session IDs that changed status.
    """
    now = datetime.now(timezone.utc)
    changed_sessions = []

    # Find sessions that should be deactivated (past end_time)
    result = await db.execute(
        select(BiddingSession).where(
            BiddingSession.is_active == True,  # noqa: E712
            BiddingSession.end_time <= now,
        )
    )
    expired_sessions = result.scalars().all()

    # Get Redis connection
    redis = redis_client.get_client()

    for session in expired_sessions:
        try:
            # Force persist all unpersisted bids before finalizing
            from app.tasks.batch_persist import force_persist_session

            persisted_count = await force_persist_session(
                session_id=session.id,
                redis=redis,
                db=db,
            )
            if persisted_count > 0:
                print(
                    f"🔒 Force persisted {persisted_count} bids for session {session.id}"
                )

            # Finalize session results (calculate winners, final price, save rankings)
            finalize_result = await finalize_session_results(
                session_id=session.id, redis=redis, db=db
            )
            print(f"✓ Session {session.id} finalized: {finalize_result}")
        except Exception as e:
            print(f"❌ Error finalizing session {session.id}: {e}")

        session.is_active = False
        changed_sessions.append(str(session.id))
        print(f"✓ Session {session.id} automatically ended at {now}")

    if changed_sessions:
        await db.commit()

    return changed_sessions


async def session_monitor_task():
    """
    Background task that periodically checks session status and broadcasts updates.
    Runs every 10 seconds.
    """
    print("✓ Session monitor task started")

    while True:
        try:
            async with AsyncSessionLocal() as db:
                changed_sessions = await check_and_update_session_status(db)

                if changed_sessions:
                    # Broadcast session list update (creates its own DB session)
                    try:
                        from app.api.websocket import broadcast_session_list_update

                        await broadcast_session_list_update()
                        print(
                            f"✓ Broadcasted session updates for {len(changed_sessions)} sessions"
                        )
                    except Exception as e:
                        print(f"❌ Error broadcasting session updates: {e}")

        except Exception as e:
            error_msg = str(e)
            if "QueuePool limit" in error_msg or "connection timed out" in error_msg:
                print(
                    f"⚠️  Connection pool exhausted in session monitor, waiting 15 seconds: {e}"
                )
                await asyncio.sleep(15)  # Wait longer if pool is exhausted
            else:
                print(f"❌ Error in session monitor task: {e}")
                await asyncio.sleep(10)  # Normal wait
        else:
            # Wait 10 seconds before next check (normal operation)
            await asyncio.sleep(10)
