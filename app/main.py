"""Flask application factory.

create_app() builds a fully wired web app. The Celery worker calls it with
register_extensions_only=True to get DB/config in a context without HTTP routes.
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from app.config import get_settings
from app.extensions import db, limiter, migrate

_BASE_DIR = Path(__file__).resolve().parent.parent
_TEMPLATES = _BASE_DIR / "templates"
_STATIC = _BASE_DIR / "static"


def create_app(register_extensions_only: bool = False) -> Flask:
    settings = get_settings()

    app = Flask(
        __name__,
        template_folder=str(_TEMPLATES),
        static_folder=str(_STATIC),
    )

    # SQLite (used in tests) doesn't support QueuePool sizing args; only apply the
    # connection-pool tuning for real server databases like Postgres.
    if settings.database_url.startswith("sqlite"):
        engine_options: dict = {}
    else:
        engine_options = {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_pre_ping": settings.db_pool_pre_ping,
        }

    app.config.update(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        JSON_SORT_KEYS=False,
    )

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure models are imported so metadata is populated. Use `from ... import`
    # so we don't rebind the local `app` (Flask instance) to the `app` package.
    from app import models as _models  # noqa: F401

    if register_extensions_only:
        return app

    limiter.init_app(app)

    # Tracing (no-op unless OTEL_ENABLED).
    from app.telemetry import init_tracing

    init_tracing(app)

    # Blueprints
    from app.api import ALL_BLUEPRINTS

    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)

    return app


# Module-level app for `flask` CLI / gunicorn: `gunicorn "app.main:app"`.
app = create_app()
