"""Human-review business logic, shared by the JSON API and the Jinja ops UI.

Keeping this in one place means the audit trail, metrics, and state transitions are
identical regardless of which surface a reviewer acts through — important for a
compliance-oriented system where every decision must be recorded the same way.
"""
from __future__ import annotations

import datetime as dt

from app.constants import ApplicationStatus, Outcome, ReviewAction
from app.extensions import db
from app.models import Application, Review, Reviewer
from app.repository.applications import count_needs_review
from app.repository.audit import write_audit
from app.telemetry import metrics


class ReviewError(Exception):
    """Raised when an application can't be reviewed in its current state."""

    def __init__(self, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def perform_review(
    application: Application,
    reviewer: Reviewer,
    action: ReviewAction,
    notes: str | None,
) -> dict:
    """Apply a reviewer's approve/decline decision, recording it fully and auditably."""
    if application.status != ApplicationStatus.NEEDS_REVIEW.value:
        raise ReviewError(f"application is {application.status}, not needs_review", 409)

    now = dt.datetime.now(dt.timezone.utc)
    submitted = application.submitted_at
    if submitted is not None and submitted.tzinfo is None:
        submitted = submitted.replace(tzinfo=dt.timezone.utc)
    ttd = int((now - submitted).total_seconds()) if submitted else None

    new_status = (
        Outcome.APPROVED.value if action == ReviewAction.APPROVE else Outcome.DECLINED.value
    )
    application.status = new_status

    db.session.add(
        Review(
            application_id=application.id,
            reviewer_id=reviewer.id,
            action=action.value,
            notes=notes,
            decided_at=now,
            time_to_decision_seconds=ttd,
        )
    )
    write_audit(
        entity="application",
        entity_id=application.id,
        actor=reviewer.email,
        action="reviewed",
        payload={"action": action.value, "new_status": new_status, "notes": notes},
    )
    db.session.commit()

    metrics.decisions_total.labels(outcome=new_status, stage="human").inc()
    metrics.review_queue_depth.set(count_needs_review())

    return {
        "id": str(application.id),
        "status": new_status,
        "reviewer": reviewer.to_dict(),
        "time_to_decision_seconds": ttd,
    }
