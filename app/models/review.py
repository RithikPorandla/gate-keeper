from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import uuid_pk


class Review(db.Model):
    """A human reviewer's decision on a needs_review application.

    time_to_decision_seconds is captured here (submitted_at -> decided_at) and is
    what powers the average / p95 review-time metric on the dashboard.
    """

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reviewers.id", ondelete="SET NULL"), nullable=True
    )

    action: Mapped[str] = mapped_column(String(16))  # approve|decline
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    decided_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    time_to_decision_seconds: Mapped[int | None] = mapped_column(nullable=True)

    application: Mapped["Application"] = relationship(back_populates="reviews")  # noqa: F821
    reviewer: Mapped["Reviewer"] = relationship()  # noqa: F821

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "application_id": str(self.application_id),
            "reviewer_id": str(self.reviewer_id) if self.reviewer_id else None,
            "action": self.action,
            "notes": self.notes,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "time_to_decision_seconds": self.time_to_decision_seconds,
        }
