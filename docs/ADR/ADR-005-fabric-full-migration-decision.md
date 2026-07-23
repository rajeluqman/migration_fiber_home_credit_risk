# ADR-005: Full Migration to Microsoft Fabric Ecosystem

**Status:** Accepted — Gate 0 signed 2026-07-01. Design-phase; real Fabric provisioning
awaits Gate 1 (see `migration/governance/SIGN_OFF.md`). Provisioning sequencing (trial-capacity
first, paid $200 credit reserved for scale validation) + local-first logic dev are governed by
**ADR-010** (Proposed, Gate 1.5).
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
  Fabric) replaces it. See ADR-006. **⚠️ This specific rejection was later reversed by ADR-013
  (2026-07-06):** Teams proved unusable in the real MSA-rooted Fabric trial tenant (BAP OAuth block
  + paid-licence requirement), so the Owner re-admitted Slack for pipeline-failure alerting. The
  rest of this ADR's "no hybrid" reasoning stands — only the alerting channel changed.

## Sign-off (REQUIRED before any real Fabric provisioning)
Per parent `CLAUDE.md` governance: @data-architect holds veto on grain/model changes,
@scope-guardian holds veto on stack/scope creep. This ADR is a stack swap by definition, so
**both vetoes are in scope, not optional**:
- [x] **@scope-guardian** — confirmed 2026-07-01: `tests/boundary_contract.py` passes clean
  (no AWS SDK, no Snowflake connector, no Airflow, no Slack SDK, dbt adapter=fabric), no
  reintroduced banned platforms, Spark confined to `notebooks/`, no scope creep beyond what's
  listed in Section "Scope". APPROVE. Full review: Gate 0 sign-off review, 2026-07-01.
- [x] **@data-architect** — confirmed 2026-07-01: all 4 implemented mart models preserve
  locked grains 1:1 against `docs/DATA_MODEL.md`; `snap_applicant.sql` correctly uses
  `strategy: check` SCD2 on `applicant_id`; no mixed-grain dimensions. APPROVE (conditional —
  `dim_loan_type`/`dim_credit_status` not yet built out, tracked as a follow-up, not a grain
  violation).
- [x] **@finops-agent** — reviewed 2026-07-01, revised after owner disclosed a **$200 USD
  Azure/Fabric trial credit** available for this project. Baseline real spend to date is
  ≈$0.186 total (AWS Glue + Snowflake, portfolio/free-tier scale, `benchmarks/COST_BASELINE.md`),
  while a Fabric F2 capacity runs a flat ≈$262/month regardless of usage. Unmitigated, that's
  roughly a 1,400x jump for month one alone — a **cost increase, not a cost saving**, unlike
  most of this ADR's other consequences. With the $200 trial credit applied, month one is
  reduced to ≈$62 out-of-pocket (≈24% of full price), and pausing/deallocating the capacity
  between work sessions (rather than leaving it running 24/7) can stretch that credit across
  more than one month of intermittent portfolio-project usage. Accepted on that basis, with the
  expectation that: (1) the F-SKU capacity is explicitly paused/deallocated when not actively in
  use, (2) `COST_LOG.md`/`benchmarks/COST_BASELINE.md` is updated with the real credit balance
  and real Fabric CU draw once provisioning happens (Gate 1+), and (3) the owner is notified
  before the $200 credit is exhausted so continued spend is a conscious choice, not a surprise.
- [x] **Owner** — final go/no-go, 2026-07-01: **GO**. Single-dev portfolio project; owner
  (Raja Ahmad Luqman) is also the implementer and accepts the finops cost trade-off above in
  exchange for the Fabric-native breadth/consolidation narrative this migration demonstrates.

**Gate 0 signed 2026-07-01 — ADR-005 status: Accepted.** Framework/governance code may now
merge to main. Real Fabric provisioning still requires Gate 1 (new repo + contract setup, see
`migration/governance/SIGN_OFF.md`) before any resource is created.
