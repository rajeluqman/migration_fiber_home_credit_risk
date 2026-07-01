# REPO_MAP — generated navigation index

> **GENERATED — do not hand-edit.** `python scripts/gen_repo_map.py` rebuilds it from
> ground truth; CI runs `--check` and fails if this file is stale. Purpose is extracted
> from each file's own docstring / first heading / leading comment; *Uses* and *Used by*
> are parsed (`ast` for Python, `ref()` for dbt), never authored.
>
> **This is a pointer, not a cache.** It tells you which file to open — then READ THAT
> FILE FRESH before you edit or assert about it (ANTI-SHORTCUT PROTOCOL, CLAUDE.md).

**73 files mapped.**

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

## Top-level docs

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `CLAUDE.md` | Home Credit Risk Pipeline (Fabric) — AI Context | — | — |
| `COST_LOG.md` | Cost Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `DECISION_LOG.md` | Decision Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `INFRA_LIMITS_LOG.md` | Infra Limits Log — Home Credit Risk Pipeline (Fabric) | — | — |
| `INTERVIEW_GUIDE.md` | Interview Guide — Home Credit Risk Pipeline (Fabric) | — | — |
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

## dbt — staging

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_fabric/models/staging/sources.yml` | — | — | — |
| `dbt_fabric/models/staging/stg_application.sql` | staging: clean + cast application_train, T-SQL dialect (no QUALIFY — Fabric Warehouse) | — | fact_loan_application.sql, int_applicant_attributes.sql |

## dbt — intermediate

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_fabric/models/intermediate/int_applicant_attributes.sql` | intermediate: feeds snap_applicant snapshot, 1:1 pass-through from staging | stg_application.sql | snap_applicant.sql |
| `dbt_fabric/models/intermediate/int_bureau_with_balance.sql` | intermediate: join bureau + bureau_balance, deferred to Fabric Warehouse compute (ADR-003) | — | — |

## dbt — mart

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_fabric/models/mart/dim_applicant.sql` | grain: SK_ID_CURR — SCD Type 2 dimension, 1 row per applicant version (ADR-001) | snap_applicant.sql | — |
| `dbt_fabric/models/mart/fact_bureau_credit.sql` | grain: SK_ID_BUREAU — 1 row per bureau credit record per applicant (ADR-001) | — | — |
| `dbt_fabric/models/mart/fact_installment_payment.sql` | grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER — 1 row per installment payment (ADR-001) | — | — |
| `dbt_fabric/models/mart/fact_loan_application.sql` | grain: SK_ID_CURR — 1 row per loan application (ADR-001) | stg_application.sql | — |

## dbt — snapshots

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_fabric/snapshots/snap_applicant.sql` | (no leading -- comment) | int_applicant_attributes.sql | dim_applicant.sql |

## dbt — other

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `dbt_fabric/dbt_project.yml` | — | — | — |

## Fabric Spark Notebooks

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `notebooks/nb_silver_application.py` | Fabric Spark Notebook stub — Silver transform for application_train. | — | — |
| `notebooks/nb_silver_bureau.py` | Fabric Spark Notebook stub — Silver transform for bureau.csv. | — | — |
| `notebooks/nb_silver_installments.py` | Fabric Spark Notebook stub — Silver transform for installments_payments.csv. | — | — |

## Data Factory pipelines

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `pipelines/README.md` | Data Factory Pipelines (stubs) | — | — |

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
| `migration/governance/SIGN_OFF.md` | Migration Sign-Off Register | — | — |
| `migration/governance/boundary_contract_fabric.py` | Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo. | — | — |
| `migration/staging/DUAL_RUN_PLAN.md` | Dual-Run Plan — Parallel Operation Before Cutover | — | — |
| `migration/validation/PARITY_TEST_PLAN.md` | Parity Test Plan | — | — |
| `migration/validation/parity_check.py` | Parity checker for the Fabric migration. | — | — |

## Tests / contracts

| File | Purpose | Uses | Used by |
|------|---------|------|---------|
| `tests/boundary_contract.py` | Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo. | — | — |
| `tests/doc_reference_contract.py` | Doc-reference contract — deterministic gate against documentation drift. | — | — |
| `tests/identity_contract.py` | Identity contract — deterministic gate over the SCD2 applicant grain. | — | — |
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
