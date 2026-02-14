"""Core sandbox service for managing ephemeral execution environments.

Handles CRUD for sandbox definitions and lifecycle management for executions.
Uses Docker SDK for container management with resource limits and network isolation.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SandboxActionType, SandboxStatus
from app.models.sandbox import Sandbox
from app.models.sandbox_audit_log import SandboxAuditLog
from app.models.sandbox_execution import SandboxExecution
from app.services.sandbox.audit_logger import log_sandbox_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sandbox CRUD
# ---------------------------------------------------------------------------


async def create_sandbox(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    description: str | None = None,
    agent_id: UUID | None = None,
    image: str = "agentguard/sandbox-base:latest",
    capabilities: list[dict[str, Any]] | None = None,
    resource_limits: dict[str, Any] | None = None,
    network_policy: dict[str, Any] | None = None,
    environment: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Sandbox:
    """Create a new sandbox definition."""
    sandbox = Sandbox(
        org_id=org_id,
        agent_id=agent_id,
        name=name,
        description=description,
        status=SandboxStatus.PENDING.value,
        image=image,
        capabilities=capabilities or [],
        resource_limits=resource_limits or {
            "cpu_shares": 512,
            "memory_mb": 256,
            "max_tokens": 10000,
            "timeout_seconds": 300,
        },
        network_policy=network_policy or {
            "allowed_hosts": [],
            "allowed_ports": [443, 80],
            "deny_all_egress": True,
        },
        environment=environment or {},
        metadata_=metadata or {},
    )
    db.add(sandbox)
    await db.flush()
    await db.refresh(sandbox)
    logger.info("Created sandbox %s for org %s", sandbox.id, org_id)
    return sandbox


async def get_sandbox(
    db: AsyncSession, org_id: UUID, sandbox_id: UUID
) -> Sandbox | None:
    """Get a sandbox by ID, scoped to org."""
    result = await db.execute(
        select(Sandbox).where(Sandbox.id == sandbox_id, Sandbox.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def list_sandboxes(
    db: AsyncSession,
    org_id: UUID,
    status: str | None = None,
    agent_id: UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Sandbox], int]:
    """List sandboxes for an org with optional filters."""
    query = select(Sandbox).where(Sandbox.org_id == org_id)
    count_query = select(func.count()).select_from(Sandbox).where(Sandbox.org_id == org_id)

    if status:
        query = query.where(Sandbox.status == status)
        count_query = count_query.where(Sandbox.status == status)
    if agent_id:
        query = query.where(Sandbox.agent_id == agent_id)
        count_query = count_query.where(Sandbox.agent_id == agent_id)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(Sandbox.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


async def update_sandbox(
    db: AsyncSession, org_id: UUID, sandbox_id: UUID, updates: dict[str, Any]
) -> Sandbox | None:
    """Update a sandbox definition."""
    sandbox = await get_sandbox(db, org_id, sandbox_id)
    if not sandbox:
        return None

    for key, value in updates.items():
        if value is not None and hasattr(sandbox, key):
            setattr(sandbox, key, value)
    await db.flush()
    await db.refresh(sandbox)
    return sandbox


async def destroy_sandbox(db: AsyncSession, org_id: UUID, sandbox_id: UUID) -> bool:
    """Delete a sandbox and all associated executions/audit logs.

    Running executions are terminated first.
    """
    sandbox = await get_sandbox(db, org_id, sandbox_id)
    if not sandbox:
        return False

    # Terminate any running executions
    running = await db.execute(
        select(SandboxExecution).where(
            SandboxExecution.sandbox_id == sandbox_id,
            SandboxExecution.status == SandboxStatus.RUNNING.value,
        )
    )
    for execution in running.scalars().all():
        execution.status = SandboxStatus.TERMINATED.value
        execution.finished_at = datetime.now(timezone.utc)
        _terminate_container(execution.container_id)

    await db.delete(sandbox)
    await db.flush()
    logger.info("Destroyed sandbox %s for org %s", sandbox_id, org_id)
    return True


# ---------------------------------------------------------------------------
# Execution Lifecycle
# ---------------------------------------------------------------------------


async def _get_execution(
    db: AsyncSession, org_id: UUID, execution_id: UUID
) -> SandboxExecution | None:
    """Internal helper to fetch an execution scoped to org."""
    result = await db.execute(
        select(SandboxExecution).where(
            SandboxExecution.id == execution_id,
            SandboxExecution.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def start_execution(
    db: AsyncSession,
    org_id: UUID,
    sandbox_id: UUID,
    trigger: str = "api",
) -> SandboxExecution | None:
    """Start a new ephemeral execution in a sandbox.

    Creates a Docker container with the sandbox's resource limits and network policy.
    """
    sandbox = await get_sandbox(db, org_id, sandbox_id)
    if not sandbox:
        return None

    # Create execution record
    execution = SandboxExecution(
        org_id=org_id,
        sandbox_id=sandbox_id,
        status=SandboxStatus.PROVISIONING.value,
        trigger=trigger,
        resource_usage={
            "cpu_seconds": 0,
            "memory_peak_mb": 0,
            "tokens_used": 0,
            "network_bytes": 0,
        },
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # Attempt to start Docker container
    container_id = _start_container(sandbox)
    if container_id:
        execution.status = SandboxStatus.RUNNING.value
        execution.container_id = container_id
        execution.started_at = datetime.now(timezone.utc)
        sandbox.status = SandboxStatus.RUNNING.value
    else:
        execution.status = SandboxStatus.FAILED.value
        execution.error_message = "Failed to start container"
        sandbox.status = SandboxStatus.FAILED.value

    await db.flush()
    await db.refresh(execution)

    # Audit log the lifecycle event
    await log_sandbox_action(
        db=db,
        org_id=org_id,
        execution_id=execution.id,
        action_type=SandboxActionType.SANDBOX_LIFECYCLE.value,
        action_detail={
            "event": "execution_started",
            "trigger": trigger,
            "container_id": container_id,
            "image": sandbox.image,
        },
        allowed=True,
    )

    return execution


async def stop_execution(
    db: AsyncSession, org_id: UUID, execution_id: UUID, reason: str = "user_request"
) -> SandboxExecution | None:
    """Gracefully stop a running execution."""
    execution = await _get_execution(db, org_id, execution_id)
    if not execution or execution.status != SandboxStatus.RUNNING.value:
        return execution

    _stop_container(execution.container_id)
    execution.status = SandboxStatus.TERMINATED.value
    execution.finished_at = datetime.now(timezone.utc)

    # Update parent sandbox status
    sandbox = await get_sandbox(db, org_id, execution.sandbox_id)
    if sandbox:
        sandbox.status = SandboxStatus.PENDING.value

    await log_sandbox_action(
        db=db,
        org_id=org_id,
        execution_id=execution.id,
        action_type=SandboxActionType.SANDBOX_LIFECYCLE.value,
        action_detail={"event": "execution_stopped", "reason": reason},
        allowed=True,
    )

    await db.flush()
    await db.refresh(execution)
    return execution


async def terminate_execution(
    db: AsyncSession, org_id: UUID, execution_id: UUID, reason: str = "forced"
) -> SandboxExecution | None:
    """Immediately kill a running execution."""
    execution = await _get_execution(db, org_id, execution_id)
    if not execution:
        return None
    if execution.status not in (SandboxStatus.RUNNING.value, SandboxStatus.PROVISIONING.value):
        return execution

    _terminate_container(execution.container_id)
    execution.status = SandboxStatus.TERMINATED.value
    execution.finished_at = datetime.now(timezone.utc)

    sandbox = await get_sandbox(db, org_id, execution.sandbox_id)
    if sandbox:
        sandbox.status = SandboxStatus.PENDING.value

    await log_sandbox_action(
        db=db,
        org_id=org_id,
        execution_id=execution.id,
        action_type=SandboxActionType.SANDBOX_LIFECYCLE.value,
        action_detail={"event": "execution_terminated", "reason": reason},
        allowed=True,
    )

    await db.flush()
    await db.refresh(execution)
    return execution


async def get_execution(
    db: AsyncSession, org_id: UUID, execution_id: UUID
) -> SandboxExecution | None:
    """Get execution details."""
    return await _get_execution(db, org_id, execution_id)


async def list_executions(
    db: AsyncSession,
    org_id: UUID,
    sandbox_id: UUID | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SandboxExecution], int]:
    """List executions with optional filters."""
    query = select(SandboxExecution).where(SandboxExecution.org_id == org_id)
    count_q = (
        select(func.count())
        .select_from(SandboxExecution)
        .where(SandboxExecution.org_id == org_id)
    )

    if sandbox_id:
        query = query.where(SandboxExecution.sandbox_id == sandbox_id)
        count_q = count_q.where(SandboxExecution.sandbox_id == sandbox_id)
    if status:
        query = query.where(SandboxExecution.status == status)
        count_q = count_q.where(SandboxExecution.status == status)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(SandboxExecution.created_at.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


async def get_sandbox_stats(db: AsyncSession, org_id: UUID) -> dict[str, int]:
    """Aggregate sandbox metrics for dashboard."""
    total_sandboxes = (
        await db.execute(
            select(func.count()).select_from(Sandbox).where(Sandbox.org_id == org_id)
        )
    ).scalar() or 0

    active_sandboxes = (
        await db.execute(
            select(func.count())
            .select_from(Sandbox)
            .where(Sandbox.org_id == org_id, Sandbox.is_active.is_(True))
        )
    ).scalar() or 0

    total_executions = (
        await db.execute(
            select(func.count())
            .select_from(SandboxExecution)
            .where(SandboxExecution.org_id == org_id)
        )
    ).scalar() or 0

    running_executions = (
        await db.execute(
            select(func.count())
            .select_from(SandboxExecution)
            .where(
                SandboxExecution.org_id == org_id,
                SandboxExecution.status == SandboxStatus.RUNNING.value,
            )
        )
    ).scalar() or 0

    denied_actions = (
        await db.execute(
            select(func.count())
            .select_from(SandboxAuditLog)
            .where(
                SandboxAuditLog.org_id == org_id,
                SandboxAuditLog.allowed.is_(False),
            )
        )
    ).scalar() or 0

    return {
        "total_sandboxes": total_sandboxes,
        "active_sandboxes": active_sandboxes,
        "total_executions": total_executions,
        "running_executions": running_executions,
        "denied_actions": denied_actions,
        "total_tokens_used": 0,
    }


# ---------------------------------------------------------------------------
# Audit Log Queries
# ---------------------------------------------------------------------------


async def list_audit_logs(
    db: AsyncSession,
    org_id: UUID,
    execution_id: UUID | None = None,
    sandbox_id: UUID | None = None,
    action_type: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> tuple[list[SandboxAuditLog], int]:
    """List sandbox audit logs with filters."""
    query = select(SandboxAuditLog).where(SandboxAuditLog.org_id == org_id)
    count_q = (
        select(func.count())
        .select_from(SandboxAuditLog)
        .where(SandboxAuditLog.org_id == org_id)
    )

    if execution_id:
        query = query.where(SandboxAuditLog.execution_id == execution_id)
        count_q = count_q.where(SandboxAuditLog.execution_id == execution_id)
    if sandbox_id:
        # Filter by sandbox_id through execution join
        exec_ids = select(SandboxExecution.id).where(
            SandboxExecution.sandbox_id == sandbox_id
        )
        query = query.where(SandboxAuditLog.execution_id.in_(exec_ids))
        count_q = count_q.where(SandboxAuditLog.execution_id.in_(exec_ids))
    if action_type:
        query = query.where(SandboxAuditLog.action_type == action_type)
        count_q = count_q.where(SandboxAuditLog.action_type == action_type)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        query.order_by(SandboxAuditLog.timestamp.desc()).offset(offset).limit(limit)
    )
    return list(result.scalars().all()), total


# ---------------------------------------------------------------------------
# Docker Container Helpers (abstraction layer for future gVisor/Firecracker)
# ---------------------------------------------------------------------------


def _get_docker_client() -> Any:
    """Get Docker client. Returns None if Docker is not available."""
    try:
        import docker
        return docker.from_env()
    except Exception as e:
        logger.warning("Docker not available: %s", e)
        return None


def _start_container(sandbox: Sandbox) -> str | None:
    """Start a Docker container for a sandbox execution."""
    client = _get_docker_client()
    if not client:
        logger.info(
            "Docker not available — running in simulation mode for sandbox %s",
            sandbox.id,
        )
        return f"sim-{str(sandbox.id)[:12]}"

    try:
        limits = sandbox.resource_limits or {}
        container = client.containers.run(
            image=sandbox.image,
            detach=True,
            mem_limit=f"{limits.get('memory_mb', 256)}m",
            cpu_shares=limits.get("cpu_shares", 512),
            network_mode="none" if sandbox.network_policy.get("deny_all_egress", True) else "bridge",
            labels={
                "agentguard.sandbox_id": str(sandbox.id),
                "agentguard.org_id": str(sandbox.org_id),
            },
            environment=sandbox.environment or {},
            auto_remove=False,
        )
        return container.id
    except Exception as e:
        logger.error("Failed to start container for sandbox %s: %s", sandbox.id, e)
        return None


def _stop_container(container_id: str | None) -> None:
    """Gracefully stop a container."""
    if not container_id or container_id.startswith("sim-"):
        return
    client = _get_docker_client()
    if not client:
        return
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
    except Exception as e:
        logger.warning("Failed to stop container %s: %s", container_id, e)


def _terminate_container(container_id: str | None) -> None:
    """Immediately kill a container."""
    if not container_id or container_id.startswith("sim-"):
        return
    client = _get_docker_client()
    if not client:
        return
    try:
        container = client.containers.get(container_id)
        container.kill()
    except Exception as e:
        logger.warning("Failed to kill container %s: %s", container_id, e)
