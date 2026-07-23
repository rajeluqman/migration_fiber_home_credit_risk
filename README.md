# home-credit-risk-pipeline (Fabric Migration)

End-to-end credit risk profiling pipeline — Home Credit Default Risk dataset (307,511 loan applications across 7 source tables), **re-platformed to Microsoft Fabric**.

Built as a banking data engineering portfolio project demonstrating **Kimball Star Schema** modelling across a full medallion architecture: Bronze → Silver → Gold → BI, with PII masking (SHA-256), SCD Type 2 historical tracking, and automated data quality gating — now on a **fully Fabric-native stack** (OneLake, Fabric Spark Notebook, Fabric Warehouse, Data Factory, Power BI Direct Lake).

---

## Why This Pipeline Exists

Same business problem as the parent repo; different compute surface. The Fabric migration is a
**platform consolidation**: 4 billing relationships (AWS + Snowflake + Databricks + Power BI) →
1 (Microsoft Fabric / Entra ID). The logic is the same — the plumbing is cleaner.

- **One storage layer**: OneLake (Delta, native) — no S3→Snowflake copy chain
- **Zero cross-cloud egress**: Spark, Warehouse SQL, Power BI all read the same OneLake Delta files
- **Direct Lake BI**: Power BI reads live Delta, no import/refresh cycle

---

## Status

> ✅ **Provisioned and run end-to-end on real Fabric compute.** Gates 0 → 3 are signed and closed
> (`migration/governance/SIGN_OFF.md`); Gate 4 is open with two Owner-browser items remaining.

What **is** proven today (evidence in `MIGRATION_JOURNEY.md` J-021…J-025, `PROJECT_STATUS.md`):
- **Full end-to-end run succeeded** (~37 min) across the 3 chained Data Factory pipelines —
  `bronze_ingestion` → `silver_transforms` → `gold_warehouse` — against the real Fabric workspace.
- **Idempotent rebuild, no row-count drift**: Gold row counts verified by live query and matching
  the prior baseline exactly (307,511 dim / 307,511 / 1,716,428 / 12,861,994 fact rows).
- **Gate 3 CLOSED against real Fabric Warehouse compute** — SCD Type 2 one-current-record-per-entity
  invariant confirmed at full scale (307,511 rows, 0 violations), all fact grains matched to Silver
  source counts. @data-architect review: `migration/governance/GATE3_ARCHITECT_REVIEW_J021.md`.
- **Failure alerting fire-tested** (G9): a Data Factory `Failed` branch POSTs to Slack via a
  `WebForPipeline` connection (webhook held in the connection store, never in git); wired into
  production `silver_transforms`. ADR-013 records the Teams → Slack change and the reason.
- **CI green** (G12) and 4 static contracts pass: `tests/boundary_contract.py`,
  `tests/identity_contract.py`, `tests/doc_reference_contract.py`, `migration/governance/
  boundary_contract_fabric.py`.
- Pre-migration benchmarks (`migration/benchmarks/`) are real numbers from the parent repo's proven
  AWS Glue runs — the bar Fabric output had to clear (ADR-007).

Still open (honestly outstanding, Gate 4):
- **G10** — Power BI Direct Lake report over the Gold tables not yet built. Direct Lake is the
  designed serving mode and the SQL Analytics Endpoint is live, but no report/screenshot exists yet.
- **G11** — CU cost capture blocked on a Fabric Admin API permission (`admin/capacities` returns
  `403 InsufficientScopes`); pending the Capacity Metrics app instead.

---

## Stack

| Layer | Tool |
|-------|------|
| Ingest | Fabric Notebook (Kaggle API download) → Data Factory pipeline |
| Bronze/Silver/Gold storage | OneLake Lakehouse (Delta, native ACID) |
| Silver transform | Fabric Spark Notebook (PySpark, Runtime 1.3 = Spark 3.5) |
| Gold transform | Fabric Warehouse T-SQL stored procedures (`warehouse/`) — dbt retired, ADR-008 |
| DQ gate | Inline notebook assertions (PySpark `assert`, WARN/FAIL semantics) |
| DQ catalog | Purview DQ (profiling + lineage, not a gate) |
| Orchestration | Data Factory pipeline (3 chained pipelines) |
| Alerting | Data Factory failure-branch → Slack Incoming Webhook (ADR-013 — was Teams) + Data Activator reflex |
| Query layer | SQL Analytics Endpoint (auto on every Lakehouse) |
| BI | Power BI Direct Lake |

**Stack boundary (hard):** no AWS/Snowflake/Airflow. Enforced by `tests/boundary_contract.py`.
(Slack was banned too until 2026-07-06, when the Owner re-admitted it for pipeline-failure alerting
only — ADR-013, after Teams proved unusable in this MSA-rooted Fabric trial tenant.)

---

## Data Model — Kimball Star Schema (unchanged from parent repo)

| Table | Type | Grain |
|-------|------|-------|
| `fact_loan_application` | Fact | 1 row = 1 loan application (SK_ID_CURR) |
| `fact_bureau_credit` | Fact | 1 row = 1 bureau credit record (SK_ID_BUREAU) |
| `fact_installment_payment` | Fact | 1 row = 1 installment payment (SK_ID_PREV + NUM) |
| `dim_applicant` | Dimension | SCD Type 2 — 1 row per applicant version |
| `dim_loan_type` | Dimension | SCD Type 1 — static lookup |
| `dim_credit_status` | Dimension | SCD Type 1 — static mapping |

**Paradigm:** Kimball chosen over OBT — unchanged from parent repo. See
`docs/ADR/ADR-001-kimball-star-schema.md` + `docs/ADR/ADR-003-kimball-over-obt-sizing.md`.

---

## Governance Framework

| Artefact | Purpose |
|----------|---------|
| `CLAUDE.md` | AI context — stack, stop-gates, anti-shortcut protocol |
| `tests/boundary_contract.py` | Enforces Fabric-only stack (FB1-FB6) |
| `tests/identity_contract.py` | Enforces SK_ID_CURR SCD2 grain fidelity |
| `tests/doc_reference_contract.py` | Enforces no doc drift |
| `.claude/hooks/governance_guard.py` | Pre/post-edit governance nudge + contract runner |
| `.claude/agents/` | 11 specialized agents with veto rights |
| `docs/ADR/` | ADR-001..007 (Fabric versions; 005-007 mirrored from `migration/ADR/` for a unified sequence) |
| `migration/` | Pre-migration design record (canonical ADR-005/006/007), benchmarks, parity plan, sign-off gates |

---

## Parent Repo

Source of truth for the pre-migration (AWS/Snowflake) stack:
`https://github.com/rajeluqman/home-credit-pipeline`

Pre-migration benchmarks: `migration/benchmarks/`
Parity validation plan: `migration/validation/PARITY_TEST_PLAN.md`
Gate sign-off register: `migration/governance/SIGN_OFF.md`
