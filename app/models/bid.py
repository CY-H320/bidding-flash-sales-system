from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Interval
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import BiddingProduct


class BiddingSession(Base):
    """BiddingSession ORM model"""

    __tablename__ = "bidding_sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    admin_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bidding_products.id"), nullable=False
    )

    upset_price: Mapped[float] = mapped_column(Float, nullable=False)
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    inventory: Mapped[int] = mapped_column(Integer, nullable=False)

    # bidding session parameters
    alpha: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    beta: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    gamma: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    duration: Mapped[int] = mapped_column(Interval, nullable=False)  # 競標時長

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    admin: Mapped["User"] = relationship("User", back_populates="sessions")
    product: Mapped["BiddingProduct"] = relationship(
        "BiddingProduct", back_populates="sessions"
    )
    rankings: Mapped[list["BiddingSessionRanking"]] = relationship(
        "BiddingSessionRanking", back_populates="session"
    )

    def __repr__(self) -> str:
        return f"<BiddingSession(id={self.id}, product_id={self.product_id})>"


class BiddingSessionBid(Base):
    """BiddingSessionBid ORM model"""

    __tablename__ = "bidding_session_bids"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bidding_sessions.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    bid_price: Mapped[float] = mapped_column(Float, nullable=False)
    bid_score: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    session: Mapped["BiddingSession"] = relationship(
        "BiddingSession", back_populates="bids"
    )
    user: Mapped["User"] = relationship("User", back_populates="bids")

    def __repr__(self) -> str:
        return f"<BiddingSessionBid(id={self.id}, session_id={self.session_id})>"


class BiddingSessionRanking(Base):
    """BiddingSessionRanking ORM model"""

    __tablename__ = "bidding_session_rankings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bidding_sessions.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    ranking: Mapped[int] = mapped_column(Integer, nullable=False)
    bid_price: Mapped[float] = mapped_column(Float, nullable=False)
    bid_score: Mapped[float] = mapped_column(Float, nullable=False)

    is_winner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    session: Mapped["BiddingSession"] = relationship(
        "BiddingSession", back_populates="rankings"
    )
    user: Mapped["User"] = relationship("User", back_populates="rankings")

    def __repr__(self) -> str:
        return f"<BiddingSessionRanking(id={self.id}, ranking={self.ranking})>"
