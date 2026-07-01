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

> ⚠️ **Governance-framework port only.** No Fabric workspace has been provisioned, no notebook
> or pipeline has actually run against real data. `migration/governance/SIGN_OFF.md` Gate 0 is
> unsigned. Every claim below is either "code/doc exists" or explicitly marked "(unverified)" —
> see `INTERVIEW_GUIDE.md`.

What **is** true today:
- Full governance framework (this repo) is a 1:1 port of the parent repo `home-credit-pipeline`,
  retargeted to Fabric per `migration/ADR/ADR-006-fabric-native-service-mapping.md`.
- 3 static contracts pass: `tests/boundary_contract.py`, `tests/identity_contract.py`,
  `tests/doc_reference_contract.py`.
- Pre-migration benchmarks (`migration/benchmarks/`) are real numbers pulled from the parent
  repo's proven AWS Glue runs — the bar Fabric output must clear (ADR-007).

---

## Stack

| Layer | Tool |
|-------|------|
| Ingest | Fabric Notebook (Kaggle API download) → Data Factory pipeline |
| Bronze/Silver/Gold storage | OneLake Lakehouse (Delta, native ACID) |
| Silver transform | Fabric Spark Notebook (PySpark, Runtime 1.3 = Spark 3.5) |
| Gold transform | dbt Core + dbt-fabric adapter (`type: fabric`) — Fabric Warehouse T-SQL |
| DQ gate | Inline notebook assertions (PySpark `assert`, WARN/FAIL semantics) |
| DQ catalog | Purview DQ (profiling + lineage, not a gate) |
| Orchestration | Data Factory pipeline (3 chained pipelines) |
| Alerting | Data Factory Teams connector + Data Activator reflex |
| Query layer | SQL Analytics Endpoint (auto on every Lakehouse) |
| BI | Power BI Direct Lake |

**Stack boundary (hard):** no AWS/Snowflake/Airflow/Slack. Enforced by `tests/boundary_contract.py`.

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
