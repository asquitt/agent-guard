"""StripeEvent model for webhook idempotency tracking."""

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.base import TimestampMixin


class StripeEvent(TimestampMixin, Base):
    __tablename__ = "stripe_events"

    stripe_event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
