from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.bid import BiddingSession, BiddingSessionBid, BiddingSessionRanking
    from app.models.product import BiddingProduct


from sqlalchemy.sql import func


class User(Base):
    """User ORM model"""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # bidding parameters - only for members
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    products: Mapped[list["BiddingProduct"]] = relationship(
        "BiddingProduct", back_populates="admin"
    )
    sessions: Mapped[list["BiddingSession"]] = relationship(
        "BiddingSession", back_populates="admin"
    )
    rankings: Mapped[list["BiddingSessionRanking"]] = relationship(
        "BiddingSessionRanking", back_populates="user"
    )
    bids: Mapped[list["BiddingSessionBid"]] = relationship(
        "BiddingSessionBid", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
