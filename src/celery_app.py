from celery import Celery
import os

celery_app = Celery(
    "ci_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "tasks.scrape_high": {"queue": "high-priority"},
        "tasks.scrape_low": {"queue": "low-priority"},
        "tasks.scrape_competitor_task": {"queue": "high-priority"},
    },
    task_annotations={"tasks.scrape_*": {"rate_limit": "10/m"}},
)

