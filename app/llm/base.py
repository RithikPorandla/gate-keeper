from __future__ import annotations

import abc
from typing import Any

from app.schemas.risk_assessment import RiskAssessment


class RiskAnalyst(abc.ABC):
    """Interface for the LLM risk analyst.

    The rest of the system depends only on this interface, never on a vendor SDK,
    so providers (mock, Anthropic, ...) are swappable via config.
    """

    name: str = "base"

    @abc.abstractmethod
    def assess(
        self,
        application: dict[str, Any],
        rule_results: list[dict[str, Any]],
    ) -> RiskAssessment:
        """Return a structured risk assessment for an application + its rule results.

        Implementations MUST fail safe: on any error, timeout, or malformed output,
        return an assessment recommending review rather than raising.
        """
        raise NotImplementedError
