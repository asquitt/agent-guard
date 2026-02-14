"""AI Model Registry — tracks LLM models, provenance, and risk profiles."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class AIModel(Base):
    """Registered AI model with provenance and risk metadata."""

    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity & Provenance
    model_name = Column(String(255), nullable=False)
    model_version = Column(String(50), nullable=False, default="latest")
    provider = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False, default="llm")
    license_type = Column(String(100), nullable=True)
    model_hash = Column(String(128), nullable=True)
    repository_url = Column(String(512), nullable=True)
    model_card_url = Column(String(512), nullable=True)
    release_date = Column(DateTime(timezone=True), nullable=True)

    # Architecture
    parameter_count = Column(String(20), nullable=True)
    context_window = Column(Integer, nullable=True)

    # Security & Risk
    risk_level = Column(String(20), nullable=False, default="medium", index=True)
    risk_factors = Column(JSONB, nullable=False, server_default="[]")
    compliance_frameworks = Column(JSONB, nullable=False, server_default="[]")
    known_limitations = Column(JSONB, nullable=False, server_default="[]")
    security_issues = Column(JSONB, nullable=False, server_default="[]")
    pii_handling = Column(String(20), nullable=False, default="strict")

    # Supply Chain
    training_data_sources = Column(JSONB, nullable=False, server_default="[]")
    training_cutoff = Column(String(20), nullable=True)
    model_dependencies = Column(JSONB, nullable=False, server_default="[]")
    capabilities = Column(JSONB, nullable=False, server_default="[]")

    # Governance
    approval_status = Column(String(20), nullable=False, default="pending", index=True)
    approval_notes = Column(String(1000), nullable=True)
    owner_email = Column(String(255), nullable=True)
    is_deprecated = Column(Boolean, nullable=False, default=False)

    # Auto-populated from proxy usage
    total_requests = Column(Integer, nullable=False, default=0)
    total_incidents = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_ai_models_org_provider", "org_id", "provider"),
        Index("ix_ai_models_org_name", "org_id", "model_name"),
        Index("ix_ai_models_org_risk", "org_id", "risk_level"),
        Index("ix_ai_models_org_status", "org_id", "approval_status"),
    )
