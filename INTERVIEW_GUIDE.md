# Interview Guide — Home Credit Risk Pipeline (Fabric)

> Co-owned by @business-analyst (evidence content) and @documentation-sherpa (doc structure).
> Rule: no Fabric claim graduates from "(unverified)" without a `file:line` pointer to a real
> parity-check run (`migration/validation/parity_check.py`) or an actual Fabric Workspace
> screenshot/log. This mirrors the parent repo's own resume-correction precedent (README.md
> "Resume wording corrected" section) — don't repeat the "Lambda / Step Functions" mistake in
> the new stack's direction.

## Resume Claim ↔ Repo Evidence

| Claim | Status | Evidence |
|-------|--------|----------|
| "Re-platformed a 58M-row pipeline to Microsoft Fabric" | (unverified) | Governance framework exists (this repo); no Fabric workspace provisioned yet |
| "OneLake Delta MERGE removes the Snowpipe idempotency workaround" | (unverified) | Design documented `docs/ADR/ADR-004-onelake-merge-idempotency.md`; not yet proven against a real Fabric Spark notebook run |
| "Fabric Warehouse T-SQL stored-proc Gold models, dbt retired" | (unverified) | `warehouse/` tree exists (ADR-008); no real proc run against a Fabric Warehouse has executed |
| "Power BI Direct Lake dashboard" | (unverified) | Design only — `docs/ARCHITECTURE.md`; no Direct Lake semantic model built |
| "Kimball star schema (3 facts + 3 dims), SCD2 on dim_applicant" | Carried forward from parent repo, unchanged (ADR-005 scope) | `docs/DATA_MODEL.md`, `docs/ADR/ADR-001-kimball-star-schema.md` — this claim is proven in the parent repo, not re-derived here |
| "PII masking (SHA-256), sentinel-before-hash order" | Carried forward, unchanged | `docs/ADR/ADR-002-pii-mask-order.md` — logic ports verbatim to `notebooks/nb_silver_application.py` (not yet written) |
| "AWS Glue baseline: G.1X×2, peak 2.90 GB / 32 GB (9%)" | Confirmed (parent repo, real run) | `migration/benchmarks/INFRA_BASELINE.md` — this is the number Fabric must match or beat, not a Fabric-side claim itself |

## Fabric-specific Q&A (drill until answerable without notes)

1. **"Why Fabric instead of staying on AWS/Snowflake/Databricks?"**
   Platform consolidation — 4 billing/IAM surfaces → 1. Power BI was already in the stack;
   Fabric is its native backend, so OneLake removes the S3→Snowflake→Databricks copy chain
   entirely. See `migration/ADR/ADR-005-fabric-full-migration-decision.md`.

2. **"Was there ever anything that WASN'T Fabric-native in this migration?"**
   Yes, briefly — dbt Core was kept as a named exception in `migration/ADR/ADR-006-*` §4. The
   owner later ruled "Fabric-only" absolute, so `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`
   exercised ADR-006's own pre-authorised "Option B" fallback: dbt is retired, Gold is now
   Fabric Warehouse T-SQL stored procedures under `warehouse/`, zero third-party tooling.

3. **"How does idempotency actually improve under Fabric vs. the old Snowpipe design?"**
   Snowflake's `CREATE PIPE` body only accepts `COPY INTO`, not `MERGE` — that pushed the
   idempotency guarantee downstream into a dbt `QUALIFY ROW_NUMBER()` dedup. Fabric Spark
   notebooks can `MERGE INTO ... ON SK_ID_CURR` directly at write time — no pipe-body
   restriction, because there's no pipe. See `docs/ADR/ADR-004-onelake-merge-idempotency.md`.

4. **"What would you check first if the Fabric Silver notebook produced duplicate rows?"**
   Whether the `MERGE INTO` has both `WHEN MATCHED THEN UPDATE` and `WHEN NOT MATCHED THEN
   INSERT` branches — an insert-only MERGE silently reintroduces the exact duplicate-row bug
   the migration was supposed to fix (ADR-004 "Consequences", ADR-007 idempotency failure modes).
