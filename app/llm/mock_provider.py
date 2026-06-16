"""Deterministic mock risk analyst.

Lets the entire pipeline (and the test suite) run offline with no API key. The
score is derived from the rule results so the mock behaves plausibly: more / more
severe rule failures → higher risk → a decline or review recommendation.
"""
from __future__ import annotations

from typing import Any

from app.constants import SEVERITY_WEIGHT, RecommendedAction
from app.llm.base import RiskAnalyst
from app.schemas.risk_assessment import RiskAssessment


class MockProvider(RiskAnalyst):
    name = "mock"

    def assess(
        self,
        application: dict[str, Any],
        rule_results: list[dict[str, Any]],
    ) -> RiskAssessment:
        failed = [r for r in rule_results if not r.get("passed")]
        # Risk score = capped sum of failed-rule severity weights.
        raw = sum(SEVERITY_WEIGHT.get(r.get("severity", "low"), 5) for r in failed)
        score = float(min(100, raw))

        if any(r.get("severity") == "critical" for r in failed):
            action = RecommendedAction.DECLINE
        elif score >= 60:
            action = RecommendedAction.DECLINE
        elif score >= 25:
            action = RecommendedAction.REVIEW
        else:
            action = RecommendedAction.APPROVE

        concerns = [f"{r['rule_name']} failed ({r.get('severity')})" for r in failed][:5]
        rationale = (
            f"Deterministic mock assessment: {len(failed)} rule(s) failed "
            f"with a combined severity score of {score:.0f}/100."
        )
        return RiskAssessment(
            risk_score=score,
            recommended_action=action,
            top_concerns=concerns,
            rationale=rationale,
            model_name="mock",
            model_version="1",
        )
