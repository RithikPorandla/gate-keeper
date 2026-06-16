"""Prometheus metrics.

Exposed at /metrics for scraping. Counters/histograms/gauge here back the Grafana
dashboard checked into infra/grafana/.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Applications submitted to the intake endpoint.
applications_submitted_total = Counter(
    "gatekeeper_applications_submitted_total",
    "Total applications submitted",
)

# Decisions made, labelled by outcome and whether a human was involved.
decisions_total = Counter(
    "gatekeeper_decisions_total",
    "Total decisions by outcome and stage",
    ["outcome", "stage"],  # stage = automated | human
)

# End-to-end decisioning latency for the async pipeline (seconds).
decision_latency_seconds = Histogram(
    "gatekeeper_decision_latency_seconds",
    "Time from task start to decision persisted",
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

# Current depth of the human review queue (needs_review applications).
review_queue_depth = Gauge(
    "gatekeeper_review_queue_depth",
    "Number of applications currently awaiting human review",
)
