"""Detector management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.detectors import (
    DetectorCreateRequest,
    DetectorListResponse,
    DetectorResponse,
    DetectorRuleCreateRequest,
    DetectorRuleResponse,
    DetectorUpdateRequest,
)
from app.services import detector_service

router = APIRouter()


@router.post(
    "/",
    response_model=DetectorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_detector(
    body: DetectorCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> DetectorResponse:
    """Create a detector with optional inline rules."""
    rules_data = None
    if body.rules:
        rules_data = [r.model_dump() for r in body.rules]

    detector = await detector_service.create_detector(
        db=db,
        org_id=UUID(str(org.id)),
        name=body.name,
        category=body.category,
        action_mode=body.action_mode,
        config=body.config,
        rules=rules_data,
    )
    return DetectorResponse.model_validate(detector)


@router.get("/", response_model=DetectorListResponse)
async def list_detectors(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DetectorListResponse:
    """List detectors for the current org."""
    items, total = await detector_service.list_detectors(
        db, UUID(str(org.id)), skip, limit
    )
    return DetectorListResponse(
        items=[DetectorResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/{detector_id}", response_model=DetectorResponse)
async def get_detector(
    detector_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DetectorResponse:
    """Get a single detector with its rules."""
    try:
        detector = await detector_service.get_detector(
            db, UUID(str(org.id)), detector_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return DetectorResponse.model_validate(detector)


@router.patch("/{detector_id}", response_model=DetectorResponse)
async def update_detector(
    detector_id: UUID,
    body: DetectorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> DetectorResponse:
    """Update detector fields."""
    try:
        detector = await detector_service.update_detector(
            db,
            UUID(str(org.id)),
            detector_id,
            name=body.name,
            is_active=body.is_active,
            action_mode=body.action_mode,
            config=body.config,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return DetectorResponse.model_validate(detector)


@router.delete("/{detector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_detector(
    detector_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a detector and its rules."""
    try:
        await detector_service.delete_detector(
            db, UUID(str(org.id)), detector_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )


@router.post(
    "/{detector_id}/rules",
    response_model=DetectorRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_rule(
    detector_id: UUID,
    body: DetectorRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> DetectorRuleResponse:
    """Add a rule to a detector."""
    try:
        rule = await detector_service.add_rule(
            db,
            UUID(str(org.id)),
            detector_id,
            name=body.name,
            rule_type=body.rule_type,
            parameters=body.parameters,
            is_active=body.is_active,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return DetectorRuleResponse.model_validate(rule)


@router.delete(
    "/{detector_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rule(
    detector_id: UUID,
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a rule from a detector."""
    try:
        await detector_service.delete_rule(
            db, UUID(str(org.id)), detector_id, rule_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
