from __future__ import annotations

import redis as redis_lib

from app.config import get_settings
from app.llm.base import RiskAnalyst
from app.llm.cache import CachingRiskAnalyst
from app.llm.mock_provider import MockProvider


def _build_provider() -> RiskAnalyst:
    settings = get_settings()
    if settings.llm_provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    return MockProvider()


def get_risk_analyst(redis_client: redis_lib.Redis | None = None) -> RiskAnalyst:
    """Build the configured risk analyst, wrapped in a Redis cache when available."""
    settings = get_settings()
    provider = _build_provider()
    if redis_client is not None:
        return CachingRiskAnalyst(provider, redis_client, settings.llm_cache_ttl_seconds)
    return provider


__all__ = ["RiskAnalyst", "get_risk_analyst", "MockProvider"]
