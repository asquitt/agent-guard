"""Report generation tasks — placeholder for periodic reporting."""

from __future__ import annotations

import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.reports.generate_daily_report")
def generate_daily_report() -> dict[str, str]:
    """Generate a daily summary report. TODO: implement in a future session."""
    logger.info("generate_daily_report: stub — not yet implemented")
    return {"status": "stub"}
