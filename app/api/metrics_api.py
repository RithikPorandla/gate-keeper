from __future__ import annotations

from flask import Blueprint, jsonify

from app.api.auth import require_api_key
from app.repository.metrics import metrics_summary, outcome_breakdown

bp = Blueprint("metrics_api", __name__, url_prefix="/api/metrics")


@bp.get("/summary")
@require_api_key
def summary():
    """Approval rate, auto-decision rate, average review time, conversion, etc."""
    data = metrics_summary()
    data["outcome_breakdown"] = outcome_breakdown()
    return jsonify(data)
