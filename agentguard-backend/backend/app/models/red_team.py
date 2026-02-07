"""Red team run and finding models for adversarial testing."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class RedTeamRun(TimestampMixin, Base):
    __tablename__ = "red_team_runs"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    test_categories = Column(JSONB, nullable=False, server_default="[]")  # e.g. ["injection", "extraction", "pii_leakage"]
    total_tests = Column(Integer, nullable=False, server_default="0")
    passed_tests = Column(Integer, nullable=False, server_default="0")
    failed_tests = Column(Integer, nullable=False, server_default="0")
    resilience_score = Column(Float, nullable=True)  # 0-100 percentage
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="red_team_runs")
    endpoint = relationship("ProxyEndpoint")
    findings = relationship("RedTeamFinding", back_populates="run", order_by="RedTeamFinding.created_at")

    __table_args__ = (
        Index("ix_red_team_runs_org_status", "org_id", "status"),
        Index("ix_red_team_runs_org_created", "org_id", "created_at"),
    )


class RedTeamFinding(TimestampMixin, Base):
    __tablename__ = "red_team_findings"

    run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("red_team_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_category = Column(String(50), nullable=False)
    test_name = Column(String(255), nullable=False)
    passed = Column(Boolean, nullable=False, default=True)
    severity = Column(String(20), nullable=False, default="info")
    attack_prompt = Column(Text, nullable=True)
    model_response = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    details = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    run = relationship("RedTeamRun", back_populates="findings")

    __table_args__ = (
        Index("ix_red_team_findings_run_category", "run_id", "test_category"),
    )
