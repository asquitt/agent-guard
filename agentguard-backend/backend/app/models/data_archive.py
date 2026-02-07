"""Data archive metadata model — tracks archived data exports."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.base import TimestampMixin


class DataArchive(TimestampMixin, Base):
    __tablename__ = "data_archives"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String, nullable=False)
    row_count = Column(Integer, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    status = Column(String, nullable=False, default="completed")
    error_message = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_data_archives_org_table", "org_id", "table_name"),
        Index("ix_data_archives_org_dates", "org_id", "start_date", "end_date"),
    )
