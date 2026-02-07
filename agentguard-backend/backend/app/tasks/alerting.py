"""Celery tasks for alert delivery."""

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.alert import Alert, AlertDestination
from app.models.incident import Incident
from app.services.alert_delivery import deliver
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _build_payload(incident: Incident) -> dict[str, Any]:
    """Build alert payload from an incident."""
    return {
        "incident_id": str(incident.id),
        "severity": str(incident.severity),
        "category": str(incident.category),
        "title": str(incident.title),
        "description": str(incident.description or ""),
        "status": str(incident.status),
        "action_taken": str(incident.action_taken or ""),
        "created_at": str(incident.created_at),
    }


@celery_app.task(
    name="app.tasks.alerting.send_alerts_for_incident",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def send_alerts_for_incident(
    self,  # type: ignore[override]
    incident_id_str: str,
    org_id_str: str,
) -> dict[str, object]:
    """Send alerts to all active destinations for an incident.

    Evaluates severity threshold per destination. Creates Alert records
    for each delivery attempt.
    """
    incident_id = UUID(incident_id_str)
    org_id = UUID(org_id_str)

    with SessionLocal() as db:
        try:
            # Load incident
            incident = db.execute(
                select(Incident).where(Incident.id == incident_id)
            ).scalar_one_or_none()

            if incident is None:
                logger.warning("Incident %s not found, skipping alerts", incident_id)
                return {"status": "skipped", "reason": "incident_not_found"}

            # Load active destinations for org
            destinations = list(
                db.execute(
                    select(AlertDestination).where(
                        AlertDestination.org_id == org_id,
                        AlertDestination.is_active.is_(True),
                    )
                )
                .scalars()
                .all()
            )

            if not destinations:
                return {"status": "skipped", "reason": "no_destinations"}

            payload = _build_payload(incident)
            incident_severity = str(incident.severity)

            severity_rank = {
                "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4,
            }
            inc_rank = severity_rank.get(incident_severity, 0)

            sent = 0
            failed = 0

            for dest in destinations:
                config = dest.config if isinstance(dest.config, dict) else {}

                # Severity threshold filtering
                min_severity = str(config.get("min_severity", "info"))
                min_rank = severity_rank.get(min_severity, 0)
                if inc_rank < min_rank:
                    continue

                # Deduplication: check if alert already sent for this incident+destination
                existing = db.execute(
                    select(Alert.id).where(
                        Alert.incident_id == incident_id,
                        Alert.destination_id == dest.id,
                        Alert.status == "sent",
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    continue

                # Deliver
                dest_type = str(dest.destination_type)
                error = deliver(dest_type, config, payload)

                alert = Alert(
                    org_id=org_id,
                    incident_id=incident_id,
                    destination_id=dest.id,
                    status="sent" if error is None else "failed",
                    sent_at=datetime.now(timezone.utc) if error is None else None,
                    error_message=error,
                )
                db.add(alert)

                if error is None:
                    sent += 1
                else:
                    failed += 1
                    logger.warning(
                        "Alert delivery failed for dest %s: %s", dest.id, error
                    )

            db.commit()

            return {
                "status": "completed",
                "sent": sent,
                "failed": failed,
                "destinations_checked": len(destinations),
            }

        except Exception:
            logger.exception(
                "Alert task failed for incident %s", incident_id
            )
            db.rollback()
            raise self.retry()
