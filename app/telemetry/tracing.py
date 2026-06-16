"""OpenTelemetry tracing setup.

Optional and off by default (OTEL_ENABLED=false) so local dev and tests don't need
a collector. When enabled, traces are exported via OTLP to the configured endpoint
(Tempo in the docker-compose stack) and Flask/Celery/SQLAlchemy are auto-instrumented.
"""
from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False


def init_tracing(flask_app=None) -> None:
    """Initialise tracing once. Safe to call from both web and worker entrypoints."""
    global _initialized
    settings = get_settings()
    if not settings.otel_enabled or _initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
        )
        trace.set_tracer_provider(provider)

        if flask_app is not None:
            from opentelemetry.instrumentation.flask import FlaskInstrumentor

            FlaskInstrumentor().instrument_app(flask_app)

        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument()
        _initialized = True
        logger.info("OpenTelemetry tracing initialised (endpoint=%s)", settings.otel_exporter_otlp_endpoint)
    except Exception as exc:  # noqa: BLE001 — never let telemetry break the app
        logger.warning("Failed to initialise tracing: %s", exc)


def get_tracer(name: str = "gatekeeper"):
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except Exception:  # noqa: BLE001
        return _NoopTracer()


class _NoopSpan:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, *args, **kwargs):
        pass


class _NoopTracer:
    def start_as_current_span(self, *args, **kwargs):
        return _NoopSpan()
