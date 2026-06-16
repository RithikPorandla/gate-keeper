from __future__ import annotations

from flask import Blueprint, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.extensions import db, redis_client

bp = Blueprint("health", __name__)


@bp.get("/healthz")
def healthz():
    """Liveness — the process is up."""
    return jsonify({"status": "ok"})


@bp.get("/readyz")
def readyz():
    """Readiness — dependencies (DB + Redis) are reachable."""
    checks = {"database": False, "redis": False}
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        redis_client.ping()
        checks["redis"] = True
    except Exception:  # noqa: BLE001
        pass

    ready = all(checks.values())
    return jsonify({"status": "ready" if ready else "not_ready", "checks": checks}), (
        200 if ready else 503
    )


@bp.get("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
