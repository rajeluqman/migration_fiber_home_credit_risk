# REPO_MAP — generated navigation index

> **GENERATED — do not hand-edit.** `python scripts/gen_repo_map.py` rebuilds it from
> ground truth; CI runs `--check` and fails if this file is stale. Purpose is extracted
> from each file's own docstring / first heading / leading comment; *Uses* and *Used by*
> are parsed (`ast` for Python, `ref()` for dbt), never authored.
>
> **This is a pointer, not a cache.** It tells you which file to open — then READ THAT
> FILE FRESH before you edit or assert about it (ANTI-SHORTCUT PROTOCOL, CLAUDE.md).

**96 files mapped.**

## Architecture Decision Records

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `docs/ADR/ADR-001-kimball-star-schema.md` | ADR-001: Data Modelling Paradigm — Kimball Star Schema | — | — |
| `docs/ADR/ADR-002-pii-mask-order.md` | ADR-002: PII Masking Order — Sentinel-Null Before SHA-256 | — | — |
| `docs/ADR/ADR-003-kimball-over-obt-sizing.md` | ADR-003: Kimball-over-OBT Sizing Math (Fabric Spark node-pool memory risk) | — | — |
| `docs/ADR/ADR-004-onelake-merge-idempotency.md` | ADR-004: OneLake Delta MERGE — Silver Idempotency (replaces Snowpipe Silver→Gold Bridge) | — | — |
| `docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md` | ADR-004: Snowpipe Silver→Gold Bridge — Parent Repo Reference (SUPERSEDED) | — | — |
| `docs/ADR/ADR-005-fabric-full-migration-decision.md` | ADR-005: Full Migration to Microsoft Fabric Ecosystem | — | — |
| `docs/ADR/ADR-006-fabric-native-service-mapping.md` | ADR-006: Fabric-Native Service Mapping (All Layers) | — | — |
| `docs/ADR/ADR-007-validation-parity-protocol.md` | ADR-007: Validation, Parity, and Idempotency Protocol | — | — |
| `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` | ADR-008: Retire dbt — Gold/Mart Layer as Fabric Warehouse T-SQL Stored Procedures | — | — |
| `docs/ADR/ADR-009-capacity-lifecycle-automation.md` | ADR-009: Fabric Capacity Lifecycle Automation — Nightly Batch, Azure-Native Resume, In-Fabric Suspend + Watch… | — | — |
| `docs/ADR/ADR-010-local-first-dev-and-fabric-trial.md` | ADR-010: Local-First Development Workflow + Fabric Trial Capacity as First Provisioning Target | — | — |
| `docs/ADR/ADR-011-onelake-landing-zone.md` | ADR-011: Explicit OneLake Landing Zone Ahead of Bronze | — | — |
| `docs/ADR/ADR-012-fabric-trial-spark-pool-sizing.md` | ADR-012: Fabric Trial Spark Pool Sizing — Small, Fixed-Node Custom Pool (mandatory workspace default) | — | — |

## Top-level docs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `CLAUDE.md` | Home Credit Risk Pipeline (Fabric) — AI Context | — | — |
| `COST_LOG.md` | Cost Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `DECISION_LOG.md` | Decision Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `INFRA_LIMITS_LOG.md` | Infra Limits Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `INTERVIEW_GUIDE.md` | Interview Guide — Home Credit Risk Pipeline (Fabric) | — | — |
| `MIGRATION_JOURNEY.md` | Migration Journey — AWS/Snowflake → Fabric (execution log) | — | — |
| `PROJECT_STATUS.md` | Project Status — Home Credit Risk Pipeline (Fabric) | — | — |
| `README.md` | home-credit-risk-pipeline (Fabric Migration) | — | — |
| `docs/ARCHITECTURE.md` | Architecture: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/BRD.md` | BRD: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/DATA_DICTIONARY.md` | Data Dictionary: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/DATA_MODEL.md` | Data Model: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/DQD.md` | DQD: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/DRD.md` | DRD: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/OPS_RUNBOOK.md` | OPS Runbook: Home Credit Risk Pipeline (Fabric) | — | — |
| `docs/PIPELINE_SPEC.md` | Pipeline SPEC: Home Credit Risk Pipeline (Fabric) | — | — |

## Warehouse — staging

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/staging/stg_application.sql` | staging: clean + cast application_train, T-SQL dialect (no QUALIFY — Fabric Warehouse) | — | — |

## Warehouse — intermediate

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/intermediate/int_applicant_attributes.sql` | intermediate: feeds the dim_applicant SCD2 build, 1:1 pass-through from staging | — | — |
| `warehouse/intermediate/int_bureau_with_balance.sql` | intermediate: join bureau + bureau_balance, deferred to Fabric Warehouse compute (ADR-003) | — | — |

## Warehouse — mart

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/mart/dim_applicant.sql` | grain: SK_ID_CURR — SCD Type 2 dimension, 1 row per applicant version (ADR-001) | — | — |
| `warehouse/mart/fact_bureau_credit.sql` | grain: SK_ID_BUREAU — 1 row per bureau credit record per applicant (ADR-001) | — | — |
| `warehouse/mart/fact_installment_payment.sql` | grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER — 1 row per installment payment (ADR-001) | — | — |
| `warehouse/mart/fact_loan_application.sql` | grain: SK_ID_CURR — 1 row per loan application (ADR-001) | — | — |

## Warehouse — SCD2 procs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/scd2/dim_applicant_scd2_fallback.sql` | SCD2 engine (ADR-008 C5) — 2-step UPDATE(expire) + INSERT(new version), NO MERGE statement. | — | — |

## Warehouse — DQ THROW procs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/dq/assert_dim_applicant_one_current.sql` | ADR-008 C4: one-current invariant, BOTH directions, every run. THROWs if any applicant_id has | — | — |
| `warehouse/dq/assert_fact_bureau_credit_grain.sql` | ADR-008 C8: fact grain uniqueness assert, extends the C4 THROW pattern to fact_bureau_credit. | — | — |
| `warehouse/dq/assert_fact_installment_payment_grain.sql` | ADR-008 C8: fact grain uniqueness assert for fact_installment_payment. | — | — |
| `warehouse/dq/assert_fact_loan_application_grain.sql` | ADR-008 C8: fact grain uniqueness assert for fact_loan_application. | — | — |

## Warehouse — other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `warehouse/PROOF_C3_C4_C5.md` | Proof: C3 (NULL-safe change detection) / C4 (one-current THROW gate) / C5 (atomic fallback) | — | — |
| `warehouse/README.md` | Fabric Warehouse T-SQL (Gold layer) | — | — |

## Fabric Spark Notebooks

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `notebooks/nb_bronze_ingest.py` | Fabric Spark Notebook — Bronze materialization from Landing (ADR-011). | — | — |
| `notebooks/nb_silver_application.py` | Fabric Spark Notebook — Silver transform for application_train. | — | — |
| `notebooks/nb_silver_balance_tables.py` | Fabric Spark Notebook — Silver transform for the balance tables | — | — |
| `notebooks/nb_silver_bureau.py` | Fabric Spark Notebook — Silver transform for bureau.csv. | — | — |
| `notebooks/nb_silver_installments.py` | Fabric Spark Notebook — Silver transform for installments_payments.csv. | — | — |
| `notebooks/nb_silver_previous_application.py` | Fabric Spark Notebook — Silver transform for previous_application.csv. | — | — |
| `notebooks/silver_common.py` | Shared Silver-transform helpers, used by every notebooks/nb_silver_*.py. | — | — |

## Data Factory pipelines

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `pipelines/README.md` | Data Factory Pipelines (real, deployed — Gate 4, J-023) | — | — |
| `pipelines/bronze_ingestion.json` | — | — | — |
| `pipelines/gold_warehouse.json` | — | — | — |
| `pipelines/silver_transforms.json` | — | — | — |

## Migration artefacts (benchmarks, validation, staging)

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `migration/ADR/ADR-005-fabric-full-migration-decision.md` | ADR-005: Full Migration to Microsoft Fabric Ecosystem | — | — |
| `migration/ADR/ADR-006-fabric-native-service-mapping.md` | ADR-006: Fabric-Native Service Mapping (All Layers) | — | — |
| `migration/ADR/ADR-007-validation-parity-protocol.md` | ADR-007: Validation, Parity, and Idempotency Protocol | — | — |
| `migration/CLAUDE.md` | Fabric Migration Framework — Directory Context | — | — |
| `migration/PROJECT_STATUS.md` | Fabric Migration — Design-Phase Status | — | — |
| `migration/benchmarks/COST_BASELINE.md` | Cost Baseline — Pre-Migration Economics | — | — |
| `migration/benchmarks/INFRA_BASELINE.md` | Infrastructure Baseline — AWS Glue Pre-Migration Numbers | — | — |
| `migration/benchmarks/SILVER_BASELINE.md` | Silver Layer Baseline — Full-Scale AWS Glue Output (Pre-Migration) | — | — |
| `migration/benchmarks/SNOWFLAKE_STAGING_BASELINE.md` | Snowflake STAGING Baseline — Pre-Migration Gold/Mart Load | — | — |
| `migration/benchmarks/SOURCE_BASELINE.md` | Source CSV Baseline — Pre-Migration Ground Truth | — | — |
| `migration/governance/GATE3_ARCHITECT_REVIEW_J021.md` | Gate 3 — @data-architect verdict on the J-021 Fabric Warehouse dialect/logic fix | — | — |
| `migration/governance/SIGN_OFF.md` | Migration Sign-Off Register | — | — |
| `migration/governance/boundary_contract_fabric.py` | Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo. | — | — |
| `migration/staging/DUAL_RUN_PLAN.md` | Dual-Run Plan — Parallel Operation Before Cutover | — | — |
| `migration/superseded/dim_applicant_scd2_merge.sql` | SUPERSEDED 2026-07-06 (J-021, migration/governance/GATE3_ARCHITECT_REVIEW_J021.md, Condition 3). | — | — |
| `migration/validation/PARITY_TEST_PLAN.md` | Parity Test Plan | — | — |
| `migration/validation/parity_check.py` | Parity checker for the Fabric migration. | — | — |

## Tests / contracts

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `tests/boundary_contract.py` | Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo. | — | — |
| `tests/doc_reference_contract.py` | Doc-reference contract — deterministic gate against documentation drift. | — | — |
| `tests/identity_contract.py` | Identity contract — deterministic gate over the SCD2 applicant grain. | — | — |
| `tests/local/README.md` | tests/local/ — Local-First Silver Dev/Test Harness (ADR-010, FB8) | — | — |
| `tests/local/conftest.py` | Local Spark fixtures for the ADR-010 Tier 0 harness (ADR-010, FB8). | — | — |
| `tests/local/test_bronze_to_silver_sample.py` | ADR-010 Tier 0 — end-to-end sample proof: real Kaggle CSV sample -> Bronze -> | — | — |
| `tests/local/test_silver_application.py` | ADR-010 Tier 0 — local pre-parity proof for nb_silver_application.py. | — | — |
| `tests/unit/test_framework_stubs.py` | Placeholder unit tests — this repo is a governance-framework port (ADR-005/006), no real | — | — |

## Governance hooks

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.claude/hooks/governance_guard.py` | Governance hook — makes Claude check governed docs/ADRs BEFORE and AFTER touching governed | — | — |

## Cabinet agents

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.claude/agents/business-analyst.md` | name: business-analyst | — | — |
| `.claude/agents/cikgu.md` | name: cikgu | — | — |
| `.claude/agents/data-architect.md` | name: data-architect | — | — |
| `.claude/agents/data-platform-engineer.md` | name: data-platform-engineer | — | — |
| `.claude/agents/data-quality-steward.md` | name: data-quality-steward | — | — |
| `.claude/agents/documentation-sherpa.md` | name: documentation-sherpa | — | — |
| `.claude/agents/finops-agent.md` | name: finops-agent | — | — |
| `.claude/agents/infra-reality-agent.md` | name: infra-reality-agent | — | — |
| `.claude/agents/product-owner.md` | name: product-owner | — | — |
| `.claude/agents/scope-guardian.md` | name: scope-guardian | — | — |
| `.claude/agents/senior-data-engineer.md` | name: senior-data-engineer | — | — |

## Learning

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `learning/CURRICULUM.md` | Curriculum — Home Credit Risk Pipeline (Fabric rebuild-from-scratch) | — | — |
| `learning/LEARNING_LOG.md` | Learning Log — Home Credit Risk Pipeline (Fabric) | — | — |

## Config

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `.mcp.json` | — | — | — |

## Other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `requirements.txt` | — | — | — |
| `scripts/gen_repo_map.py` | Repo-map generator — the NAVIGATION half of the ANTI-SHORTCUT PROTOCOL (see CLAUDE.md). | — | — |
