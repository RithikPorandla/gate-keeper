# Decision policy

The policy (`app/decisioning/policy.py`) merges the deterministic rule engine with
the LLM risk analyst into one of three outcomes: `approved`, `declined`, or
`needs_review`. Thresholds live in `app/decisioning/policy.yaml` so they can be
tuned without a code change.

## The rules

1. **Critical rule failure → hard block (`declined`).** If any rule fails with
   `severity: critical` (e.g. a sanctions/watchlist hit), the application is
   declined immediately and the LLM is ignored. The LLM never has the authority to
   override a hard block — this is the core safety property.

2. **Otherwise, compute a combined risk score.** A weighted blend of:
   - the **rule-derived score** (capped sum of failed-rule severity weights), and
   - the **LLM `risk_score`** (0–100).

   Weights are configurable (default 50/50).

3. **Human-in-the-loop on disagreement.** If the rule-derived score and the LLM
   score disagree by more than `disagreement_delta` (default 40), the application
   goes to `needs_review` regardless of the combined score. This catches the cases
   where the deterministic and probabilistic views of risk diverge.

4. **Threshold routing** on the combined score:
   - `< auto_approve_below` (default 25) → `approved`
   - `> auto_decline_above` (default 70) → `declined`
   - in between → `needs_review`

## Severity weights

| Severity | Weight |
|----------|-------:|
| low | 5 |
| medium | 20 |
| high | 45 |
| critical | 100 (and triggers the hard block) |

## Tuning

Lowering `auto_approve_below` sends more applications to review (higher precision,
lower throughput); raising it auto-approves more (higher throughput, more risk).
The dashboard's approval-rate and auto-decision-rate make the effect of a change
visible immediately.

## Explainability

Every decision persists the LLM's raw structured output — `recommended_action`,
`risk_score`, `top_concerns`, `rationale`, and the `model_name`/`model_version` —
in the `decisions` table, plus a per-rule row in `rule_results`. Combined with the
append-only `audit_log`, every decision is fully reconstructable after the fact.
