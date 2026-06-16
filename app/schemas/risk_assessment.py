from __future__ import annotations

from pydantic import BaseModel, Field

from app.constants import RecommendedAction


class RiskAssessment(BaseModel):
    """Strict schema for the LLM risk analyst's output.

    The analyst is required to return exactly this JSON shape. Any deviation fails
    validation and the pipeline falls back to needs_review (never auto-approve).
    """

    risk_score: float = Field(ge=0, le=100)
    recommended_action: RecommendedAction
    top_concerns: list[str] = Field(default_factory=list, max_length=10)
    rationale: str = Field(min_length=1, max_length=4000)

    # Provenance — filled in by the provider, not the model, so decisions are
    # reproducible after the fact.
    model_name: str | None = None
    model_version: str | None = None
