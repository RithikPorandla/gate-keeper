"""The individual deterministic rules.

Each is a pure function of (application dict, RuleContext) -> RuleOutcome. No I/O
except the velocity rule, which reads/writes Redis counters via the context.
"""
from __future__ import annotations

import re
from typing import Any

from app.constants import Severity
from app.rules.base import RuleContext, RuleOutcome

_EIN_RE = re.compile(r"^\d{2}-?\d{7}$")


def kyb_completeness(app: dict[str, Any], ctx: RuleContext) -> RuleOutcome:
    cfg = ctx.config["kyb_completeness"]
    missing = [f for f in cfg["required_fields"] if not app.get(f)]
    ein_ok = bool(_EIN_RE.match(str(app.get("registration_number", ""))))
    passed = not missing and ein_ok
    return RuleOutcome(
        name="kyb_completeness",
        passed=passed,
        severity=Severity.LOW.value if passed else cfg["severity_on_fail"],
        detail={"missing_fields": missing, "ein_well_formed": ein_ok},
    )


def watchlist_check(app: dict[str, Any], ctx: RuleContext) -> RuleOutcome:
    cfg = ctx.config["watchlist"]
    name = str(app.get("applicant_name", "")).strip().lower()
    biz = str(app.get("business_name", "")).strip().lower()
    hit = name in ctx.watchlist or biz in ctx.watchlist
    return RuleOutcome(
        name="watchlist",
        passed=not hit,
        severity=cfg["severity_on_hit"] if hit else Severity.LOW.value,
        detail={"matched": name if name in ctx.watchlist else (biz if hit else None)},
    )


def country_risk(app: dict[str, Any], ctx: RuleContext) -> RuleOutcome:
    cfg = ctx.config["country_risk"]
    country = str(app.get("country", "")).upper()
    score = cfg["scores"].get(country, cfg["default_score"])
    passed = score < cfg["high_risk_threshold"]
    return RuleOutcome(
        name="country_risk",
        passed=passed,
        severity=Severity.LOW.value if passed else cfg["severity_on_fail"],
        detail={"country": country, "risk_score": score},
    )


def credit_threshold(app: dict[str, Any], ctx: RuleContext) -> RuleOutcome:
    cfg = ctx.config["credit_threshold"]
    score = app.get("mock_credit_score")
    if score is None:
        return RuleOutcome(
            name="credit_threshold",
            passed=False,
            severity=cfg["severity_when_missing"],
            detail={"reason": "missing_credit_score"},
        )
    passed = score >= cfg["minimum_score"]
    return RuleOutcome(
        name="credit_threshold",
        passed=passed,
        severity=Severity.LOW.value if passed else cfg["severity_on_fail"],
        detail={"score": score, "minimum": cfg["minimum_score"]},
    )


def velocity_check(app: dict[str, Any], ctx: RuleContext) -> RuleOutcome:
    """Flag the same EIN/email applying too often within a window.

    Uses Redis INCR + EXPIRE counters — this is where Redis earns its place. If no
    redis is wired in (e.g. a pure unit test), the rule passes (fail-open is safe
    here because it is a soft, severity-high signal, not a hard block).
    """
    cfg = ctx.config["velocity"]
    if ctx.redis is None:
        return RuleOutcome(name="velocity", passed=True, detail={"skipped": "no_redis"})

    ein = str(app.get("registration_number", "")).strip().lower()
    email = str(app.get("applicant_email", "")).strip().lower()
    window = int(cfg["window_seconds"])
    limit = int(cfg["max_within_window"])

    counts = {}
    breached = False
    for key_part in (f"ein:{ein}", f"email:{email}"):
        rkey = f"velocity:{key_part}"
        n = ctx.redis.incr(rkey)
        if n == 1:
            ctx.redis.expire(rkey, window)
        counts[key_part] = n
        if n > limit:
            breached = True

    return RuleOutcome(
        name="velocity",
        passed=not breached,
        severity=cfg["severity_on_fail"] if breached else Severity.LOW.value,
        detail={"counts": counts, "limit": limit, "window_seconds": window},
    )
