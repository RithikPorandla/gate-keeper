"""Integration test for the decisioning pipeline (mock LLM, fake redis, sqlite)."""
from __future__ import annotations

from app.constants import ApplicationStatus, Outcome
from app.extensions import db, redis_client
from app.models import Application, AuditLog, Decision, RuleResult
from app.services.decision_service import run_pipeline


def _make_application(**overrides) -> Application:
    data = {
        "business_name": "Acme Co",
        "registration_number": "12-3456789",
        "country": "US",
        "industry_code": "5999",
        "requested_spend_limit": 5000,
        "applicant_name": "Jane Doe",
        "applicant_email": "jane@acme.example",
        "mock_credit_score": 760,
        "status": ApplicationStatus.PENDING.value,
    }
    data.update(overrides)
    app_row = Application(**data)
    db.session.add(app_row)
    db.session.commit()
    return app_row


def test_clean_application_is_approved(app):
    app_row = _make_application()
    result = run_pipeline(app_row, redis_client=redis_client)
    assert result["outcome"] == Outcome.APPROVED.value
    assert app_row.status == Outcome.APPROVED.value
    # Decision + rule results + audit rows were persisted.
    assert db.session.get(Decision, app_row.decision.id) is not None
    assert db.session.query(RuleResult).filter_by(application_id=app_row.id).count() == 5
    assert db.session.query(AuditLog).filter_by(entity_id=str(app_row.id), action="decided").count() == 1


def test_watchlist_application_is_declined(app):
    app_row = _make_application(
        business_name="Shadowfront Holdings",
        applicant_name="Ivan Q. Blocklisted",
    )
    result = run_pipeline(app_row, redis_client=redis_client)
    assert result["outcome"] == Outcome.DECLINED.value
    assert result["combined_risk_score"] == 100.0


def test_missing_credit_routes_to_review(app):
    app_row = _make_application(mock_credit_score=None)
    result = run_pipeline(app_row, redis_client=redis_client)
    assert result["outcome"] in {Outcome.NEEDS_REVIEW.value, Outcome.DECLINED.value}


def test_pipeline_is_idempotent(app):
    app_row = _make_application()
    run_pipeline(app_row, redis_client=redis_client)
    second = run_pipeline(app_row, redis_client=redis_client)
    assert second["status"] == "already_processed"
    assert db.session.query(Decision).filter_by(application_id=app_row.id).count() == 1
