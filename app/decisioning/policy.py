"""The decision policy — merges deterministic rules with the LLM assessment.

This is the architecturally important bit: the LLM augments and explains, but the
rule engine holds veto power over hard blocks, and humans review on disagreement.
The LLM never has unilateral authority to approve.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.constants import SEVERITY_WEIGHT, Outcome, Severity
from app.rules.base import RuleOutcome
from app.schemas.risk_assessment import RiskAssessment

_POLICY_YAML = Path(__file__).with_name("policy.yaml")


@lru_cache
def load_policy_config() -> dict[str, Any]:
    with _POLICY_YAML.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class DecisionResult:
    outcome: str
    combined_risk_score: float
    rule_score: float
    reason: str


def rule_derived_score(rule_results: list[RuleOutcome]) -> float:
    """Capped sum of failed-rule severity weights, 0-100."""
    raw = sum(
        SEVERITY_WEIGHT.get(r.severity, 5) for r in rule_results if not r.passed
    )
    return float(min(100, raw))


def decide(
    rule_results: list[RuleOutcome],
    assessment: RiskAssessment,
    config: dict[str, Any] | None = None,
) -> DecisionResult:
    cfg = config or load_policy_config()
    weights = cfg["weights"]
    thresholds = cfg["thresholds"]

    # 1. Critical rule failure -> hard block. LLM is ignored.
    critical = [r for r in rule_results if not r.passed and r.severity == Severity.CRITICAL.value]
    if critical:
        names = ", ".join(r.name for r in critical)
        return DecisionResult(
            outcome=Outcome.DECLINED.value,
            combined_risk_score=100.0,
            rule_score=100.0,
            reason=f"Hard block: critical rule(s) failed: {names}",
        )

    # 2. Combined score = weighted blend of rule-derived risk and the LLM score.
    r_score = rule_derived_score(rule_results)
    llm_score = float(assessment.risk_score)
    combined = weights["rules"] * r_score + weights["llm"] * llm_score

    # 3. Human-in-the-loop on significant rule/LLM disagreement.
    if abs(r_score - llm_score) > cfg["disagreement_delta"]:
        return DecisionResult(
            outcome=Outcome.NEEDS_REVIEW.value,
            combined_risk_score=round(combined, 2),
            rule_score=r_score,
            reason=(
                f"Rule score ({r_score:.0f}) and LLM score ({llm_score:.0f}) disagree "
                "significantly — routed to human review."
            ),
        )

    # 4. Threshold routing.
    if combined < thresholds["auto_approve_below"]:
        outcome, reason = Outcome.APPROVED.value, "Low combined risk — auto-approved."
    elif combined > thresholds["auto_decline_above"]:
        outcome, reason = Outcome.DECLINED.value, "High combined risk — auto-declined."
    else:
        outcome, reason = Outcome.NEEDS_REVIEW.value, "Mid-range risk — routed to human review."

    return DecisionResult(
        outcome=outcome,
        combined_risk_score=round(combined, 2),
        rule_score=r_score,
        reason=reason,
    )
