"""Celery tasks for sandbox resource monitoring and lifecycle management."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.enums import SandboxActionType, SandboxStatus
from app.models.sandbox import Sandbox
from app.models.sandbox_execution import SandboxExecution
from app.services.sandbox.audit_logger import log_sandbox_action_sync
from app.services.sandbox.resource_monitor import check_resource_limits
from app.services.sandbox.types import ResourceUsage
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.sandbox_tasks.monitor_sandbox_resources")
def monitor_sandbox_resources() -> dict[str, int]:
    """Periodic task to check running sandbox executions for resource limit violations.

    Checks timeout, token budget, and memory limits. Auto-terminates on violation.
    """
    terminated = 0
    checked = 0

    with SessionLocal() as db:
        result = db.execute(
            select(SandboxExecution).where(
                SandboxExecution.status == SandboxStatus.RUNNING.value,
            )
        )
        executions = result.scalars().all()

        for execution in executions:
            checked += 1
            try:
                sandbox_result = db.execute(
                    select(Sandbox).where(Sandbox.id == execution.sandbox_id)
                )
                sandbox = sandbox_result.scalar_one_or_none()
                if not sandbox:
                    continue

                limits = sandbox.resource_limits or {}
                usage_data = execution.resource_usage or {}
                usage = ResourceUsage(
                    tokens_used=usage_data.get("tokens_used", 0),
                    memory_peak_mb=usage_data.get("memory_peak_mb", 0),
                    cpu_seconds=usage_data.get("cpu_seconds", 0),
                )

                violation = check_resource_limits(
                    usage, limits, started_at=execution.started_at
                )

                if violation:
                    # Terminate the execution
                    execution.status = SandboxStatus.TERMINATED.value
                    execution.finished_at = datetime.now(timezone.utc)
                    execution.error_message = violation.message
                    sandbox.status = SandboxStatus.PENDING.value

                    # Kill container if real
                    container_id = execution.container_id
                    if container_id and not container_id.startswith("sim-"):
                        try:
                            import docker
                            client = docker.from_env()
                            container = client.containers.get(container_id)
                            container.kill()
                        except Exception:
                            pass

                    # Audit log
                    log_sandbox_action_sync(
                        org_id=UUID(str(execution.org_id)),
                        execution_id=UUID(str(execution.id)),
                        action_type=SandboxActionType.RESOURCE_EXCEEDED.value,
                        action_detail={
                            "resource": violation.resource,
                            "limit": violation.limit,
                            "current": violation.current,
                            "message": violation.message,
                        },
                        allowed=False,
                    )

                    terminated += 1
                    logger.info(
                        "Terminated sandbox execution %s: %s",
                        execution.id, violation.message,
                    )

            except Exception:
                logger.exception(
                    "Error monitoring sandbox execution %s", execution.id
                )

        db.commit()

    return {"checked": checked, "terminated": terminated}
