# ADR-005: Full Migration to Microsoft Fabric Ecosystem

**Status:** Proposed — design-phase only, NOT signed off, NOT executed.
**Date:** 2026-06-30
**Owner:** Raja Ahmad Luqman (single-dev). Drafted in `fabric-migration/` per the
2026-06-30 design session — built outside the live AWS/Snowflake governance globs so this
ADR does not itself trip `tests/boundary_contract.py`.

## Context
The current pipeline (see parent `CLAUDE.md` Stack table) spans 4 platforms: AWS (S3 + Glue),
Snowflake (Gold/marts), Databricks (Serverless SQL, query-only), and Power BI. This is
intentional breadth for a portfolio project, but it carries real multi-vendor overhead:
4 billing relationships, 4 IAM/credential surfaces, cross-cloud egress between S3 → Snowflake →
Databricks, and 3 copies of the same data living in 3 different storage systems.

Power BI is already in the stack as the BI layer. Microsoft Fabric is Power BI's native backend
— OneLake, Fabric Spark, Fabric Warehouse, and Power BI all share one workspace and one storage
layer (OneLake), eliminating the cross-cloud copy problem entirely. This makes Fabric a
**consolidation**, not an unrelated stack swap.

## Decision
**Migrate the full pipeline to a fully Fabric-native ecosystem** — no AWS, no Snowflake, no
standalone Databricks. Every layer (ingest orchestration, Bronze/Silver/Gold storage, transform
compute, data quality, alerting, BI) is re-platformed onto a Fabric-native service. See
`ADR-006-fabric-native-service-mapping.md` for the per-layer mapping and the one named exception
(dbt Core).

**This is a re-platform, not a logic rewrite, for the transform layers that matter most:**
- PII mask order (DI-002, sentinel→NULL before SHA-256), XNA→NULL, dedup, MERGE-upsert logic in
  the 5 Glue Silver jobs ports to Fabric Spark notebooks largely unchanged — Spark API surface is
  the same engine family (Glue 4.0 = Spark 3.3, Fabric Runtime 1.2/1.3 = Spark 3.4/3.5).
- The Kimball star schema, grain decisions (`SK_ID_CURR`/`applicant_id`, `SK_ID_BUREAU`,
  `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)`), and SCD2 strategy are **unchanged** — this ADR does not
  touch ADR-001. A Fabric migration is a compute/storage re-platform, not a re-grain.

## Scope (in / out)
**In scope:** ingestion orchestration, Bronze/Silver/Gold storage, Silver transform compute, Gold
transform compute, data-quality gating, pipeline alerting, BI serving layer.
**Out of scope (unchanged by this ADR):**
- The Kimball grain/SCD2 design (ADR-001) — re-platformed, not re-designed.
- The PII mask order (ADR-002) — re-platformed, not re-designed.
- The Kaggle Competition API as sole ingestion source — Fabric has no Kaggle connector
  (verified: Fabric's Data Factory connector catalog does not list Kaggle), so the existing
  `download_dataset.py`-style script still runs, just inside a Fabric notebook instead of a
  local/Codespace shell. This is a hard external-data-source boundary, not a service choice —
  flagged once here, not re-litigated per file.

## Consequences
**(+)** One platform, one billing relationship, one IAM/identity surface (Entra ID) instead of 4.
**(+)** Zero cross-cloud egress — OneLake is the single storage layer every compute engine
(Spark notebook, Warehouse, SQL endpoint, Power BI) reads directly; no S3→Snowflake→Databricks
copy chain.
**(+)** Power BI Direct Lake removes the import/refresh cycle entirely — BI reads live Delta from
OneLake.
**(+)** Native Delta MERGE inside a Fabric Spark notebook removes the idempotency workaround this
repo's `docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md:96` was forced into (Snowflake's
`CREATE PIPE` body cannot be `MERGE`, only `COPY INTO` — the binding idempotency guarantee had to
be pushed downstream into a dbt `QUALIFY ROW_NUMBER()` dedup, `stg_application.sql:34`). In
Fabric, the Lakehouse write step itself can do `MERGE INTO ... ON SK_ID_CURR` directly — see
`ADR-007-validation-parity-protocol.md` for how this gets proven, not assumed.
**(-)** This is a full re-platform, not a tweak — every layer needs its own validation pass before
the AWS/Snowflake side can be torn down (see `staging/DUAL_RUN_PLAN.md`).
**(-)** dbt Core (current Gold transform framework) is not a Fabric-native service — named
exception, see ADR-006.
**(-)** Purview DQ is not a drop-in replacement for Great Expectations' inline PASS/FAIL gate
semantics — ADR-006 resolves this with a hybrid (inline notebook assertions for gating, Purview
for catalog/lineage), not a silent swap.
**(-)** Narrative cost for portfolio purposes: a single-platform Fabric stack demonstrates less
multi-cloud breadth than the current AWS+Snowflake+Databricks spread. Noted, not resolved here —
a presentation/positioning question, not an engineering one.

## Alternatives rejected
- **Partial migration (Fabric for Gold only, keep AWS Glue for Silver):** rejected per owner
  instruction (2026-06-30) — "fully fabric ecosystem," not a hybrid. A hybrid would also
  reintroduce the cross-cloud egress problem this ADR exists to remove.
- **Keep Slack for alerting, Fabric for everything else:** rejected at migration time — Slack
  is a third-party service outside the Fabric/M365 ecosystem; Teams (native M365, same tenant as
  Fabric) replaces it. See ADR-006. **⚠️ Reversed for the alerting channel by ADR-013 (2026-07-06):**
  Teams proved unusable in the real MSA-rooted Fabric trial tenant, so Slack was re-admitted for
  pipeline-failure alerting. The "no hybrid data plane" reasoning stands; only alerting changed.

## Sign-off (REQUIRED before any real Fabric provisioning — none granted yet)
Per parent `CLAUDE.md` governance: @data-architect holds veto on grain/model changes,
@scope-guardian holds veto on stack/scope creep. This ADR is a stack swap by definition, so
**both vetoes are in scope, not optional**:
- [ ] **@scope-guardian** — confirm this ADR's scope (Section "Scope") does not silently expand
  beyond what's listed; confirm the existing `tests/boundary_contract.py` continues to pass
  unmodified for as long as the AWS/Snowflake pipeline keeps running in parallel
  (`staging/DUAL_RUN_PLAN.md`).
- [ ] **@data-architect** — confirm the Kimball grain/SCD2 design genuinely survives the
  re-platform unchanged (re-verify against `ADR-006`'s Gold-layer mapping, not assumed from this
  ADR's claim alone).
- [ ] **@finops-agent** — cost comparison: Fabric capacity-unit pricing vs. current AWS
  free-tier + Snowflake credit spend (`benchmarks/COST_BASELINE.md` is the baseline to compare
  against — not done in this pass, flagged as a pre-sign-off requirement, not a nice-to-have).
- [ ] **Owner** — final go/no-go, since this is a single-dev portfolio project and the owner is
  also the implementer.

**This ADR stays Proposed until all four boxes are checked.** No Fabric resource should be
provisioned against this design while it remains Proposed.
