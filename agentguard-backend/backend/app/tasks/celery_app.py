"""Celery application configuration."""

# pyright: reportArgumentType=false

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "agentguard",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.analysis",
        "app.tasks.alerting",
        "app.tasks.billing",
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
    "reset-monthly-usage": {
        "task": "app.tasks.billing.reset_monthly_usage",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    },
    "sync-subscription-status": {
        "task": "app.tasks.billing.sync_subscription_status",
        "schedule": crontab(hour=3, minute=0),
    },
}
