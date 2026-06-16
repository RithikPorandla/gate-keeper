"""API + UI blueprints."""
from app.api import applications, health, metrics_api, queue, review, ui

ALL_BLUEPRINTS = [
    health.bp,
    applications.bp,
    queue.bp,
    review.bp,
    metrics_api.bp,
    ui.bp,
]

__all__ = ["ALL_BLUEPRINTS"]
