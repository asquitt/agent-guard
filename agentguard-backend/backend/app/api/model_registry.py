"""AI Model Registry router — track LLM models, provenance, and risk profiles."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin, require_permission
from app.models.model_registry import AIModel
from app.models.user import Organization, User

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────

class AIModelCreate(BaseModel):
    model_name: str = Field(min_length=1, max_length=255)
    model_version: str = "latest"
    provider: str = Field(min_length=1, max_length=100)
    model_type: str = "llm"
    license_type: str | None = None
    model_hash: str | None = None
    repository_url: str | None = None
    model_card_url: str | None = None
    release_date: str | None = None
    parameter_count: str | None = None
    context_window: int | None = None
    risk_level: str = "medium"
    risk_factors: list[str] = Field(default_factory=list)
    compliance_frameworks: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    pii_handling: str = "strict"
    training_data_sources: list[str] = Field(default_factory=list)
    training_cutoff: str | None = None
    model_dependencies: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    owner_email: str | None = None


class AIModelUpdate(BaseModel):
    model_version: str | None = None
    risk_level: str | None = None
    risk_factors: list[str] | None = None
    compliance_frameworks: list[str] | None = None
    known_limitations: list[str] | None = None
    security_issues: list[str] | None = None
    pii_handling: str | None = None
    approval_status: str | None = None
    approval_notes: str | None = None
    is_deprecated: bool | None = None
    model_card_url: str | None = None
    owner_email: str | None = None
    capabilities: list[str] | None = None


class AIModelResponse(BaseModel):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: UUID
    model_name: str = Field(serialization_alias="modelName")
    model_version: str = Field(serialization_alias="modelVersion")
    provider: str
    model_type: str = Field(serialization_alias="modelType")
    license_type: str | None = Field(serialization_alias="licenseType")
    model_hash: str | None = Field(serialization_alias="modelHash")
    repository_url: str | None = Field(serialization_alias="repositoryUrl")
    model_card_url: str | None = Field(serialization_alias="modelCardUrl")
    release_date: datetime | None = Field(serialization_alias="releaseDate")
    parameter_count: str | None = Field(serialization_alias="parameterCount")
    context_window: int | None = Field(serialization_alias="contextWindow")
    risk_level: str = Field(serialization_alias="riskLevel")
    risk_factors: list[Any] = Field(serialization_alias="riskFactors")
    compliance_frameworks: list[Any] = Field(serialization_alias="complianceFrameworks")
    known_limitations: list[Any] = Field(serialization_alias="knownLimitations")
    security_issues: list[Any] = Field(serialization_alias="securityIssues")
    pii_handling: str = Field(serialization_alias="piiHandling")
    training_data_sources: list[Any] = Field(serialization_alias="trainingDataSources")
    training_cutoff: str | None = Field(serialization_alias="trainingCutoff")
    model_dependencies: list[Any] = Field(serialization_alias="modelDependencies")
    capabilities: list[Any]
    approval_status: str = Field(serialization_alias="approvalStatus")
    approval_notes: str | None = Field(serialization_alias="approvalNotes")
    owner_email: str | None = Field(serialization_alias="ownerEmail")
    is_deprecated: bool = Field(serialization_alias="isDeprecated")
    total_requests: int = Field(serialization_alias="totalRequests")
    total_incidents: int = Field(serialization_alias="totalIncidents")
    last_used_at: datetime | None = Field(serialization_alias="lastUsedAt")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AIModelListResponse(BaseModel):
    items: list[AIModelResponse]
    total: int


class ModelSummary(BaseModel):
    total_models: int = Field(serialization_alias="totalModels")
    approved: int
    pending: int
    deprecated: int
    by_risk_level: dict[str, int] = Field(serialization_alias="byRiskLevel")
    by_provider: dict[str, int] = Field(serialization_alias="byProvider")


# ── Endpoints ───────────────────────────────────────────────────

@router.get("", response_model=AIModelListResponse)
async def list_models(
    provider: str | None = None,
    risk_level: str | None = Query(default=None, alias="riskLevel"),
    approval_status: str | None = Query(default=None, alias="approvalStatus"),
    model_type: str | None = Query(default=None, alias="modelType"),
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(require_permission("compliance:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AIModelListResponse:
    """List registered AI models with filtering."""
    base = select(AIModel).where(AIModel.org_id == org.id)

    if provider:
        base = base.where(AIModel.provider == provider)
    if risk_level:
        base = base.where(AIModel.risk_level == risk_level)
    if approval_status:
        base = base.where(AIModel.approval_status == approval_status)
    if model_type:
        base = base.where(AIModel.model_type == model_type)
    if q:
        base = base.where(AIModel.model_name.ilike(f"%{q}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        base.order_by(AIModel.updated_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return AIModelListResponse(
        items=[AIModelResponse.model_validate(m) for m in items],
        total=total,
    )


@router.get("/summary", response_model=ModelSummary)
async def get_model_summary(
    _user: User = Depends(require_permission("compliance:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ModelSummary:
    """Get summary statistics for registered models."""
    base = select(AIModel).where(AIModel.org_id == org.id)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    approved = (await db.execute(
        select(func.count()).select_from(
            base.where(AIModel.approval_status == "approved").subquery()
        )
    )).scalar_one()

    pending = (await db.execute(
        select(func.count()).select_from(
            base.where(AIModel.approval_status == "pending").subquery()
        )
    )).scalar_one()

    deprecated_count = (await db.execute(
        select(func.count()).select_from(
            base.where(AIModel.is_deprecated == True).subquery()  # noqa: E712
        )
    )).scalar_one()

    # Risk distribution
    risk_rows = (await db.execute(
        select(AIModel.risk_level, func.count(AIModel.id))
        .where(AIModel.org_id == org.id)
        .group_by(AIModel.risk_level)
    )).all()
    by_risk = {str(row[0]): row[1] for row in risk_rows}

    # Provider distribution
    provider_rows = (await db.execute(
        select(AIModel.provider, func.count(AIModel.id))
        .where(AIModel.org_id == org.id)
        .group_by(AIModel.provider)
    )).all()
    by_provider = {str(row[0]): row[1] for row in provider_rows}

    return ModelSummary(
        total_models=total,
        approved=approved,
        pending=pending,
        deprecated=deprecated_count,
        by_risk_level=by_risk,
        by_provider=by_provider,
    )


@router.get("/{model_id}", response_model=AIModelResponse)
async def get_model(
    model_id: UUID,
    _user: User = Depends(require_permission("compliance:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AIModelResponse:
    """Get a specific registered model."""
    result = await db.execute(
        select(AIModel).where(AIModel.id == model_id, AIModel.org_id == org.id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return AIModelResponse.model_validate(model)


@router.post("", response_model=AIModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    body: AIModelCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> AIModelResponse:
    """Register a new AI model in the org's model registry."""
    release_dt = None
    if body.release_date:
        try:
            release_dt = datetime.fromisoformat(body.release_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    model = AIModel(
        org_id=org.id,
        model_name=body.model_name,
        model_version=body.model_version,
        provider=body.provider,
        model_type=body.model_type,
        license_type=body.license_type,
        model_hash=body.model_hash,
        repository_url=body.repository_url,
        model_card_url=body.model_card_url,
        release_date=release_dt,
        parameter_count=body.parameter_count,
        context_window=body.context_window,
        risk_level=body.risk_level,
        risk_factors=body.risk_factors,
        compliance_frameworks=body.compliance_frameworks,
        known_limitations=body.known_limitations,
        pii_handling=body.pii_handling,
        training_data_sources=body.training_data_sources,
        training_cutoff=body.training_cutoff,
        model_dependencies=body.model_dependencies,
        capabilities=body.capabilities,
        owner_email=body.owner_email,
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return AIModelResponse.model_validate(model)


@router.patch("/{model_id}", response_model=AIModelResponse)
async def update_model(
    model_id: UUID,
    body: AIModelUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> AIModelResponse:
    """Update a registered model's metadata."""
    result = await db.execute(
        select(AIModel).where(AIModel.id == model_id, AIModel.org_id == org.id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)
    return AIModelResponse.model_validate(model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a registered model from the registry."""
    result = await db.execute(
        select(AIModel).where(AIModel.id == model_id, AIModel.org_id == org.id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    await db.delete(model)
    await db.commit()
