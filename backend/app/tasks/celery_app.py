from celery import Celery
from app.config import settings

celery_app = Celery(
    "facebook_scraper",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # ONE task at a time to avoid overloading the bot
    worker_concurrency=1,
    worker_prefetch_multiplier=1,
    # Task routing
    task_routes={
        "app.tasks.scrape_task.scrape_profile": {"queue": "scrape_queue"},
        "app.tasks.scrape_task.cleanup_stale": {"queue": "scrape_queue"},
        "app.tasks.ingest_task.ingest_profile_json": {"queue": "ingest_queue"},
    },
    # Retry config
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Beat schedule (periodic cleanup of stale tasks)
celery_app.conf.beat_schedule = {
    "cleanup-stale-processing": {
        "task": "app.tasks.scrape_task.cleanup_stale",
        "schedule": 300.0,  # every 5 minutes
    },
}

# Auto-discover tasks — explicitly list the modules so Celery registers them
celery_app.autodiscover_tasks(["app.tasks.scrape_task", "app.tasks.ingest_task"], force=True)

# Ensure modules are imported so tasks are registered with the worker
import app.tasks.scrape_task  # noqa: F401, E402
import app.tasks.ingest_task  # noqa: F401, E402
