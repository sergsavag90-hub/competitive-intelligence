from celery import Celery
from celery.schedules import crontab
import os

celery_app = Celery(
    "ci_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=["src.tasks.scraping_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_rate_limit="100/m",
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    result_persistent=True,
    worker_hijack_root_logger=False,
    task_routes={
        "tasks.scrape_high": {"queue": "high-priority"},
        "tasks.scrape_low": {"queue": "low-priority"},
        "tasks.scrape_competitor_task": {"queue": "high-priority"},
    },
    task_annotations={"tasks.scrape_*": {"rate_limit": "10/m"}},
    beat_schedule={
        "daily-scan-placeholder": {
            "task": "tasks.scrape_competitor_task",
            "schedule": crontab(hour=3, minute=0),
            "args": (1, ["seo"]),  # replace with real competitor id/modules in staging
            "options": {"queue": "low-priority"},
        }
    },
)
