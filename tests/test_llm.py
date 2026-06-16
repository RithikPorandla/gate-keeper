"""Tests for the risk analyst providers."""
from __future__ import annotations

from app.constants import RecommendedAction
from app.llm.mock_provider import MockProvider


def _rules(failed=None):
    failed = failed or []
    base = [{"rule_name": "kyb", "passed": True, "severity": "low", "detail": {}}]
    return base + failed


def test_mock_clean_app_recommends_approve():
    assessment = MockProvider().assess({"business_name": "x"}, _rules())
    assert assessment.recommended_action == RecommendedAction.APPROVE
    assert assessment.risk_score < 25


def test_mock_critical_failure_recommends_decline():
    failed = [{"rule_name": "watchlist", "passed": False, "severity": "critical", "detail": {}}]
    assessment = MockProvider().assess({"business_name": "x"}, _rules(failed))
    assert assessment.recommended_action == RecommendedAction.DECLINE
    assert assessment.risk_score >= 60


def test_anthropic_provider_fails_safe_to_review(monkeypatch):
    """If the SDK call raises, the provider returns a review recommendation."""
    from app.llm import anthropic_provider

    class _BoomClient:
        class messages:  # noqa: N801
            @staticmethod
            def parse(**kwargs):
                raise RuntimeError("simulated API failure")

    provider = anthropic_provider.AnthropicProvider.__new__(anthropic_provider.AnthropicProvider)
    provider._client = _BoomClient()
    provider._model = "claude-sonnet-4-6"
    provider._timeout = 5

    assessment = provider.assess({"business_name": "x"}, _rules())
    assert assessment.recommended_action == RecommendedAction.REVIEW
    assert assessment.model_name == "fail-safe"
