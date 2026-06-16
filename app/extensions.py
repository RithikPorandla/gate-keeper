"""Shared extension singletons.

Kept separate from the app factory so models, tasks, and tests can import them
without triggering circular imports.
"""
from __future__ import annotations

import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import get_settings

db = SQLAlchemy()
migrate = Migrate()

_settings = get_settings()

# Redis-backed rate limiter — shared across API replicas so limits are global,
# not per-process.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_settings.redis_url,
)

# A plain Redis client for the assessment cache and velocity counters. Decoded
# responses so callers get str, not bytes.
redis_client: redis.Redis = redis.Redis.from_url(_settings.redis_url, decode_responses=True)
