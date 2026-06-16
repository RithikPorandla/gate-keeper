"""Validation tests for the request and LLM-output schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.constants import RecommendedAction
from app.schemas.application import ApplicationCreate
from app.schemas.risk_assessment import RiskAssessment


def _valid_app(**overrides):
    data = {
        "business_name": "Acme Co",
        "registration_number": "12-3456789",
        "country": "us",
        "industry_code": "5999",
        "requested_spend_limit": 5000,
        "applicant_name": "Jane Doe",
        "applicant_email": "jane@acme.example",
        "mock_credit_score": 700,
    }
    data.update(overrides)
    return data


def test_country_is_uppercased():
    app = ApplicationCreate.model_validate(_valid_app(country="gb"))
    assert app.country == "GB"


def test_negative_spend_limit_rejected():
    with pytest.raises(ValidationError):
        ApplicationCreate.model_validate(_valid_app(requested_spend_limit=-1))


def test_bad_email_rejected():
    with pytest.raises(ValidationError):
        ApplicationCreate.model_validate(_valid_app(applicant_email="not-an-email"))


def test_credit_score_out_of_range_rejected():
    with pytest.raises(ValidationError):
        ApplicationCreate.model_validate(_valid_app(mock_credit_score=9999))


def test_risk_assessment_score_bounds():
    with pytest.raises(ValidationError):
        RiskAssessment(
            risk_score=150,
            recommended_action=RecommendedAction.APPROVE,
            top_concerns=[],
            rationale="x",
        )
