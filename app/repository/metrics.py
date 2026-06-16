"""Database-derived metrics for the app's own dashboard.

Separate from the Prometheus metrics in app/telemetry — these are computed on demand
from the DB so the numbers are always exact and historical.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.constants import ApplicationStatus
from app.extensions import db
from app.models import Application, Decision, Review


def _count(stmt) -> int:
    return db.session.scalar(stmt) or 0


def metrics_summary() -> dict:
    total = _count(select(func.count()).select_from(Application))
    approved = _count(
        select(func.count())
        .select_from(Application)
        .where(Application.status == ApplicationStatus.APPROVED.value)
    )
    declined = _count(
        select(func.count())
        .select_from(Application)
        .where(Application.status == ApplicationStatus.DECLINED.value)
    )
    needs_review = _count(
        select(func.count())
        .select_from(Application)
        .where(Application.status == ApplicationStatus.NEEDS_REVIEW.value)
    )
    pending = _count(
        select(func.count())
        .select_from(Application)
        .where(Application.status == ApplicationStatus.PENDING.value)
    )

    decided = approved + declined + needs_review
    human_reviewed = _count(select(func.count()).select_from(Review))

    # Auto-decision rate = share of decided apps resolved without a human.
    auto_decided = max(0, decided - needs_review)
    auto_decision_rate = (auto_decided / decided) if decided else 0.0

    # Approval rate among automated outcomes (approved / (approved + declined)).
    auto_resolved = approved + declined
    approval_rate = (approved / auto_resolved) if auto_resolved else 0.0

    # Conversion = approved / submitted.
    conversion = (approved / total) if total else 0.0

    avg_review_seconds = db.session.scalar(
        select(func.avg(Review.time_to_decision_seconds))
    )

    return {
        "total_applications": total,
        "pending": pending,
        "approved": approved,
        "declined": declined,
        "needs_review": needs_review,
        "approval_rate": round(approval_rate, 4),
        "auto_decision_rate": round(auto_decision_rate, 4),
        "conversion": round(conversion, 4),
        "human_reviews": human_reviewed,
        "avg_review_time_seconds": round(float(avg_review_seconds), 1) if avg_review_seconds else None,
    }


def outcome_breakdown() -> dict[str, int]:
    rows = db.session.execute(
        select(Decision.outcome, func.count()).group_by(Decision.outcome)
    ).all()
    return {outcome: count for outcome, count in rows}


def recent_decisions(limit: int = 8) -> list[dict]:
    rows = db.session.execute(
        select(Application, Decision)
        .join(Decision, Application.id == Decision.application_id)
        .order_by(Decision.created_at.desc())
        .limit(limit)
    ).all()
    return [{"app": r[0], "decision": r[1]} for r in rows]
