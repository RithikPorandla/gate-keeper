from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import uuid_pk


class RuleResult(db.Model):
    """The outcome of a single deterministic rule for one application.

    One row per rule makes each decision auditable down to which rule fired and why.
    """

    __tablename__ = "rule_results"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )

    rule_name: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(Boolean)
    severity: Mapped[str] = mapped_column(String(16))  # low|medium|high|critical
    detail: Mapped[dict | None] = mapped_column(db.JSON, nullable=True)

    application: Mapped["Application"] = relationship(back_populates="rule_results")  # noqa: F821

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }
