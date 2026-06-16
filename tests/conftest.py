"""Test fixtures.

Tests run fully offline:
  - LLM provider is the deterministic mock (no API key).
  - Redis is faked in-process with fakeredis.
  - The database is in-memory SQLite (models use portable column types).
"""
from __future__ import annotations

import os

# Configure the environment BEFORE importing the app or its extensions.
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DEMO_REVIEWER_API_KEY", "test-ops-key")

# Patch redis.Redis.from_url -> fakeredis before app.extensions constructs its client.
import fakeredis  # noqa: E402
import redis  # noqa: E402

_fake_server = fakeredis.FakeServer()


def _fake_from_url(url, **kwargs):  # noqa: ANN001
    return fakeredis.FakeStrictRedis(
        server=_fake_server, decode_responses=kwargs.get("decode_responses", False)
    )


redis.Redis.from_url = _fake_from_url  # type: ignore[assignment]

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.extensions import db, limiter, redis_client  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Reviewer  # noqa: E402


@pytest.fixture()
def app():
    get_settings.cache_clear()
    application = create_app()
    application.config.update(TESTING=True)
    limiter.enabled = False  # don't hit rate-limit storage in tests
    with application.app_context():
        db.create_all()
        redis_client.flushall()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def fake_redis():
    return redis_client


@pytest.fixture()
def demo_reviewer(app):
    reviewer = Reviewer(
        name="Test Reviewer",
        email="reviewer@test.example",
        api_key_hash=Reviewer.hash_key("test-ops-key"),
    )
    db.session.add(reviewer)
    db.session.commit()
    return reviewer
