from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.mixins import uuid_pk


class Decision(db.Model):
    """The merged outcome of the rule engine + LLM analyst for one application.

    The raw LLM structured output (recommendation, score, rationale, concerns,
    model name + version) is persisted so every decision is reproducible and
    explainable after the fact — the whole point in a compliance context.
    """

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True, unique=True
    )

    stage: Mapped[str] = mapped_column(String(32), default="automated")
    combined_risk_score: Mapped[float] = mapped_column()  # 0-100
    outcome: Mapped[str] = mapped_column(String(16))  # approved|declined|needs_review

    # Raw LLM output (nullable: a critical-rule hard block skips the LLM).
    llm_recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    llm_risk_score: Mapped[float | None] = mapped_column(nullable=True)
    llm_rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_top_concerns: Mapped[list | None] = mapped_column(db.JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    application: Mapped["Application"] = relationship(back_populates="decision")  # noqa: F821

    __table_args__ = (
        # Powers the metrics dashboard (outcomes over time).
        Index("ix_decisions_outcome_created", "outcome", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "application_id": str(self.application_id),
            "stage": self.stage,
            "combined_risk_score": self.combined_risk_score,
            "outcome": self.outcome,
            "llm_recommendation": self.llm_recommendation,
            "llm_risk_score": self.llm_risk_score,
            "llm_rationale": self.llm_rationale,
            "llm_top_concerns": self.llm_top_concerns,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
