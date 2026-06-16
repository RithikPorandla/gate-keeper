from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.repository.applications import count_needs_review, get_queue

bp = Blueprint("queue", __name__, url_prefix="/api/queue")


@bp.get("")
def list_queue():
    """List needs_review applications, sortable by risk score or age."""
    sort = request.args.get("sort", "risk")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    apps = get_queue(limit=limit, offset=offset, sort=sort)
    items = []
    for app_row in apps:
        decision = app_row.decision
        items.append(
            {
                "application": app_row.to_dict(),
                "combined_risk_score": decision.combined_risk_score if decision else None,
                "llm_top_concerns": decision.llm_top_concerns if decision else None,
                "llm_rationale": decision.llm_rationale if decision else None,
            }
        )
    return jsonify({"total_in_queue": count_needs_review(), "count": len(items), "items": items})
