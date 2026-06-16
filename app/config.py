"""Environment-driven application settings.

All configuration is read from the environment (12-factor) so the same image runs
unchanged across local docker-compose, CI, and any orchestrator. Nothing here is
secret by default — secrets come from the environment / .env.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Core
    flask_env: str = "development"
    secret_key: str = "dev-secret-change-me"

    # Postgres
    database_url: str = "postgresql+psycopg://gatekeeper:gatekeeper@localhost:5432/gatekeeper"
    # Connection pooling — sized for many concurrent API/worker processes.
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_pre_ping: bool = True

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # LLM risk analyst
    llm_provider: str = "mock"  # "mock" | "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    llm_timeout_seconds: int = 30
    llm_cache_ttl_seconds: int = 86400

    # Auth
    demo_reviewer_api_key: str = "demo-ops-key-please-change"

    # Rate limiting (Redis-backed) for the public intake endpoint.
    intake_rate_limit: str = "60 per minute"

    # Observability
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "gatekeeper"


@lru_cache
def get_settings() -> Settings:
    return Settings()
