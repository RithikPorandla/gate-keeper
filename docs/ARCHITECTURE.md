# Architecture

## Overview

GateKeeper is a two-stage decisioning system fronted by a stateless HTTP API and
driven by an asynchronous worker pool.

```
client ──POST /api/applications──▶ Flask API (stateless, N replicas)
                                     │ validate (Pydantic) + persist status=pending
                                     │ enqueue Celery task (idempotency key honoured)
                                     └─▶ 202 {id, status:"pending"}

Celery worker (M replicas) ─▶ rule engine ─▶ RiskAnalyst.assess() ─▶ decision policy
                                   │             (Claude, Redis-cached)        │
                                   └─────────── persist decision + rule_results + audit
                                               emit OTel spans + Prometheus metrics

Redis    = Celery broker + result backend + assessment cache + velocity/rate-limit counters
Postgres = applications, decisions, rule_results, reviews, audit_log, reviewers
Tempo / Prometheus / Grafana = traces + metrics dashboards
Jinja UI = /queue (ops review) + /dashboard (metrics)
```

## Component responsibilities

| Layer | Module | Responsibility |
|------|--------|----------------|
| API / UI | `app/api/` | HTTP intake, queue, review, metrics, health, Jinja UI |
| Schemas | `app/schemas/` | Pydantic request/response + strict LLM-output validation |
| Rules | `app/rules/` | Deterministic, config-driven checks (pure functions) |
| LLM | `app/llm/` | `RiskAnalyst` interface + mock/Anthropic providers + Redis cache |
| Policy | `app/decisioning/` | Merge rules + LLM into an outcome (config-driven thresholds) |
| Services | `app/services/` | Shared pipeline + review business logic |
| Workers | `app/workers/` | Celery task wrapping the pipeline |
| Repository | `app/repository/` | Data access (keeps SQL out of routes/tasks) |
| Telemetry | `app/telemetry/` | Prometheus metrics + OpenTelemetry tracing |

## Why it scales

- **Stateless API and workers** — both scale horizontally. Workers:
  `docker compose up --scale worker=3`.
- **Connection pooling** — SQLAlchemy `QueuePool` (size/overflow configurable);
  drop in PgBouncer in front of Postgres for very high replica counts.
- **Idempotency** — intake honours an `Idempotency-Key`; the pipeline is idempotent
  on application status; Celery uses `acks_late` + a bounded retry. At-least-once
  delivery is therefore safe.
- **Redis offload** — assessment cache (cost control), velocity counters, and a
  shared rate-limiter keep hot paths off Postgres.
- **Append-only, partition-ready audit log** — `audit_log.created_at` is indexed so
  the table can be `RANGE`-partitioned by month once it grows.
- **Observable saturation** — a decision-latency histogram (p50/p95) and a
  queue-depth gauge make back-pressure visible before it becomes an outage.

## Path to production (not built here, documented)

- **Kubernetes**: one Deployment for the API, one for the worker, an HPA on each
  (API on RPS/CPU, worker on Celery queue depth via a custom metric).
- **Read replicas**: route the dashboard's read-only metrics queries to a replica.
- **Queue sharding**: route critical-priority applications to a dedicated Celery
  queue so a backlog of low-priority work can't starve them.
- **PgBouncer**: transaction pooling between the app and Postgres.
