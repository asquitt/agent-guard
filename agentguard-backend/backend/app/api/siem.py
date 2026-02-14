"""SIEM/SOAR integration router — manage SIEM destinations and preview event formats."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.models.alert import AlertDestination
from app.models.user import Organization, User
from app.services import siem_service
from app.services.audit_service import write_audit

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

VALID_FORMATS = siem_service.get_supported_formats()


class SiemDestinationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    format: str = Field(description="SIEM format: splunk_hec, cef, leef, ecs, ocsf")
    auth_header: str | None = Field(
        default=None, max_length=512,
        description="Authorization header value (e.g. 'Splunk <token>')",
    )
    event_types: list[str] = Field(
        default_factory=lambda: ["incident.created", "incident.resolved"],
    )
    min_severity: str = "medium"


class SiemDestinationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    format: str | None = None
    auth_header: str | None = None
    event_types: list[str] | None = None
    min_severity: str | None = None
    is_active: bool | None = None


class SiemDestinationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    url: str
    format: str
    event_types: list[str] = Field(serialization_alias="eventTypes")
    min_severity: str = Field(serialization_alias="minSeverity")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")


class SiemDestinationListResponse(BaseModel):
    items: list[SiemDestinationResponse]
    total: int


class FormatPreviewResponse(BaseModel):
    format: str
    output: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/formats")
async def list_siem_formats(
    _org: Organization = Depends(get_current_org),
) -> dict:
    """List supported SIEM output formats."""
    return {
        "formats": [
            {"id": "splunk_hec", "name": "Splunk HEC", "description": "HTTP Event Collector JSON"},
            {"id": "cef", "name": "CEF", "description": "Common Event Format (syslog)"},
            {"id": "leef", "name": "LEEF", "description": "Log Event Extended Format (IBM QRadar)"},
            {"id": "ecs", "name": "ECS", "description": "Elastic Common Schema"},
            {"id": "ocsf", "name": "OCSF", "description": "Open Cybersecurity Schema Framework"},
        ]
    }


@router.post("/preview", response_model=FormatPreviewResponse)
async def preview_format(
    fmt: str = Query(description="SIEM format to preview"),
    _org: Organization = Depends(get_current_org),
) -> FormatPreviewResponse:
    """Preview a sample incident in the requested SIEM format."""
    if fmt not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{fmt}'. Supported: {VALID_FORMATS}",
        )

    sample = {
        "id": "00000000-0000-0000-0000-000000000001",
        "org_id": "00000000-0000-0000-0000-000000000002",
        "title": "Prompt injection detected in production agent",
        "description": "DAN mode activation attempt blocked by prompt injection detector",
        "severity": "high",
        "category": "prompt_injection",
        "status": "open",
        "action_taken": "block",
        "model": "gpt-4o",
        "risk_score": 92,
        "proxy_request_id": "00000000-0000-0000-0000-000000000003",
        "detector_id": "00000000-0000-0000-0000-000000000004",
        "created_at": datetime.now(timezone.utc),
    }

    result = siem_service.format_incident(sample, fmt)
    import json as _json
    output = result if isinstance(result, str) else _json.dumps(result, indent=2, default=str)
    return FormatPreviewResponse(format=fmt, output=output)


@router.post("", response_model=SiemDestinationResponse, status_code=status.HTTP_201_CREATED)
async def create_siem_destination(
    body: SiemDestinationCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> SiemDestinationResponse:
    """Register a SIEM destination."""
    if body.format not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{body.format}'. Supported: {VALID_FORMATS}",
        )

    dest = AlertDestination(
        org_id=org.id,
        name=body.name,
        destination_type="siem",
        config={
            "url": body.url,
            "format": body.format,
            "auth_header": body.auth_header or "",
            "event_types": body.event_types,
            "min_severity": body.min_severity,
        },
        is_active=True,
    )
    db.add(dest)
    await db.flush()
    await write_audit(
        db, UUID(str(org.id)), UUID(str(admin_user.id)),
        "siem.created", "siem_destination", UUID(str(dest.id)),
        {"name": body.name, "format": body.format}, None,
    )
    await db.commit()
    await db.refresh(dest)
    return _to_response(dest)


@router.get("", response_model=SiemDestinationListResponse)
async def list_siem_destinations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SiemDestinationListResponse:
    """List SIEM destinations for the org."""
    base = select(AlertDestination).where(
        AlertDestination.org_id == org.id,
        AlertDestination.destination_type == "siem",
    )
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    result = await db.execute(base.order_by(AlertDestination.created_at.desc()).offset(skip).limit(limit))
    items = [_to_response(d) for d in result.scalars().all()]
    return SiemDestinationListResponse(items=items, total=total)


@router.patch("/{dest_id}", response_model=SiemDestinationResponse)
async def update_siem_destination(
    dest_id: UUID,
    body: SiemDestinationUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> SiemDestinationResponse:
    """Update a SIEM destination."""
    dest = await _get_or_404(db, org, dest_id)

    if body.format and body.format not in VALID_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format '{body.format}'. Supported: {VALID_FORMATS}",
        )

    if body.name is not None:
        dest.name = body.name  # type: ignore[assignment]
    if body.is_active is not None:
        dest.is_active = body.is_active  # type: ignore[assignment]

    config = dest.config if isinstance(dest.config, dict) else {}
    if body.url is not None:
        config["url"] = body.url
    if body.format is not None:
        config["format"] = body.format
    if body.auth_header is not None:
        config["auth_header"] = body.auth_header
    if body.event_types is not None:
        config["event_types"] = body.event_types
    if body.min_severity is not None:
        config["min_severity"] = body.min_severity
    dest.config = config  # type: ignore[assignment]

    await db.commit()
    await db.refresh(dest)
    return _to_response(dest)


@router.delete("/{dest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_siem_destination(
    dest_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a SIEM destination."""
    dest = await _get_or_404(db, org, dest_id)
    await db.delete(dest)
    await db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(dest: AlertDestination) -> SiemDestinationResponse:
    config = dest.config if isinstance(dest.config, dict) else {}
    return SiemDestinationResponse(
        id=dest.id,
        name=dest.name,
        url=config.get("url", ""),
        format=config.get("format", "cef"),
        event_types=config.get("event_types", []),
        min_severity=config.get("min_severity", "medium"),
        is_active=dest.is_active,
        created_at=dest.created_at,
    )


async def _get_or_404(
    db: AsyncSession, org: Organization, dest_id: UUID
) -> AlertDestination:
    result = await db.execute(
        select(AlertDestination).where(
            AlertDestination.id == dest_id,
            AlertDestination.org_id == org.id,
            AlertDestination.destination_type == "siem",
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SIEM destination not found")
    return dest
