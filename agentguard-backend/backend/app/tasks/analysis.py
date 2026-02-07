"""Celery tasks for async detection analysis."""

# pyright: reportCallIssue=false, reportGeneralTypeIssues=false

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.models.detector import Detector
from app.models.incident import Incident
from app.models.proxy import ProxyRequest
from app.services.detection.registry import ASYNC_CATEGORIES, get_async_detector
from app.services.detection.types import ACTION_MODE_MAP, DetectionAction
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.analysis.run_async_detection",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def run_async_detection(
    self,  # type: ignore[override]
    org_id_str: str,
    proxy_request_id_str: str,
) -> dict[str, object]:
    """Run all async detectors for a proxy request.

    Uses sync DB session (Celery worker context).
    """
    org_id = UUID(org_id_str)
    proxy_request_id = UUID(proxy_request_id_str)

    with SessionLocal() as db:
        try:
            proxy_req = db.execute(select(ProxyRequest).where(ProxyRequest.id == proxy_request_id)).scalar_one_or_none()

            if proxy_req is None:
                logger.warning("ProxyRequest %s not found, skipping", proxy_request_id)
                return {"status": "skipped", "reason": "request_not_found"}

            detectors = list(
                db.execute(
                    select(Detector)
                    .options(selectinload(Detector.rules))
                    .where(
                        Detector.org_id == org_id,
                        Detector.is_active.is_(True),
                        Detector.category.in_(ASYNC_CATEGORIES),
                    )
                    .order_by(Detector.category)
                )
                .scalars()
                .all()
            )

            if not detectors:
                return {"status": "skipped", "reason": "no_async_detectors"}

            request_body = str(proxy_req.request_body or "")
            response_body = str(proxy_req.response_body or "")
            model = str(proxy_req.model) if proxy_req.model else None

            incidents_created = 0

            for detector in detectors:
                category = str(detector.category)
                action_mode = str(detector.action_mode)
                config = detector.config if isinstance(detector.config, dict) else {}

                try:
                    impl = get_async_detector(category)
                    result = impl.run(
                        request_body,
                        response_body,
                        model,
                        config,
                        str(org_id),
                        str(proxy_request_id),
                    )

                    if result.detected:
                        effective_action = ACTION_MODE_MAP.get(action_mode, DetectionAction.MONITOR)
                        incident = Incident(
                            org_id=org_id,
                            proxy_request_id=proxy_request_id,
                            detector_id=detector.id,
                            severity=result.severity,
                            category=result.category,
                            title=result.title,
                            description=result.description,
                            status="open",
                            action_taken=effective_action.value,
                            metadata_=result.details,
                        )
                        db.add(incident)
                        incidents_created += 1

                except Exception:
                    logger.exception(
                        "Async detector %s failed for request %s",
                        category,
                        proxy_request_id,
                    )
                    continue

            db.commit()

            # Publish real-time events for created incidents (best-effort)
            if incidents_created > 0:
                try:
                    from app.core.events import publish_event_sync

                    publish_event_sync(
                        str(org_id),
                        "incident.new",
                        {
                            "source": "async_detection",
                            "count": incidents_created,
                        },
                    )
                except Exception:
                    logger.exception("Failed to publish incident.new events")

            return {
                "status": "completed",
                "detectors_run": len(detectors),
                "incidents_created": incidents_created,
            }

        except Exception:
            logger.exception(
                "Async detection task failed for request %s",
                proxy_request_id,
            )
            db.rollback()
            raise self.retry()
