# ADR-007: Validation, Parity, and Idempotency Protocol

**Status:** Proposed — pending ADR-005 sign-off before execution.
**Date:** 2026-06-30
**Owner:** Raja Ahmad Luqman

## Context
Before the AWS/Snowflake stack can be torn down, Fabric output must be proven equal to
the pre-migration baseline captured in `benchmarks/`. The protocol below defines what
"proven equal" means, what the acceptance criteria are, and how idempotency is
validated. Every number it references has a citation in `benchmarks/*.md` back to the
parent repo's evidence trail.

This ADR answers three questions:
1. **Parity** — how do we know Fabric produces the same rows as the AWS/Snowflake stack?
2. **Idempotency** — how do we know re-running the Fabric pipeline produces the same
   output (no duplicates, no silent row drops)?
3. **Completeness gate** — what is the exhaustive checklist that authorises the AWS
   teardown?

## Parity Protocol

### Tier 1 — Row-count match (mandatory, all tables)
For every Silver and Gold table, post-Fabric run:
```
| table | Fabric COUNT(*) | Baseline COUNT(*) | delta | pass? |
|-------|----------------|-------------------|-------|-------|
| silver_application | ? | 307,511 | ? | |
...
```
Baseline values are in `benchmarks/SILVER_BASELINE.md` (Silver, full-scale) and
`benchmarks/SNOWFLAKE_STAGING_BASELINE.md` (Gold/STAGING). **Delta must be 0.**
Any non-zero delta is a hard block — not a warning.

### Tier 2 — PK uniqueness (mandatory, all keyed tables)
For each table with a declared primary key, `COUNT(*) == COUNT(DISTINCT pk_col)` after
the Fabric run. Baseline PK-distinct values are in `benchmarks/SNOWFLAKE_STAGING_BASELINE.md`.
Duplicates are a hard block regardless of row-count match.

### Tier 3 — Null-count match on PK columns (mandatory)
`COUNT_IF(pk_col IS NULL) == 0` for every keyed Silver table. Baseline is 0 for all
4 tables loaded to Snowflake STAGING (`benchmarks/SNOWFLAKE_STAGING_BASELINE.md`).

### Tier 4 — PII mask verification (mandatory, silver_application only)
The following columns must exist in the Fabric Silver output and the raw columns must
be absent, matching the current GX `silver_suite` expectation
(`gx/expectations/silver_suite.json`):
- `DAYS_BIRTH_MASKED` present, `DAYS_BIRTH` absent.
- `DAYS_EMPLOYED_MASKED` present, `DAYS_EMPLOYED` absent.
This mirrors the current GX silver_suite PII-mask check that already gates the
AWS/Glue run (`PROJECT_STATUS.md` line ~127: "GX silver_suite (FAIL gate): ALL PASS").

### Tier 5 — Dedup-rate preservation (Silver tables with known dedup)
Two Silver tables have documented post-dedup row counts that differ from their Bronze
source (see `benchmarks/SILVER_BASELINE.md`):
- `silver_bureau_balance`: 610,965 from 27,299,925 Bronze rows (post `MONTHS_BALANCE=0`
  filter + dedup). The Fabric run must produce the same 610,965 — not the Bronze count.
- `silver_installments`: 12,861,994 from 13,605,401 Bronze rows (dedup on
  `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)`, 94.5% retention). The Fabric run must produce
  the same 12,861,994.

### Tier 6 — Checksum spot-check on sample (recommended, not mandatory for initial cutover)
For `silver_application` (smallest, most structurally complex), compute
`MD5(CONCAT(SK_ID_CURR, DAYS_BIRTH_MASKED, NAME_INCOME_TYPE))` per row and compare the
sorted-row hash set between the current Snowflake STAGING table and the Fabric Lakehouse.
A 100% row-hash match on this table gives high confidence the transform logic ported
correctly. Not mandatory for initial cutover — required before production release.

### Runnable implementation
`validation/parity_check.py` — stdlib-only skeleton that takes two JSON row-count
manifests (one from the current stack, one from Fabric) and asserts all Tier 1-3
conditions. Run it as:
```
python parity_check.py benchmarks/silver_manifest.json fabric_run/silver_manifest.json
```

## Idempotency Protocol

### Why this is different from the current stack
The current stack's idempotency is enforced **downstream** of the ingest step because
Snowflake `CREATE PIPE` body accepts only `COPY INTO`, not `MERGE`
(`docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md:92`). The binding guarantee therefore
lives in `dbt_home_credit/models/staging/stg_application.sql:34`
(`QUALIFY ROW_NUMBER() OVER (PARTITION BY SK_ID_CURR ORDER BY ingestion_date DESC) = 1`)
placed between the raw STAGING table and `dbt snapshot`.

In Fabric, the Silver Spark notebook can execute `MERGE INTO` directly against the
OneLake Delta table at the end of the job — upstream idempotency, not downstream
workaround. The Snowpipe constraint is gone. This means the ADR-004 downstream dedup
is no longer the binding guarantee — the MERGE itself is.

### Idempotency test (mandatory before cutover authorisation)
**Run the Silver pipeline twice in a row on the same source data, then assert:**
1. `COUNT(*)` after run 2 == `COUNT(*)` after run 1 (no row doubling).
2. `COUNT(DISTINCT pk)` after run 2 == `COUNT(DISTINCT pk)` after run 1 (no duplicate PKs).
3. Max `ingestion_ts` after run 2 == max `ingestion_ts` after run 1 (no silent re-stamp).

This is a re-run test, not a data-variation test. The correct result is identical output
both runs. `validation/parity_check.py` includes an idempotency sub-command:
```
python parity_check.py --idempotency run1_manifest.json run2_manifest.json
```

### Idempotency failure modes to guard against
- **MERGE INTO without a matched `WHEN MATCHED THEN UPDATE`:** if the MERGE only inserts
  (no update clause), a second run inserts duplicate rows instead of upserting. Each
  Silver notebook must include both `WHEN MATCHED THEN UPDATE` and `WHEN NOT MATCHED
  THEN INSERT` branches — verified by code review of the ported notebooks before the
  idempotency test is run.
- **Delta table path reuse without schema evolution:** if a notebook writes to a path
  that already has a Delta log, and the schema changed, the write fails (schema
  enforcement). Test with `mergeSchema = false` explicitly — surface failures loudly,
  don't silently override.

## Completeness gate (authorises AWS/Snowflake teardown)

All of the following must be checked and signed off before ANY resource in the current
stack is deprovisioned:

| # | Condition | Evidence required | Owner |
|---|---|---|---|
| G1 | All 7 Silver tables pass Tier 1 row-count parity | Parity check output, run date | @senior-data-engineer |
| G2 | All Silver keyed tables pass Tier 2 PK uniqueness | Parity check output | @senior-data-engineer |
| G3 | All Silver keyed tables pass Tier 3 null-PK check | Parity check output | @senior-data-engineer |
| G4 | silver_application passes Tier 4 PII mask check | Notebook assertion log | @data-quality-steward |
| G5 | silver_bureau_balance and silver_installments match Tier 5 dedup counts | Parity check output | @senior-data-engineer |
| G6 | Gold mart tables exist in Fabric Warehouse with same grain | dbt run output, row counts | @data-architect |
| G7 | SCD2 snapshot produces exactly 1 is_current=TRUE row per applicant | `assert_scd2_one_current_per_applicant.sql` equivalent test passing | @data-architect |
| G8 | Idempotency test passes (re-run produces identical output) | parity_check.py --idempotency output | @senior-data-engineer |
| G9 | Slack alert fires on a simulated pipeline failure (ADR-013 — was Teams; Teams unusable in this tenant) | Screenshot/log of Slack message received | @data-platform-engineer |
| G10 | Power BI Direct Lake report loads without errors | Report screenshot, semantic model refresh log | Owner |
| G11 | @finops-agent confirms Fabric CU cost estimate acceptable vs. `COST_BASELINE.md` | Written cost comparison | @finops-agent |
| G12 | `governance/boundary_contract_fabric.py` exits 0 in the new repo | CI output | @scope-guardian |

**G1-G8 are hard blocks.** G9-G12 are required but can be completed in parallel with G1-G8.
No teardown of `snowflake_silver_loader` IAM role, Snowflake schemas, S3 buckets, or Glue
jobs until ALL 12 conditions are checked and signed in `governance/SIGN_OFF.md`.

## Why teardown matters (don't skip the completeness gate)
The parent repo's `docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md` already has an
example of a teardown that got rescoped mid-execution because a shared IAM role dependency
was missed (`snowflake_silver_loader` widened to cover both dev Snowpipe AND the staging
COPY INTO bridge — tearing down the dev Snowpipe per the original plan would have silently
broken the staging bridge too, `ADR-004:148-163`). The 12-condition gate above exists so
that "cutover" is a deliberate, evidence-backed event — not the point where problems
first surface.
