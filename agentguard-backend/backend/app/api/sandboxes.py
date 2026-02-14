"""Sandbox execution runtime router — CRUD, execution lifecycle, and audit trail."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization
from app.schemas.sandbox import (
    SandboxAuditLogListResponse,
    SandboxAuditLogResponse,
    SandboxCreateRequest,
    SandboxExecutionCreateRequest,
    SandboxExecutionListResponse,
    SandboxExecutionResponse,
    SandboxListResponse,
    SandboxResponse,
    SandboxStats,
    SandboxUpdateRequest,
)
from app.services.sandbox import sandbox_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Sandbox CRUD
# ---------------------------------------------------------------------------


@router.get("/stats", response_model=SandboxStats)
async def sandbox_stats(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxStats:
    """Get aggregate sandbox metrics for dashboard."""
    stats = await sandbox_service.get_sandbox_stats(db, org.id)
    return SandboxStats(**stats)


@router.get("", response_model=SandboxListResponse)
async def list_sandboxes(
    sandbox_status: str | None = Query(default=None, alias="status"),
    agent_id: UUID | None = Query(default=None, alias="agentId"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxListResponse:
    """List sandboxes with optional filtering."""
    items, total = await sandbox_service.list_sandboxes(
        db, org.id, status=sandbox_status, agent_id=agent_id, offset=skip, limit=limit
    )
    return SandboxListResponse(
        items=[SandboxResponse.model_validate(s) for s in items],
        total=total,
    )


@router.post("", response_model=SandboxResponse, status_code=status.HTTP_201_CREATED)
async def create_sandbox(
    body: SandboxCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxResponse:
    """Create a new sandbox definition."""
    sandbox = await sandbox_service.create_sandbox(
        db=db,
        org_id=org.id,
        name=body.name,
        description=body.description,
        agent_id=body.agent_id,
        image=body.image,
        capabilities=[c.model_dump() for c in body.capabilities],
        resource_limits=body.resource_limits.model_dump(),
        network_policy=body.network_policy.model_dump(),
        environment=body.environment,
        metadata=body.metadata,
    )
    await db.commit()
    return SandboxResponse.model_validate(sandbox)


# ---------------------------------------------------------------------------
# Execution routes (MUST be before /{sandbox_id} to avoid path conflicts)
# ---------------------------------------------------------------------------


@router.get("/executions/{execution_id}", response_model=SandboxExecutionResponse)
async def get_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxExecutionResponse:
    """Get execution details with resource usage."""
    execution = await sandbox_service.get_execution(db, org.id, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return SandboxExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/stop", response_model=SandboxExecutionResponse)
async def stop_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxExecutionResponse:
    """Gracefully stop a running execution."""
    execution = await sandbox_service.stop_execution(db, org.id, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    await db.commit()
    return SandboxExecutionResponse.model_validate(execution)


@router.post("/executions/{execution_id}/terminate", response_model=SandboxExecutionResponse)
async def terminate_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxExecutionResponse:
    """Immediately kill a running execution."""
    execution = await sandbox_service.terminate_execution(db, org.id, execution_id)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    await db.commit()
    return SandboxExecutionResponse.model_validate(execution)


@router.get("/executions/{execution_id}/audit", response_model=SandboxAuditLogListResponse)
async def get_execution_audit(
    execution_id: UUID,
    action_type: str | None = Query(default=None, alias="actionType"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxAuditLogListResponse:
    """Get audit log for a specific execution."""
    items, total = await sandbox_service.list_audit_logs(
        db, org.id, execution_id=execution_id, action_type=action_type, offset=skip, limit=limit
    )
    return SandboxAuditLogListResponse(
        items=[SandboxAuditLogResponse.model_validate(a) for a in items],
        total=total,
    )


@router.get("/executions/{execution_id}/incidents")
async def get_execution_incidents(
    execution_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> dict:
    """Get incidents linked to a specific sandbox execution."""
    from sqlalchemy import select, func
    from app.models.incident import Incident
    from app.schemas.incidents import IncidentResponse

    base_filter = [Incident.org_id == org.id, Incident.sandbox_execution_id == execution_id]
    count_result = await db.execute(select(func.count(Incident.id)).where(*base_filter))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Incident)
        .where(*base_filter)
        .order_by(Incident.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = [IncidentResponse.model_validate(i) for i in result.scalars().all()]
    return {"items": items, "total": total}


# ---------------------------------------------------------------------------
# Sandbox-scoped routes (/{sandbox_id}/...)
# ---------------------------------------------------------------------------


@router.get("/{sandbox_id}", response_model=SandboxResponse)
async def get_sandbox(
    sandbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxResponse:
    """Get sandbox details."""
    sandbox = await sandbox_service.get_sandbox(db, org.id, sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found")
    return SandboxResponse.model_validate(sandbox)


@router.patch("/{sandbox_id}", response_model=SandboxResponse)
async def update_sandbox(
    sandbox_id: UUID,
    body: SandboxUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxResponse:
    """Update sandbox configuration."""
    update_data = body.model_dump(exclude_unset=True)
    if "metadata" in update_data:
        update_data["metadata_"] = update_data.pop("metadata")
    if "capabilities" in update_data and update_data["capabilities"] is not None:
        update_data["capabilities"] = [
            c.model_dump() if hasattr(c, "model_dump") else c
            for c in update_data["capabilities"]
        ]
    if "resource_limits" in update_data and update_data["resource_limits"] is not None:
        rl = update_data["resource_limits"]
        update_data["resource_limits"] = rl.model_dump() if hasattr(rl, "model_dump") else rl
    if "network_policy" in update_data and update_data["network_policy"] is not None:
        np = update_data["network_policy"]
        update_data["network_policy"] = np.model_dump() if hasattr(np, "model_dump") else np

    sandbox = await sandbox_service.update_sandbox(db, org.id, sandbox_id, update_data)
    if not sandbox:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found")
    await db.commit()
    return SandboxResponse.model_validate(sandbox)


@router.delete("/{sandbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sandbox(
    sandbox_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a sandbox and all associated resources."""
    deleted = await sandbox_service.destroy_sandbox(db, org.id, sandbox_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found")
    await db.commit()


@router.put("/{sandbox_id}/capabilities", response_model=SandboxResponse)
async def set_capabilities(
    sandbox_id: UUID,
    capabilities: list[dict],
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxResponse:
    """Replace all capabilities for a sandbox."""
    sandbox = await sandbox_service.update_sandbox(
        db, org.id, sandbox_id, {"capabilities": capabilities}
    )
    if not sandbox:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found")
    await db.commit()
    return SandboxResponse.model_validate(sandbox)


@router.post("/{sandbox_id}/execute", response_model=SandboxExecutionResponse, status_code=status.HTTP_201_CREATED)
async def start_execution(
    sandbox_id: UUID,
    body: SandboxExecutionCreateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxExecutionResponse:
    """Start a new ephemeral execution in a sandbox."""
    trigger = body.trigger if body else "api"
    execution = await sandbox_service.start_execution(db, org.id, sandbox_id, trigger=trigger)
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sandbox not found")
    await db.commit()
    return SandboxExecutionResponse.model_validate(execution)


@router.get("/{sandbox_id}/executions", response_model=SandboxExecutionListResponse)
async def list_executions(
    sandbox_id: UUID,
    exec_status: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxExecutionListResponse:
    """List executions for a sandbox."""
    items, total = await sandbox_service.list_executions(
        db, org.id, sandbox_id=sandbox_id, status=exec_status, offset=skip, limit=limit
    )
    return SandboxExecutionListResponse(
        items=[SandboxExecutionResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get("/{sandbox_id}/audit", response_model=SandboxAuditLogListResponse)
async def get_sandbox_audit(
    sandbox_id: UUID,
    action_type: str | None = Query(default=None, alias="actionType"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SandboxAuditLogListResponse:
    """Get all audit logs for a sandbox across all executions."""
    items, total = await sandbox_service.list_audit_logs(
        db, org.id, sandbox_id=sandbox_id, action_type=action_type, offset=skip, limit=limit
    )
    return SandboxAuditLogListResponse(
        items=[SandboxAuditLogResponse.model_validate(a) for a in items],
        total=total,
    )
