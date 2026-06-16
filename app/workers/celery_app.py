"""Celery application.

Run a worker with:
    celery -A app.workers.celery_app:celery worker --loglevel=info

Each task runs inside a Flask application context (lazily created once per worker
process) so models, the DB session, and config are all available.
"""
from __future__ import annotations

from celery import Celery

from app.config import get_settings

_settings = get_settings()

celery = Celery(
    "gatekeeper",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,  # redeliver if a worker dies mid-task (at-least-once)
    worker_prefetch_multiplier=1,  # fair dispatch across horizontally-scaled workers
    task_track_started=True,
)


class _ContextTask(celery.Task):
    """Base task that pushes a Flask app context around every run."""

    _flask_app = None

    def __call__(self, *args, **kwargs):
        if _ContextTask._flask_app is None:
            from app.main import create_app

            _ContextTask._flask_app = create_app(register_extensions_only=True)
        with _ContextTask._flask_app.app_context():
            return self.run(*args, **kwargs)


celery.Task = _ContextTask

# Import tasks so they register with this Celery app.
from app.workers import tasks  # noqa: E402,F401
