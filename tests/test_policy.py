"""Unit tests for the decision policy. No DB / no network."""
from __future__ import annotations

from app.constants import Outcome, RecommendedAction, Severity
from app.decisioning import decide
from app.rules.base import RuleOutcome
from app.schemas.risk_assessment import RiskAssessment


def _assessment(score, action=RecommendedAction.APPROVE):
    return RiskAssessment(
        risk_score=score,
        recommended_action=action,
        top_concerns=[],
        rationale="test",
    )


def _passing_rules():
    return [RuleOutcome(name=n, passed=True, severity=Severity.LOW.value) for n in ("a", "b", "c")]


def test_critical_rule_is_hard_block_ignoring_llm():
    rules = _passing_rules() + [
        RuleOutcome(name="watchlist", passed=False, severity=Severity.CRITICAL.value)
    ]
    # Even with an approve recommendation and a low LLM score:
    result = decide(rules, _assessment(0, RecommendedAction.APPROVE))
    assert result.outcome == Outcome.DECLINED.value
    assert result.combined_risk_score == 100.0


def test_low_risk_auto_approves():
    result = decide(_passing_rules(), _assessment(5))
    assert result.outcome == Outcome.APPROVED.value


def test_high_risk_auto_declines():
    # Rules and the LLM agree on high risk (so no disagreement override): two high
    # failures -> rule score 90, LLM 90 -> combined 90 > auto_decline_above.
    rules = _passing_rules() + [
        RuleOutcome(name="country_risk", passed=False, severity=Severity.HIGH.value),
        RuleOutcome(name="credit_threshold", passed=False, severity=Severity.HIGH.value),
    ]
    result = decide(rules, _assessment(90, RecommendedAction.DECLINE))
    assert result.outcome == Outcome.DECLINED.value


def test_mid_range_routes_to_review():
    rules = _passing_rules() + [
        RuleOutcome(name="credit_threshold", passed=False, severity=Severity.MEDIUM.value)
    ]
    result = decide(rules, _assessment(40, RecommendedAction.REVIEW))
    assert result.outcome == Outcome.NEEDS_REVIEW.value


def test_significant_disagreement_routes_to_review():
    # Rules say clean (score 0) but the LLM is very worried (score 90) -> review.
    result = decide(_passing_rules(), _assessment(90, RecommendedAction.DECLINE))
    assert result.outcome == Outcome.NEEDS_REVIEW.value
    assert "disagree" in result.reason.lower()
