"""Celery application configuration."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "agentguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.analysis",
        "app.tasks.reports",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "generate-daily-report": {
        "task": "app.tasks.reports.generate_daily_report",
        "schedule": 86400.0,  # Every 24 hours
    },
}
