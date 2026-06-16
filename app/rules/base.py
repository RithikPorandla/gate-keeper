from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import redis as redis_lib

from app.constants import Severity


@dataclass
class RuleOutcome:
    """The result of evaluating one rule. Mirrors the RuleResult model row."""

    name: str
    passed: bool
    severity: str = Severity.LOW.value
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleContext:
    """Side inputs a rule may need beyond the application itself.

    Keeping these in a context object means each rule stays a pure-ish function of
    (application, context) and is trivially unit-testable with a fake redis.
    """

    config: dict[str, Any]
    redis: redis_lib.Redis | None = None
    watchlist: set[str] = field(default_factory=set)


# A rule is a callable taking the application dict + context and returning an outcome.
Rule = Callable[[dict[str, Any], RuleContext], RuleOutcome]
