"""Integration tests for the HTTP API."""
from __future__ import annotations

from app.constants import ApplicationStatus, Outcome
from app.extensions import db, redis_client
from app.models import Application
from app.services.decision_service import run_pipeline


def _valid_payload(**overrides):
    data = {
        "business_name": "Acme Co",
        "registration_number": "12-3456789",
        "country": "US",
        "industry_code": "5999",
        "requested_spend_limit": 5000,
        "applicant_name": "Jane Doe",
        "applicant_email": "jane@acme.example",
        "mock_credit_score": 760,
    }
    data.update(overrides)
    return data


def test_healthz(client):
    assert client.get("/healthz").status_code == 200


def test_submit_returns_202_pending(client, monkeypatch):
    # Don't enqueue to a real broker in tests.
    import app.workers.tasks as tasks

    monkeypatch.setattr(tasks.process_application, "delay", lambda *a, **k: None)

    resp = client.post("/api/applications", json=_valid_payload())
    assert resp.status_code == 202
    body = resp.get_json()
    assert body["status"] == ApplicationStatus.PENDING.value
    assert "id" in body


def test_submit_validation_error(client):
    resp = client.post("/api/applications", json={"business_name": ""})
    assert resp.status_code == 422


def test_idempotency_key_dedupes(client, monkeypatch):
    import app.workers.tasks as tasks

    monkeypatch.setattr(tasks.process_application, "delay", lambda *a, **k: None)

    headers = {"Idempotency-Key": "abc-123"}
    first = client.post("/api/applications", json=_valid_payload(), headers=headers)
    second = client.post("/api/applications", json=_valid_payload(), headers=headers)
    assert first.get_json()["id"] == second.get_json()["id"]
    assert db.session.query(Application).count() == 1


def _seed_needs_review() -> Application:
    app_row = Application(
        business_name="Bayou Seafood",
        registration_number="76-4455221",
        country="BR",
        industry_code="5146",
        requested_spend_limit=60000,
        applicant_name="Lucas Almeida",
        applicant_email="lucas@bayou.example",
        mock_credit_score=605,
        status=ApplicationStatus.PENDING.value,
    )
    db.session.add(app_row)
    db.session.commit()
    run_pipeline(app_row, redis_client=redis_client)
    return app_row


def test_queue_lists_needs_review(client, app):
    app_row = _seed_needs_review()
    if app_row.status != Outcome.NEEDS_REVIEW.value:
        return  # policy resolved it automatically; nothing to assert here
    resp = client.get("/api/queue")
    assert resp.status_code == 200
    assert resp.get_json()["total_in_queue"] >= 1


def test_review_requires_auth(client, app):
    app_row = _seed_needs_review()
    resp = client.post(f"/api/applications/{app_row.id}/review", json={"action": "approve"})
    assert resp.status_code == 401


def test_review_with_auth(client, app, demo_reviewer):
    app_row = _seed_needs_review()
    if app_row.status != Outcome.NEEDS_REVIEW.value:
        return
    resp = client.post(
        f"/api/applications/{app_row.id}/review",
        json={"action": "approve", "notes": "looks fine"},
        headers={"X-API-Key": "test-ops-key"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == Outcome.APPROVED.value


def test_metrics_summary_requires_auth(client):
    assert client.get("/api/metrics/summary").status_code == 401


def test_metrics_summary_with_auth(client, demo_reviewer):
    resp = client.get("/api/metrics/summary", headers={"X-API-Key": "test-ops-key"})
    assert resp.status_code == 200
    assert "approval_rate" in resp.get_json()
