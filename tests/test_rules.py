"""Unit tests for the deterministic rule engine. No DB / no network."""
from __future__ import annotations

import fakeredis
import pytest

from app.rules import checks, run_rules
from app.rules.base import RuleContext
from app.rules.config import load_rules_config


@pytest.fixture()
def ctx():
    return RuleContext(
        config=load_rules_config(),
        redis=fakeredis.FakeStrictRedis(decode_responses=True),
        watchlist={"ivan q. blocklisted", "shadowfront holdings"},
    )


def _base_app(**overrides):
    app = {
        "business_name": "Acme Co",
        "registration_number": "12-3456789",
        "country": "US",
        "industry_code": "5999",
        "applicant_name": "Jane Doe",
        "applicant_email": "jane@acme.example",
        "mock_credit_score": 720,
    }
    app.update(overrides)
    return app


def test_kyb_completeness_passes_for_complete_app(ctx):
    result = checks.kyb_completeness(_base_app(), ctx)
    assert result.passed is True
    assert result.severity == "low"


def test_kyb_completeness_fails_on_bad_ein(ctx):
    result = checks.kyb_completeness(_base_app(registration_number="not-an-ein"), ctx)
    assert result.passed is False
    assert result.detail["ein_well_formed"] is False


def test_watchlist_hit_is_critical(ctx):
    result = checks.watchlist_check(_base_app(applicant_name="Ivan Q. Blocklisted"), ctx)
    assert result.passed is False
    assert result.severity == "critical"


def test_watchlist_clean_passes(ctx):
    result = checks.watchlist_check(_base_app(), ctx)
    assert result.passed is True


def test_country_risk_high_fails(ctx):
    result = checks.country_risk(_base_app(country="RU"), ctx)
    assert result.passed is False
    assert result.detail["risk_score"] >= 60


def test_credit_below_threshold_fails(ctx):
    result = checks.credit_threshold(_base_app(mock_credit_score=500), ctx)
    assert result.passed is False


def test_missing_credit_fails(ctx):
    result = checks.credit_threshold(_base_app(mock_credit_score=None), ctx)
    assert result.passed is False
    assert result.detail["reason"] == "missing_credit_score"


def test_velocity_trips_after_limit(ctx):
    app = _base_app()
    # Limit is 3 within the window; the 4th application should fail.
    outcomes = [checks.velocity_check(app, ctx) for _ in range(4)]
    assert outcomes[0].passed is True
    assert outcomes[-1].passed is False


def test_run_rules_returns_all_registered():
    outcomes = run_rules(_base_app(), redis_client=None)
    names = {o.name for o in outcomes}
    assert names == {"kyb_completeness", "watchlist", "country_risk", "credit_threshold", "velocity"}
