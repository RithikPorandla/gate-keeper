from __future__ import annotations

from typing import Any

import redis as redis_lib

from app.rules import checks
from app.rules.base import Rule, RuleContext, RuleOutcome
from app.rules.config import load_rules_config, load_watchlist

# Registry of active rules, in evaluation order. Adding a rule = one line here plus
# its function in checks.py.
REGISTERED_RULES: list[Rule] = [
    checks.kyb_completeness,
    checks.watchlist_check,
    checks.country_risk,
    checks.credit_threshold,
    checks.velocity_check,
]


def run_rules(
    app: dict[str, Any],
    redis_client: redis_lib.Redis | None = None,
) -> list[RuleOutcome]:
    """Run every registered rule against an application and return their outcomes."""
    ctx = RuleContext(
        config=load_rules_config(),
        redis=redis_client,
        watchlist=set(load_watchlist()),
    )
    return [rule(app, ctx) for rule in REGISTERED_RULES]
