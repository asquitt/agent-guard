"""Per-organization data retention policy model."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.base import TimestampMixin


class RetentionPolicy(TimestampMixin, Base):
    __tablename__ = "retention_policies"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    proxy_requests_days = Column(Integer, nullable=False, default=30)
    incidents_days = Column(Integer, nullable=False, default=365)
    audit_logs_days = Column(Integer, nullable=False, default=365)
