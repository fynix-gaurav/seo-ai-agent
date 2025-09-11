from celery import Celery

# Configure the Redis URL for Celery
# Assumes Redis is running on localhost:6379
REDIS_URL = "redis://localhost:6379/0"

celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"] # Points Celery to our tasks.py file
)

celery_app.conf.update(
    task_track_started=True,
)