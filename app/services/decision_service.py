"""The core decisioning pipeline, independent of how it's triggered.

Used by both the Celery worker (async, in production) and the seed script (inline,
so the demo populates without a running worker). Keeping it here means there is a
single, tested code path from application to decision.
"""
from __future__ import annotations

import logging
import time

import redis as redis_lib

from app.constants import ApplicationStatus
from app.decisioning import decide
from app.extensions import db
from app.llm import get_risk_analyst
from app.models import Application, Decision, RuleResult
from app.repository.applications import count_needs_review
from app.repository.audit import write_audit
from app.rules import run_rules
from app.telemetry import get_tracer, metrics

logger = logging.getLogger(__name__)


def run_pipeline(application: Application, redis_client: redis_lib.Redis | None = None) -> dict:
    """Run rules -> LLM -> policy and persist the decision. Idempotent on status."""
    if application.status != ApplicationStatus.PENDING.value:
        return {"status": "already_processed", "outcome": application.status}

    started = time.perf_counter()
    tracer = get_tracer()
    app_data = application.to_dict()

    with tracer.start_as_current_span("rule_engine"):
        rule_outcomes = run_rules(app_data, redis_client=redis_client)

    with tracer.start_as_current_span("llm_assess"):
        analyst = get_risk_analyst(redis_client=redis_client)
        rule_dicts = [
            {"rule_name": r.name, "passed": r.passed, "severity": r.severity, "detail": r.detail}
            for r in rule_outcomes
        ]
        assessment = analyst.assess(app_data, rule_dicts)

    with tracer.start_as_current_span("decision_policy"):
        result = decide(rule_outcomes, assessment)

    for r in rule_outcomes:
        db.session.add(
            RuleResult(
                application_id=application.id,
                rule_name=r.name,
                passed=r.passed,
                severity=r.severity,
                detail=r.detail,
            )
        )
    db.session.add(
        Decision(
            application_id=application.id,
            stage="automated",
            combined_risk_score=result.combined_risk_score,
            outcome=result.outcome,
            llm_recommendation=assessment.recommended_action.value,
            llm_risk_score=assessment.risk_score,
            llm_rationale=assessment.rationale,
            llm_top_concerns=assessment.top_concerns,
            model_name=assessment.model_name,
            model_version=assessment.model_version,
        )
    )
    application.status = result.outcome
    write_audit(
        entity="application",
        entity_id=application.id,
        actor="system",
        action="decided",
        payload={
            "outcome": result.outcome,
            "combined_risk_score": result.combined_risk_score,
            "reason": result.reason,
            "llm_recommendation": assessment.recommended_action.value,
        },
    )
    db.session.commit()

    metrics.decisions_total.labels(outcome=result.outcome, stage="automated").inc()
    metrics.decision_latency_seconds.observe(time.perf_counter() - started)
    metrics.review_queue_depth.set(count_needs_review())

    logger.info("Decided application %s -> %s", application.id, result.outcome)
    return {
        "status": "decided",
        "application_id": str(application.id),
        "outcome": result.outcome,
        "combined_risk_score": result.combined_risk_score,
    }
