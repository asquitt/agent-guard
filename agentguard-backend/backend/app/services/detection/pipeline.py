"""Detection pipeline — orchestrates sync and async detector execution."""

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.detector import Detector
from app.models.enums import ActionMode
from app.models.incident import Incident
from app.services.detection.registry import (
    ASYNC_CATEGORIES,
    SYNC_CATEGORIES,
    get_sync_detector,
)
from app.services.detection.types import (
    DetectionAction,
    DetectionResult,
    PipelineDecision,
)

logger = logging.getLogger(__name__)

# Priority ordering for action escalation
_ACTION_PRIORITY: dict[str, int] = {
    DetectionAction.PASS.value: 0,
    DetectionAction.MONITOR.value: 1,
    DetectionAction.WARN.value: 2,
    DetectionAction.REDACT.value: 3,
    DetectionAction.BLOCK.value: 4,
}

_ACTION_MODE_MAP: dict[str, DetectionAction] = {
    ActionMode.MONITOR.value: DetectionAction.MONITOR,
    ActionMode.WARN.value: DetectionAction.WARN,
    ActionMode.REDACT.value: DetectionAction.REDACT,
    ActionMode.BLOCK.value: DetectionAction.BLOCK,
}


async def load_active_detectors(
    db: AsyncSession,
    org_id: UUID,
    categories: frozenset[str],
) -> list[Detector]:
    """Fetch org's active detectors for the given categories."""
    result = await db.execute(
        select(Detector)
        .options(selectinload(Detector.rules))
        .where(
            Detector.org_id == org_id,
            Detector.is_active.is_(True),
            Detector.category.in_(categories),
        )
        .order_by(Detector.category)
    )
    return list(result.scalars().all())


async def run_sync_detectors(
    db: AsyncSession,
    org_id: UUID,
    request_body: str,
    response_body: str,
    model: str | None,
    proxy_request_id: UUID,
) -> PipelineDecision:
    """Run all sync detectors and aggregate results.

    Creates incidents for any detections. Uses flush() so caller commits.
    Detector failures are caught and logged, never propagated.
    """
    detectors = await load_active_detectors(db, org_id, SYNC_CATEGORIES)

    if not detectors:
        return PipelineDecision(action=DetectionAction.PASS, results=[])

    results: list[DetectionResult] = []
    highest_action = DetectionAction.PASS
    modified_body: str | None = None

    for detector in detectors:
        category = str(detector.category)
        action_mode = str(detector.action_mode)
        config = detector.config if isinstance(detector.config, dict) else {}

        try:
            impl = get_sync_detector(category)
            result = impl.run(request_body, response_body, model, config)

            if result.detected:
                effective_action = _ACTION_MODE_MAP.get(action_mode, DetectionAction.MONITOR)
                result = DetectionResult(
                    detected=True,
                    severity=result.severity,
                    category=result.category,
                    detector_id=UUID(str(detector.id)),
                    action=effective_action,
                    title=result.title,
                    description=result.description,
                    details=result.details,
                )

                if _ACTION_PRIORITY.get(effective_action.value, 0) > _ACTION_PRIORITY.get(highest_action.value, 0):
                    highest_action = effective_action

                if effective_action == DetectionAction.REDACT and "redacted_response" in result.details:
                    modified_body = str(result.details["redacted_response"])

                await _create_incident_from_result(db, org_id, proxy_request_id, result)

            results.append(result)

        except Exception:
            logger.exception("Sync detector %s failed for org %s", category, org_id)
            continue

    return PipelineDecision(
        action=highest_action,
        results=results,
        modified_response=modified_body,
    )


async def queue_async_detectors(
    db: AsyncSession,
    org_id: UUID,
    proxy_request_id: UUID,
) -> str | None:
    """Check for active async detectors and queue a Celery task.

    Returns the Celery task ID if queued, None otherwise.
    """
    detectors = await load_active_detectors(db, org_id, ASYNC_CATEGORIES)

    if not detectors:
        return None

    from app.tasks.analysis import run_async_detection

    task = run_async_detection.delay(str(org_id), str(proxy_request_id))
    logger.info(
        "Queued async detection task %s for request %s",
        task.id,
        proxy_request_id,
    )
    return str(task.id)


async def _create_incident_from_result(
    db: AsyncSession,
    org_id: UUID,
    proxy_request_id: UUID,
    result: DetectionResult,
) -> Incident:
    """Create an Incident record from a DetectionResult and queue alerts."""
    incident = Incident(
        org_id=org_id,
        proxy_request_id=proxy_request_id,
        detector_id=result.detector_id,
        severity=result.severity,
        category=result.category,
        title=result.title,
        description=result.description,
        status="open",
        action_taken=result.action.value,
        metadata_=result.details,  # type: ignore[assignment]
    )
    db.add(incident)
    await db.flush()

    # Publish real-time event (best-effort)
    try:
        from app.core.events import publish_event

        await publish_event(
            str(org_id),
            "incident.new",
            {
                "id": str(incident.id),
                "severity": str(incident.severity),
                "category": str(incident.category),
                "title": str(incident.title),
                "status": "open",
            },
        )
    except Exception:
        logger.exception("Failed to publish incident.new event for %s", incident.id)

    # Queue alerts asynchronously (best-effort, never block detection)
    try:
        from app.services.alert_service import trigger_alerts

        await trigger_alerts(org_id, UUID(str(incident.id)))
    except Exception:
        logger.exception("Failed to queue alerts for incident %s", incident.id)

    return incident
