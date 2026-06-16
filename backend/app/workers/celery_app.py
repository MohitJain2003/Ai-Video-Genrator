"""
Celery application configuration.
"""

import redis
from celery import Celery
from app.config import get_settings

settings = get_settings()

def _check_redis_up() -> bool:
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        return True
    except Exception:
        return False

# Determine eager mode
is_redis_up = _check_redis_up()
force_eager = not is_redis_up

# Create initial Celery app depending on Redis availability
if force_eager:
    celery_app = Celery(
        "reelgen",
        broker="memory://",
        backend="cache+memory://",
        include=["app.workers.tasks"],
    )
else:
    celery_app = Celery(
        "reelgen",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.workers.tasks"],
    )
    # Check if there are active workers
    try:
        i = celery_app.control.inspect(timeout=0.5)
        stats = i.stats() if i else None
        if not stats:
            force_eager = True
    except Exception:
        force_eager = True

# Update Celery settings
celery_app.conf.update(
    task_always_eager=force_eager,
    task_eager_propagates=force_eager,
    broker_url="memory://" if force_eager else settings.redis_url,
    result_backend="cache+memory://" if force_eager else settings.redis_url,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (memory cleanup)
    worker_concurrency=2,  # 2 concurrent tasks per worker

    # Task execution limits
    task_soft_time_limit=600,   # 10 minutes soft limit
    task_time_limit=900,        # 15 minutes hard limit

    # Retry settings
    task_acks_late=True,  # Acknowledge after task completes (crash safety)
    task_reject_on_worker_lost=True,

    # Result settings
    result_expires=86400,  # Results expire after 24 hours
)

