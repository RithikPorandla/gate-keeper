"""Redis-backed caching wrapper for any RiskAnalyst.

Identical (application, rule_results) inputs produce the same assessment, so we
cache by a hash of the inputs to control LLM cost. Cache failures never break the
pipeline — they just fall through to a live assessment.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis as redis_lib

from app.llm.base import RiskAnalyst
from app.schemas.risk_assessment import RiskAssessment

logger = logging.getLogger(__name__)


class CachingRiskAnalyst(RiskAnalyst):
    def __init__(self, inner: RiskAnalyst, redis_client: redis_lib.Redis, ttl_seconds: int) -> None:
        self._inner = inner
        self._redis = redis_client
        self._ttl = ttl_seconds
        self.name = f"cached:{inner.name}"

    @staticmethod
    def _key(application: dict[str, Any], rule_results: list[dict[str, Any]]) -> str:
        # Drop volatile fields (ids, timestamps) so logically-identical apps share a key.
        app_view = {k: v for k, v in application.items() if k not in {"id", "submitted_at", "status"}}
        blob = json.dumps(
            {"app": app_view, "rules": rule_results}, sort_keys=True, default=str
        )
        digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
        return f"assessment:{digest}"

    def assess(
        self,
        application: dict[str, Any],
        rule_results: list[dict[str, Any]],
    ) -> RiskAssessment:
        key = self._key(application, rule_results)
        try:
            cached = self._redis.get(key)
            if cached:
                return RiskAssessment.model_validate_json(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("assessment cache read failed: %s", exc)

        assessment = self._inner.assess(application, rule_results)

        try:
            self._redis.set(key, assessment.model_dump_json(), ex=self._ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("assessment cache write failed: %s", exc)
        return assessment
