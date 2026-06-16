"""Seed the database with a demo reviewer and synthetic applications.

Runs each application through the real decisioning pipeline inline (no Celery worker
required) so the dashboard and queue look alive immediately after `docker compose up`.

Usage:
    python -m scripts.seed
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.constants import ApplicationStatus
from app.extensions import db, redis_client
from app.main import create_app
from app.models import Application, Reviewer
from app.repository.audit import write_audit
from app.services.decision_service import run_pipeline

_DATA = Path(__file__).resolve().parents[1] / "data" / "sample_applications.json"


def ensure_demo_reviewer() -> Reviewer:
    settings = get_settings()
    key_hash = Reviewer.hash_key(settings.demo_reviewer_api_key)
    reviewer = db.session.scalar(select(Reviewer).where(Reviewer.api_key_hash == key_hash))
    if reviewer is None:
        reviewer = Reviewer(
            name="Demo Ops Reviewer",
            email="ops@gatekeeper.example",
            api_key_hash=key_hash,
        )
        db.session.add(reviewer)
        db.session.commit()
        print(f"Created demo reviewer (api key: {settings.demo_reviewer_api_key})")
    else:
        print("Demo reviewer already exists.")
    return reviewer


def seed_applications() -> None:
    samples = json.loads(_DATA.read_text(encoding="utf-8"))
    created = 0
    for sample in samples:
        data = {k: v for k, v in sample.items() if not k.startswith("_")}
        # Skip if an identical registration number already seeded (idempotent reseed).
        exists = db.session.scalar(
            select(Application).where(Application.registration_number == data["registration_number"])
        )
        if exists is not None:
            continue

        application = Application(
            business_name=data["business_name"],
            registration_number=data["registration_number"],
            country=data["country"],
            industry_code=data["industry_code"],
            requested_spend_limit=data["requested_spend_limit"],
            applicant_name=data["applicant_name"],
            applicant_email=data["applicant_email"],
            applicant_dob=data.get("applicant_dob"),
            mock_credit_score=data.get("mock_credit_score"),
            status=ApplicationStatus.PENDING.value,
        )
        db.session.add(application)
        db.session.flush()
        write_audit("application", application.id, "seed", "submitted", data)
        db.session.commit()

        result = run_pipeline(application, redis_client=redis_client)
        created += 1
        print(f"  {application.business_name:42s} -> {result.get('outcome')}")

    print(f"Seeded {created} new application(s).")


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()  # convenience for first run; migrations are the source of truth
        ensure_demo_reviewer()
        seed_applications()
        print("\nDone. Open http://localhost:8000/dashboard and /queue")


if __name__ == "__main__":
    main()
