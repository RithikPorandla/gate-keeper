from __future__ import annotations

import uuid

from sqlalchemy import select

from app.constants import ApplicationStatus
from app.extensions import db
from app.models import Application
from app.schemas.application import ApplicationCreate


def create_application(payload: ApplicationCreate, idempotency_key: str | None) -> tuple[Application, bool]:
    """Create an application, honouring an optional idempotency key.

    Returns (application, created). If an application with the same idempotency key
    already exists, returns it with created=False (no duplicate is made).
    """
    if idempotency_key:
        existing = db.session.scalar(
            select(Application).where(Application.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return existing, False

    app_row = Application(
        business_name=payload.business_name,
        registration_number=payload.registration_number,
        country=payload.country,
        industry_code=payload.industry_code,
        requested_spend_limit=payload.requested_spend_limit,
        applicant_name=payload.applicant_name,
        applicant_email=payload.applicant_email,
        applicant_dob=payload.applicant_dob,
        mock_credit_score=payload.mock_credit_score,
        status=ApplicationStatus.PENDING.value,
        idempotency_key=idempotency_key,
    )
    db.session.add(app_row)
    db.session.flush()  # populate app_row.id
    return app_row, True


def get_application(application_id: str | uuid.UUID) -> Application | None:
    return db.session.get(Application, _as_uuid(application_id))


def get_queue(limit: int = 50, offset: int = 0, sort: str = "risk") -> list[Application]:
    """needs_review applications, joined with their decision, sorted by risk or age."""
    from app.models import Decision

    stmt = (
        select(Application)
        .where(Application.status == ApplicationStatus.NEEDS_REVIEW.value)
        .join(Decision, Decision.application_id == Application.id, isouter=True)
    )
    if sort == "age":
        stmt = stmt.order_by(Application.submitted_at.asc())
    else:  # risk (highest first)
        stmt = stmt.order_by(Decision.combined_risk_score.desc().nullslast())
    stmt = stmt.limit(limit).offset(offset)
    return list(db.session.scalars(stmt))


def count_needs_review() -> int:
    from sqlalchemy import func

    return db.session.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.status == ApplicationStatus.NEEDS_REVIEW.value)
    ) or 0


def _as_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None
