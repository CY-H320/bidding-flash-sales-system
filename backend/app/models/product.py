from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.bid import BiddingSession


class BiddingProduct(Base):
    """BiddingProduct ORM model"""

    __tablename__ = "bidding_products"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    admin_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    admin: Mapped["User"] = relationship("User", back_populates="products")
    sessions: Mapped[list["BiddingSession"]] = relationship(
        "BiddingSession", back_populates="product"
    )

    def __repr__(self) -> str:
        return f"<BiddingProduct(id={self.id}, name={self.name})>"
