# Snowflake STAGING Baseline — Pre-Migration Gold/Mart Load

> Numbers from the parent repo's `gold/load_silver_to_staging.py` COPY INTO run.
> Source: `PROJECT_STATUS.md` ~867-877: "Load run-evidence (2026-06-30, this session) —
> exact row-count match + PK uniqueness on all 4 in-scope tables, ~20s total wall time."
> All figures verified via live `SELECT COUNT(*)`/`COUNT(DISTINCT ...)`/`COUNT_IF(... IS NULL)`
> queries against `HOME_CREDIT_RISK.STAGING.*`, not assumed from COPY INTO return values alone.

**Snowflake schema:** `HOME_CREDIT_RISK.STAGING`
**Load method:** manual `COPY INTO` (no Snowpipe — deliberate, see parent `ADR-004`)
**Total rows loaded:** 14,496,898 across 4 tables

## Tables loaded to Snowflake STAGING

| Table | Rows loaded | PK | PK distinct | Null PKs | Status |
|---|---|---|---|---|---|
| SILVER_APPLICATION | **307,511** | `SK_ID_CURR` | **307,511** | **0** | ✅ Loaded |
| SILVER_BUREAU | **1,716,428** | `SK_ID_BUREAU` | **1,716,428** | **0** | ✅ Loaded |
| SILVER_BUREAU_BALANCE | **610,965** | `SK_ID_BUREAU` | **610,965** | **0** | ✅ Loaded |
| SILVER_INSTALLMENTS | **12,861,994** | (`SK_ID_PREV`, `NUM_INSTALMENT_NUMBER`) | **12,861,994** | n/a | ✅ Loaded |

## ⚠️ Gap — 3 Silver tables NOT yet loaded to Snowflake STAGING

`PROJECT_STATUS.md` ~855: the `gold/load_silver_to_staging.py` script was scoped to the
4 tables above ("4 in-scope tables"). The following 3 Silver tables were produced by Glue
but never COPY INTO'd into `HOME_CREDIT_RISK.STAGING`:

| Table | Silver row count (from SILVER_BASELINE.md) | Snowflake STAGING row count | Gap |
|---|---|---|---|
| SILVER_PREVIOUS_APPLICATION | 1,670,214 | **0 — never loaded** | Benchmark gap |
| SILVER_POS_CASH | 10,001,358 | **0 — never loaded** | Benchmark gap |
| SILVER_CREDIT_CARD | 3,840,312 | **0 — never loaded** | Benchmark gap |

**Implication for migration parity:** there is no existing Snowflake-side baseline to
compare Fabric output against for these 3 tables. The Fabric migration validation must
treat the Silver row counts from `SILVER_BASELINE.md` as the parity target (not a
Snowflake comparison), and the Gold/mart models for these 3 tables need a separate
validation against dbt test output once ported.

## Idempotency baseline
The COPY INTO run completed once. The Snowflake STAGING tables contain exactly one copy
of each row — no re-run was performed against these tables. This is relevant because the
current idempotency guarantee (ADR-004, downstream `QUALIFY ROW_NUMBER()` in
`stg_application.sql:34`) was built for the Snowpipe-auto-ingest case, not the
manual-COPY-INTO case. For the Fabric migration, the idempotency guarantee moves upstream
into the Silver MERGE (see ADR-007) — the Snowflake STAGING tables serve only as a
row-count reference, not as an idempotency-proof surface.

## Gold mart dbt run status (as of 2026-06-30)
Source: `PROJECT_STATUS.md` (gate closure sections) — the Gold-layer dbt run against
`HOME_CREDIT_RISK.STAGING` was in progress / partially proven during Gate 2. Full Gold
mart row counts (dim_applicant, fact_application, fact_bureau, etc.) are not separately
captured in a single benchmark table in the parent repo at time of this design pass.

**Implication:** Gate 3 of `governance/SIGN_OFF.md` (G6 — "Gold mart tables in Fabric
Warehouse, same grain as Snowflake equivalents") requires running `dbt run` against the
current Snowflake target and capturing output row counts BEFORE migration, as an
additional benchmark not yet present in this folder. Flag for completion before Gate 3
opens.
