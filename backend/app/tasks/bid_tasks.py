from Celery import app
from app.core.database import engine
from app.models.bid import BiddingSessionBid
from uuid import UUID
from datetime import datetime


@app.task
def save_bid_to_db(
    self,
    session_id: UUID,
    user_id: UUID,
    bid_price: float,
    bid_score: float,
    timestamp: datetime,
):
    """Save bid to database"""
    bid_session = BiddingSessionBid(
        session_id=session_id,
        user_id=user_id,
        bid_price=bid_price,
        bid_score=bid_score,
        created_at=timestamp,
        updated_at=timestamp,
    )
    engine.add(bid_session)
    engine.commit()
