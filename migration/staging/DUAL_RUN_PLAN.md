# Dual-Run Plan — Parallel Operation Before Cutover

> Governs the period between "Fabric is provisioned" and "AWS/Snowflake is torn down."
> Nothing in the current AWS/Snowflake stack gets deprovisioned until this plan completes
> AND all conditions in `governance/SIGN_OFF.md` Gates 1–4 are signed.

## Why a dual-run period?
The parity test (`validation/PARITY_TEST_PLAN.md`) only proves Fabric output MATCHES the
pre-migration baseline on a single run. The dual-run period proves that:
1. Both stacks can be run **concurrently** without interfering (no shared mutable state,
   no double-charging from Snowpipe auto-fire triggered by Fabric writes to S3, etc.).
2. A **second real Fabric run** on fresh data produces consistent output before the old
   stack is permanently decommissioned (no last-minute surprises after teardown).
3. The old stack is genuinely **idle** during the dual-run period and not incurring new
   cost — confirming it is safe to remove.

## Dual-run period definition
- **Start:** All of Gate 1 AND Gate 2 conditions signed (Fabric Silver proven).
- **End:** All of Gate 3 AND Gate 4 conditions signed (Fabric Gold + alerting proven).
- **Duration:** minimum 1 full pipeline run on Fabric after Gate 2 sign-off; no fixed
  calendar duration (single-dev portfolio project — this is a quality gate, not a SLA).

## What runs during the dual-run period

| Action | AWS/Snowflake stack | Fabric stack |
|---|---|---|
| Source data (Kaggle download) | **Frozen** — no new download, no new S3 writes to dev/staging buckets | Fabric notebook runs the download → OneLake Bronze |
| Silver transform | **Frozen** — Glue jobs NOT re-triggered | Fabric Silver notebooks run, parity check captured |
| Gold/mart | **Read-only** — Snowflake STAGING queried for comparison only, no new COPY INTO | dbt-fabric run → Fabric Warehouse Gold |
| Alerting | **Frozen** — Airflow DAGs NOT running | Data Factory pipeline + Data Activator active |
| BI | **Read-only** — Snowflake-connected Power BI still live for comparison | Power BI Direct Lake on Fabric Gold |

**Why "frozen" for the old stack:** re-triggering AWS Glue during the dual-run period
would risk writing new Delta files to `home-credit-risk-staging/`, which the dev
Snowpipe (still armed, teardown deferred per `PROJECT_STATUS.md:1613`) could auto-fire
on and consume SQS credits. Keeping the old stack frozen eliminates that risk entirely
and makes the economics comparison clean.

## Critical pre-conditions (check BEFORE starting dual-run)
1. **Snowpipe auto-fire risk neutralised:** confirm the 4 dev Snowpipe objects are NOT
   watching any path the Fabric stack writes to. Fabric writes to OneLake (Azure), not
   S3 — so no cross-cloud Snowpipe trigger is possible by construction. The staging S3
   bucket (`home-credit-risk-staging`) must NOT receive any new writes from Fabric during
   the dual-run period (Fabric does not need S3 during dual-run). ✅ Safe by architecture.
2. **Snowflake STAGING tables are read-only:** no writes to `HOME_CREDIT_RISK.STAGING.*`
   during the dual-run period. The parity comparison reads these tables as a static
   baseline. ✅ Enforce via Snowflake role permission review before dual-run starts.
3. **`tests/boundary_contract.py` in the parent repo still passes:** confirm no parent-
   repo files were accidentally edited as part of the Fabric work. Run
   `python tests/boundary_contract.py` from the parent repo root.

## Dual-run completion checklist (must all be ticked to authorise Gate 5 teardown)

- [ ] Gate 2 signed (`governance/SIGN_OFF.md`) — Fabric Silver parity proven
- [ ] Gate 3 signed — Fabric Gold/mart parity proven
- [ ] Gate 4 signed — End-to-end + alerting + BI confirmed
- [ ] At least 1 additional full-pipeline Fabric run completed AFTER Gate 2 (second data
      point — shows the pipeline is not a one-time fluke)
- [ ] Idempotency test (`parity_check.py --idempotency`) passed on the second run
- [ ] Old stack confirmed idle (no new Glue job runs, no new Snowflake COPY INTO charges)
      during the dual-run period — logged in `COST_BASELINE.md` addendum
- [ ] Owner confirms readiness to proceed to teardown — single-dev project, one person
      is the final gate

Only after all boxes above are checked does Gate 5 open (`governance/SIGN_OFF.md`).

## What changes in `governance/SIGN_OFF.md` when this plan completes
Update Gate 5 status from OPEN → all rows from "☐ Pending" to either "✅ Done" or
"⚠️ Deferred (reason)". Add execution date and evidence (command output / screenshots)
to each Gate 5 teardown row. Log final status in `PROJECT_STATUS.md`.
