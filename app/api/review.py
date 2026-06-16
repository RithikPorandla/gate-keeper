from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError

from app.api.auth import require_api_key
from app.repository.applications import get_application
from app.schemas.review import ReviewCreate
from app.services.review_service import ReviewError, perform_review

bp = Blueprint("review", __name__, url_prefix="/api/applications")


@bp.post("/<application_id>/review")
@require_api_key
def review_application(application_id: str):
    """A human reviewer approves or declines a needs_review application."""
    try:
        payload = ReviewCreate.model_validate(request.get_json(force=True))
    except ValidationError as exc:
        return jsonify({"error": "validation_error", "detail": exc.errors()}), 422

    application = get_application(application_id)
    if application is None:
        return jsonify({"error": "not_found"}), 404

    try:
        result = perform_review(application, g.reviewer, payload.action, payload.notes)
    except ReviewError as exc:
        return jsonify({"error": "invalid_state", "detail": exc.message}), exc.status_code

    return jsonify(result)
