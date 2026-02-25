"""Data retention management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.deps import get_client_ip, get_current_org, get_db, require_admin, require_permission
from app.models.user import Organization, User
from app.schemas.retention import (
    DataArchiveListResponse,
    DataArchiveResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdate,
)
from app.services import retention_service
from app.services.audit_service import write_audit

router = APIRouter()


@router.get("/policy", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    _user: User = Depends(require_permission("settings:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> RetentionPolicyResponse:
    """Get the organization's data retention policy (creates default if none)."""
    with SessionLocal() as sync_db:
        policy = retention_service.get_or_create_policy(sync_db, UUID(str(org.id)))
    return RetentionPolicyResponse.model_validate(policy)


@router.put("/policy", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    body: RetentionPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> RetentionPolicyResponse:
    """Update the organization's data retention policy (admin only)."""
    with SessionLocal() as sync_db:
        policy = retention_service.update_policy(
            sync_db,
            UUID(str(org.id)),
            proxy_requests_days=body.proxy_requests_days,
            incidents_days=body.incidents_days,
            audit_logs_days=body.audit_logs_days,
        )

    await write_audit(
        db,
        UUID(str(org.id)),
        UUID(str(admin_user.id)),
        "retention.policy.updated",
        "retention_policy",
        UUID(str(policy.id)),
        body.model_dump(exclude_none=True, by_alias=True),
        client_ip,
    )
    await db.commit()

    return RetentionPolicyResponse.model_validate(policy)


@router.get("/archives", response_model=DataArchiveListResponse)
async def list_archives(
    table_name: str | None = Query(None, alias="tableName"),
    skip: int = 0,
    limit: int = 50,
    _user: User = Depends(require_permission("settings:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DataArchiveListResponse:
    """List data archives for the organization."""
    with SessionLocal() as sync_db:
        items, total = retention_service.list_archives(
            sync_db, UUID(str(org.id)), table_name, skip, limit
        )
    return DataArchiveListResponse(
        items=[DataArchiveResponse.model_validate(a) for a in items],
        total=total,
    )


@router.get("/archives/{archive_id}", response_model=DataArchiveResponse)
async def get_archive(
    archive_id: UUID,
    _user: User = Depends(require_permission("settings:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DataArchiveResponse:
    """Get a single archive's details."""
    with SessionLocal() as sync_db:
        archive = retention_service.get_archive(sync_db, UUID(str(org.id)), archive_id)
    if archive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")
    return DataArchiveResponse.model_validate(archive)


@router.post("/archives/{archive_id}/retrieve", status_code=status.HTTP_200_OK)
async def retrieve_archive(
    archive_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("settings:read")),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> dict[str, str]:
    """Request archive retrieval (no-op for local storage; future S3 Glacier support)."""
    from app.services.archive_storage import LocalArchiveStorage
    from app.core.config import settings

    with SessionLocal() as sync_db:
        archive = retention_service.get_archive(sync_db, UUID(str(org.id)), archive_id)
    if archive is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")

    storage = LocalArchiveStorage(settings.ARCHIVE_STORAGE_PATH)
    if not storage.exists(str(archive.file_path)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive file not found in storage")

    await write_audit(
        db,
        UUID(str(org.id)),
        UUID(str(current_user.id)),
        "retention.archive.retrieve",
        "data_archive",
        archive_id,
        {"table_name": str(archive.table_name), "row_count": int(str(archive.row_count))},
        client_ip,
    )
    await db.commit()

    return {"status": "available", "message": "Archive is available for download"}
