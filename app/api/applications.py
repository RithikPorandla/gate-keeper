from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from app.extensions import db, limiter
from app.config import get_settings
from app.repository.applications import create_application, get_application
from app.repository.audit import write_audit
from app.schemas.application import ApplicationCreate
from app.telemetry import metrics

bp = Blueprint("applications", __name__, url_prefix="/api/applications")


@bp.post("")
@limiter.limit(lambda: get_settings().intake_rate_limit)
def submit_application():
    """Accept an application, persist as pending, enqueue decisioning, return 202."""
    try:
        payload = ApplicationCreate.model_validate(request.get_json(force=True))
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "detail": exc.errors()}), 422

    idempotency_key = request.headers.get("Idempotency-Key")
    application, created = create_application(payload, idempotency_key)

    if created:
        write_audit("application", application.id, "system", "submitted", payload.model_dump(mode="json"))
        db.session.commit()
        metrics.applications_submitted_total.inc()

        # Enqueue async decisioning (import here to avoid loading Celery in tests
        # that don't need it).
        from app.workers.tasks import process_application

        process_application.delay(str(application.id))

    status_code = 202 if created else 200
    return jsonify({"id": str(application.id), "status": application.status}), status_code


@bp.get("/<application_id>")
def get_application_detail(application_id: str):
    """Return an application with its decision and rule results."""
    application = get_application(application_id)
    if application is None:
        return jsonify({"error": "not_found"}), 404

    return jsonify(
        {
            "application": application.to_dict(),
            "decision": application.decision.to_dict() if application.decision else None,
            "rule_results": [r.to_dict() for r in application.rule_results],
        }
    )
