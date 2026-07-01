# ADR-004: OneLake Delta MERGE — Silver Idempotency (replaces Snowpipe Silver→Gold Bridge)

Status: Proposed — pending real Fabric provisioning (`migration/governance/SIGN_OFF.md` Gate 0)
Date  : 2026-06-30
Owner : Senior Data Engineer (build) · Scope Guardian (boundary) · Data Architect (data path)

## Context
The parent repo's ADR-004 (`ADR-004-snowpipe-silver-gold-bridge.md`, home-credit-pipeline)
documented a real, hard-won constraint: Snowflake's `CREATE PIPE ... AS <stmt>` accepts only a
`COPY INTO` statement as its body — `MERGE` is not a legal pipe body. That forced the binding
idempotency guarantee downstream, into a dbt `QUALIFY ROW_NUMBER() OVER (PARTITION BY
SK_ID_CURR ORDER BY ingestion_date DESC) = 1` dedup in `stg_application.sql`, sitting between
the raw Snowpipe-loaded table and `dbt snapshot`. A re-fired Snowpipe load (Delta MERGE
rewriting Silver files under new names, defeating Snowflake's file-level load-history dedup)
could land duplicate physical rows for the same `SK_ID_CURR` — caught only after the fact by
`assert_scd2_one_current_per_applicant.sql`, invisible to any static contract.

In the Fabric stack, this constraint does not exist. Fabric Spark notebooks write directly to
OneLake Delta tables, and Delta Lake's `MERGE INTO` is a first-class, unrestricted SQL/PySpark
operation — there is no pipe-body restriction analogous to Snowflake's, because there is no
pipe: the Silver notebook itself performs the write.

## Decision
The Fabric Silver notebook executes `MERGE INTO silver_application ON SK_ID_CURR` directly, at
the end of the notebook run, against the OneLake Delta table:

```python
DeltaTable.forPath(spark, silver_path).alias("t").merge(
    transformed_df.alias("s"), "t.SK_ID_CURR = s.SK_ID_CURR"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

This makes idempotency an **upstream, write-time guarantee** — not a downstream dbt dedup
backstop. Re-running the Silver notebook on the same source data updates existing rows in
place and inserts only genuinely new rows; it cannot produce duplicate `SK_ID_CURR` rows.

## Why this removes the parent repo's dbt QUALIFY backstop
The parent repo's `QUALIFY ROW_NUMBER() = 1` in `stg_application.sql` existed **only** because
Snowpipe's `COPY INTO`-only body could not guarantee upsert semantics — it was a compensating
control for a platform limitation. Fabric Spark's native `MERGE INTO` removes the platform
limitation at its source, so the compensating control is no longer load-bearing. The
`dbt_fabric/models/staging/stg_application.sql` model in this repo does not need an equivalent
`QUALIFY`/`ROW_NUMBER()` dedup for idempotency — see ADR-007 (`migration/ADR/
ADR-007-validation-parity-protocol.md`) for how this claim gets proven, not assumed, before any
cutover decision.

## Consequences
(+) Idempotency guarantee moves from "downstream compensating control, easy to forget on a new
    staging model" to "upstream, structural, one line in the notebook."
(+) No pipe-body restriction to work around — Fabric Spark notebooks are not constrained the
    way a Snowflake `CREATE PIPE` body is.
(+) Simpler dbt staging models — no `QUALIFY` dedup boilerplate needed purely for idempotency
    (a `QUALIFY`-equivalent may still be needed for genuine business-logic dedup, but that is a
    separate concern from idempotency).
(-) The `MERGE INTO` must include **both** `WHEN MATCHED THEN UPDATE` and `WHEN NOT MATCHED
    THEN INSERT` branches — an insert-only MERGE (missing the matched-update branch) silently
    reintroduces the exact duplicate-row failure mode this ADR exists to remove. Code review of
    every ported notebook must verify both branches are present (see ADR-007 idempotency
    failure modes).
(-) This has not been proven against real Fabric infrastructure yet — Status stays Proposed
    until the idempotency re-run test in `migration/validation/parity_check.py
    --idempotency` passes against an actual Fabric Spark notebook run (ADR-007, Gate G8 in
    `migration/governance/SIGN_OFF.md`).

## Alternatives Rejected
- Keep the dbt `QUALIFY ROW_NUMBER()` dedup as a defense-in-depth backstop even though it's no
  longer strictly required: rejected as unnecessary complexity carried forward from a
  constraint that no longer applies — if a genuine business-logic dedup need arises later, it
  should be added deliberately with its own rationale, not inherited by default from the
  Snowpipe-era design.
- Insert-only append + separate downstream dedup job: rejected — reintroduces exactly the
  downstream-compensating-control pattern this ADR is designed to eliminate.
