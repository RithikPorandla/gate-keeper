"""Anthropic Claude risk analyst.

Uses the official Anthropic SDK and structured outputs (`messages.parse`) so the
model is constrained to the required JSON shape. Fails safe to a review
recommendation on any error, timeout, or malformed output — never auto-approve.
"""
from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.config import get_settings
from app.constants import RecommendedAction
from app.llm.base import RiskAnalyst
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas.risk_assessment import RiskAssessment

logger = logging.getLogger(__name__)


class _LLMRiskOutput(BaseModel):
    """The exact shape the model must return (no provenance fields — we add those)."""

    risk_score: float = Field(ge=0, le=100)
    recommended_action: RecommendedAction
    top_concerns: list[str]
    rationale: str


def _fail_safe(reason: str) -> RiskAssessment:
    """Conservative assessment used whenever the model can't be trusted."""
    return RiskAssessment(
        risk_score=50.0,
        recommended_action=RecommendedAction.REVIEW,
        top_concerns=[f"LLM assessment unavailable: {reason}"],
        rationale=(
            "The automated risk analyst could not produce a valid assessment, so "
            "this application is routed to a human reviewer (fail-safe)."
        ),
        model_name="fail-safe",
        model_version="1",
    )


class AnthropicProvider(RiskAnalyst):
    name = "anthropic"

    def __init__(self) -> None:
        # Imported lazily so the package imports even when `anthropic` isn't needed
        # (e.g. when running with the mock provider).
        import anthropic

        settings = get_settings()
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        # api_key falls back to the ANTHROPIC_API_KEY env var if unset.
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key or None,
            timeout=self._timeout,
        )

    def assess(
        self,
        application: dict[str, Any],
        rule_results: list[dict[str, Any]],
    ) -> RiskAssessment:
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(application, rule_results)}],
                output_format=_LLMRiskOutput,
            )
            parsed = response.parsed_output
            if parsed is None:
                return _fail_safe("model returned no parseable output")
            return RiskAssessment(
                risk_score=parsed.risk_score,
                recommended_action=parsed.recommended_action,
                top_concerns=parsed.top_concerns[:10],
                rationale=parsed.rationale[:4000],
                model_name=getattr(response, "model", self._model),
                model_version=self._model,
            )
        except Exception as exc:  # noqa: BLE001 — fail safe on ANY provider error
            logger.warning("LLM risk assessment failed: %s", exc, exc_info=True)
            return _fail_safe(type(exc).__name__)
