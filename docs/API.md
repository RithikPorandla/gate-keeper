# API reference

Base URL (local): `http://localhost:8000`

Protected endpoints require an `X-API-Key` header matching a seeded reviewer
(`DEMO_REVIEWER_API_KEY`, default `demo-ops-key-please-change`).

## POST /api/applications

Submit a business application. Returns **202** with a pending record; decisioning
happens asynchronously.

Headers (optional): `Idempotency-Key: <string>` — a repeat submission with the same
key returns the existing application instead of creating a duplicate.

```bash
curl -X POST http://localhost:8000/api/applications \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-001" \
  -d '{
    "business_name": "Northwind Coffee",
    "registration_number": "12-3456789",
    "country": "US",
    "industry_code": "7220",
    "requested_spend_limit": 5000,
    "applicant_name": "Dana Whitfield",
    "applicant_email": "dana@northwind.example",
    "mock_credit_score": 760
  }'
```

```json
{ "id": "f1c2...", "status": "pending" }
```

## GET /api/applications/{id}

Returns the application with its decision and per-rule results.

```json
{
  "application": { "...": "..." },
  "decision": { "outcome": "approved", "combined_risk_score": 8.5, "llm_rationale": "..." },
  "rule_results": [ { "rule_name": "watchlist", "passed": true, "severity": "low" } ]
}
```

## GET /api/queue

`needs_review` applications. Query params: `sort=risk|age`, `limit`, `offset`.

## POST /api/applications/{id}/review  *(auth)*

```bash
curl -X POST http://localhost:8000/api/applications/<id>/review \
  -H "X-API-Key: demo-ops-key-please-change" \
  -H "Content-Type: application/json" \
  -d '{ "action": "approve", "notes": "verified manually" }'
```

`action` is `approve` or `decline`. Records the reviewer and time-to-decision.

## GET /api/metrics/summary  *(auth)*

Approval rate, auto-decision rate, conversion, average review time, status counts,
and an outcome breakdown.

## Operational

- `GET /healthz` — liveness.
- `GET /readyz` — readiness (checks Postgres + Redis); 503 if not ready.
- `GET /metrics` — Prometheus exposition format.
