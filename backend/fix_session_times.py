"""
Fix session start times that are in the future due to timezone issues.
This script sets all active sessions to start 1 minute ago.
"""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.bid import BiddingSession


async def fix_session_times():
    """Update all active sessions to start 1 minute ago"""
    async with AsyncSessionLocal() as db:
        # Get all active sessions
        result = await db.execute(
            select(BiddingSession).where(BiddingSession.is_active == True)
        )
        sessions = result.scalars().all()

        print(f"Found {len(sessions)} active sessions")

        for session in sessions:
            old_start = session.start_time
            old_end = session.end_time

            # Calculate duration
            if old_start.tzinfo is None:
                old_start = old_start.replace(tzinfo=timezone.utc)
            if old_end.tzinfo is None:
                old_end = old_end.replace(tzinfo=timezone.utc)

            duration = old_end - old_start

            # Set new times: start 1 minute ago, maintain duration
            new_start = datetime.now(timezone.utc) - timedelta(minutes=1)
            new_end = new_start + duration

            session.start_time = new_start
            session.end_time = new_end

            print(f"\nSession {session.id}:")
            print(f"  Old start: {old_start}")
            print(f"  New start: {new_start}")
            print(f"  Old end: {old_end}")
            print(f"  New end: {new_end}")
            print(f"  Duration: {duration}")

        await db.commit()
        print(f"\n✅ Updated {len(sessions)} sessions")


if __name__ == "__main__":
    asyncio.run(fix_session_times())
