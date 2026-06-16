"""Simple API-key auth for the protected (review / metrics) endpoints.

A reviewer presents `X-API-Key`; we look up its SHA-256 hash in the reviewers table.
Synthetic demo, but it keeps the write/ops surface from being wide open.
"""
from __future__ import annotations

import functools

from flask import g, jsonify, request
from sqlalchemy import select

from app.extensions import db
from app.models import Reviewer


def _resolve_reviewer() -> Reviewer | None:
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        return None
    key_hash = Reviewer.hash_key(raw_key)
    return db.session.scalar(select(Reviewer).where(Reviewer.api_key_hash == key_hash))


def require_api_key(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        reviewer = _resolve_reviewer()
        if reviewer is None:
            return jsonify({"error": "unauthorized", "detail": "valid X-API-Key required"}), 401
        g.reviewer = reviewer
        return fn(*args, **kwargs)

    return wrapper
