"""Celery task wrapping the decisioning pipeline.

The actual work lives in app.services.decision_service.run_pipeline so the worker
and the seed script share one implementation. Idempotent + acks_late => Celery's
at-least-once delivery is safe.
"""
from __future__ import annotations

import logging

from app.extensions import redis_client
from app.repository.applications import get_application
from app.services.decision_service import run_pipeline
from app.workers.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="gatekeeper.process_application", bind=True, max_retries=3, default_retry_delay=10)
def process_application(self, application_id: str) -> dict:
    application = get_application(application_id)
    if application is None:
        logger.error("Application %s not found", application_id)
        return {"status": "not_found", "application_id": str(application_id)}

    try:
        return run_pipeline(application, redis_client=redis_client)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline failed for %s; retrying", application_id)
        raise self.retry(exc=exc)
