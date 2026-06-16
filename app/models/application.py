from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import ApplicationStatus
from app.extensions import db
from app.models.mixins import uuid_pk


class Application(db.Model):
    """A submitted business onboarding application.

    The applicant_* and mock_credit_score fields are SYNTHETIC demo data — this is
    a demonstration of decisioning architecture, not a real KYB/AML system.
    """

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Business / KYB fields
    business_name: Mapped[str] = mapped_column(String(255))
    registration_number: Mapped[str] = mapped_column(String(64), index=True)  # EIN-like
    country: Mapped[str] = mapped_column(String(2))  # ISO-3166 alpha-2
    industry_code: Mapped[str] = mapped_column(String(16))
    requested_spend_limit: Mapped[float] = mapped_column(Numeric(12, 2))

    # Applicant identity (synthetic)
    applicant_name: Mapped[str] = mapped_column(String(255))
    applicant_email: Mapped[str] = mapped_column(String(255), index=True)
    applicant_dob: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    mock_credit_score: Mapped[int | None] = mapped_column(nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(16), default=ApplicationStatus.PENDING.value)
    submitted_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Idempotency: a duplicate POST with the same key returns the existing record
    # instead of creating a second application. Safe under retries / at scale.
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)

    # Relationships
    decision: Mapped["Decision | None"] = relationship(  # noqa: F821
        back_populates="application", uselist=False, cascade="all, delete-orphan"
    )
    rule_results: Mapped[list["RuleResult"]] = relationship(  # noqa: F821
        back_populates="application", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        back_populates="application", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Powers the ops queue (filter by status, order by age).
        Index("ix_applications_status_submitted", "status", "submitted_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "business_name": self.business_name,
            "registration_number": self.registration_number,
            "country": self.country,
            "industry_code": self.industry_code,
            "requested_spend_limit": float(self.requested_spend_limit),
            "applicant_name": self.applicant_name,
            "applicant_email": self.applicant_email,
            "applicant_dob": self.applicant_dob,
            "mock_credit_score": self.mock_credit_score,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
        }
