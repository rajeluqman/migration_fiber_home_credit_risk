# Home Credit Risk Pipeline (Fabric) — AI Context

> Auto-loaded by Claude Code every session. Governance framework ported 1:1 from the parent repo
> `home-credit-pipeline` (AWS/Snowflake stack), retargeted to Microsoft Fabric per
> `migration/ADR/ADR-006-fabric-native-service-mapping.md` — the authoritative per-layer stack
> mapping. Do not re-derive decisions already made there; read it first.

## 🛑 STOP-GATE — read before ANY notebook/model/identity work
This repo is governed. Before you edit a Fabric Spark notebook, a `warehouse/` mart proc, an
SCD2 proc, or a Data Factory pipeline — or before you "proceed" past an identity/grain question —
you MUST:
1. **Open the governing doc first.** Grain/star schema → ADR-001 + `docs/DATA_MODEL.md`.
   PII masking order → ADR-002. Kimball-over-OBT sizing → ADR-003. Stack boundary (Fabric-only,
   Spark only inside notebooks/) → `docs/ARCHITECTURE.md` + `tests/boundary_contract.py`.
   Fabric service mapping → `migration/ADR/ADR-006-fabric-native-service-mapping.md`.
2. **Validate identity BEFORE building downstream.** `dim_applicant` is SCD Type 2 keyed on
   `SK_ID_CURR` (`applicant_id`) — exactly one `is_current = TRUE` row per applicant at all
   times. Run `python tests/identity_contract.py` and `python tests/boundary_contract.py` before
   calling any mart/notebook change done — these are the binding checks, not your judgement.
3. **If a rule and the request conflict, STOP and surface it** — do not silently proceed.
   Mixed-grain dimension, Spark outside notebooks/, AWS/Snowflake/Airflow/Slack reintroduced,
   PII masked in the wrong order (DI-002: sentinel→NULL must happen BEFORE SHA-256) → name it,
   cite the doc, and ask @data-architect / @scope-guardian before writing code.

Enforced three ways: this prompt (soft), `.claude/hooks/governance_guard.py` (blocks edits to
governed files without a context nudge), and CI (`tests/identity_contract.py` +
`tests/boundary_contract.py` + `tests/doc_reference_contract.py`, blocks the PR).

## 🔁 ANTI-SHORTCUT PROTOCOL — read-before-touch, reconcile-before-done
1. **Read-before-touch** — never edit or assert about a file from memory; read it THIS turn.
2. **Enumerate, don't sample** — for "all N tables/notebooks" tasks, get N from `ls`/`grep`
   BEFORE acting (7 source tables, 5 Silver notebooks, 3 chained Data Factory pipelines — verify
   the count, don't recall it).
3. **Reconcile-before-done** — before saying done/fixed/green, restate the request as a
   numbered checklist with `file:line` evidence per item. No evidence = "unverified".
4. **Tag assumptions** — any unchecked load-bearing claim is marked "(unverified)"; any
   reconstructed rationale (no contemporaneous deliberation) is marked
   "(reconstructed — owner confirm)".

The machine half: `tests/doc_reference_contract.py` proves every model/path a doc references
actually exists. `scripts/gen_repo_map.py` generates `architecture/REPO_MAP.md` — a pointer
index, not a cache; it tells you which file to open, then you read that file fresh.

## Project Overview
**Domain**: Consumer credit risk (banking).
**Problem**: Profile credit default risk across 307,511 loan applications + 6 related bureau/
installment/balance tables (≈58.4M rows total across the 7 source CSVs), built as a Kimball
star schema with PII masking and SCD2 historical tracking — same problem as the parent repo,
re-platformed onto Microsoft Fabric.
**Purpose**: Data Engineering portfolio project (single-dev, Raja Ahmad Luqman).

## Stack (Fabric-native, per ADR-006 — locked, not re-litigated per file)
| Layer | Storage / Service | Compute / engine | Notes |
|-------|--------------------|-------------------|-------|
| Source | Kaggle Competition API (`home-credit-default-risk`) | Fabric Notebook (invoked by Data Factory) | 7 CSVs, 300k–27M rows each |
| Landing (raw ingress) | OneLake Lakehouse **Files** (`Files/landing/{env}/{batch_id}/`, raw/unmanaged) | Fabric Notebook | ADR-011 — byte-for-byte CSV + checksum, immutable; Kaggle hit once here; Bronze replays from Landing; `{env}` = single-workspace tag (`dev`), not a separate dev/staging/prod workspace |
| Bronze/Silver/Gold storage | OneLake Lakehouse **Tables** (Delta, native ACID/time-travel) | — | one storage layer (same Lakehouse as Landing), zero cross-cloud egress |
| Silver transform | OneLake Delta | **Fabric Spark Notebook** (Runtime 1.3 = Spark 3.5), 5 notebooks in `notebooks/` | PII mask (DI-002), XNA→NULL, dedup, native Delta MERGE |
| Gold/marts | Fabric Warehouse (T-SQL) | **Fabric Warehouse T-SQL stored procedures**, `warehouse/{staging,intermediate,mart,scd2,dq}` | Kimball star, SCD2 = T-SQL MERGE proc (ADR-008, supersedes ADR-006 §4) — dbt retired entirely |
| Quality | Inline notebook assertions (hard gate) + Purview DQ (catalog, not a gate) | plain PySpark/Python `assert` | two-layer design, ADR-006 §5 |
| Orchestration | — | Data Factory pipeline (drag-drop canvas), `pipelines/` (3 chained pipelines) | replaces Airflow |
| Alerting | Teams connector + Data Activator | Data Factory failure branch / metric-threshold reflex | replaces Slack |
| Serving (query-only) | Gold OneLake | **SQL Analytics Endpoint** (auto-provisioned on every Lakehouse) | replaces Databricks Serverless SQL |
| BI | Gold OneLake Delta | Power BI **Direct Lake** | no import/refresh cycle |

⚠️ Stack boundary: **Spark only inside `notebooks/`** (Fabric Spark runtime) — no standalone
PySpark elsewhere (`tests/boundary_contract.py` FB6). No AWS SDK (FB1), no Snowflake connector
(FB2), no Airflow (FB3), no Slack SDK (FB4). dbt is retired entirely — no `profiles.yml`/
`dbt_project.yml`/`import dbt` anywhere (FB5, ADR-008). One narrow, fenced exception: a single
external capacity-lifecycle control-plane component citing ADR-009 (FB7).

## Architecture of Record
`docs/` — BRD.md, DRD.md, DATA_MODEL.md, ARCHITECTURE.md, PIPELINE_SPEC.md, DATA_DICTIONARY.md,
DQD.md, OPS_RUNBOOK.md, `docs/ADR/` (ADR-001 Kimball-over-OBT paradigm, ADR-002 PII-mask-order,
ADR-003 Kimball-over-OBT sizing, ADR-004 OneLake MERGE idempotency). `migration/ADR/` (ADR-005
full migration decision, ADR-006 Fabric service mapping, ADR-007 validation/parity protocol) —
the pre-migration design record and benchmark evidence trail, carried forward verbatim.
`architecture/REPO_MAP.md` (generated, see above).

**Identity key**: `SK_ID_CURR` (aliased `applicant_id`) — SCD Type 2 via a Fabric Warehouse T-SQL
MERGE proc (`warehouse/scd2/dim_applicant_scd2_merge.sql`, fallback
`dim_applicant_scd2_fallback.sql`), NULL-safe check-column comparison on tracked cols:
`name_income_type`, `name_education_type`, `name_family_status`, `cnt_children` (ADR-008 C2/C3).
Bureau/installment facts key on `SK_ID_BUREAU` / `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)`.
Unchanged from the parent repo — a Fabric migration is a compute/storage re-platform, not a
re-grain (ADR-005); retiring dbt (ADR-008) re-platforms the *enforcement* mechanism, not the grain.

**Governance gate**: @data-architect holds veto on grain/model changes (Kimball star locked,
ADR-001); @scope-guardian holds veto on stack/scope creep (no Spark outside notebooks/, no
AWS/Snowflake/Databricks/Airflow/Slack reintroduced, no new ingestion connectors beyond the
Kaggle API).

## Source Tables (7 files, ≈58.4M rows total — unchanged from parent repo)
| File | Rows |
|------|------|
| application_train.csv | 307,511 |
| bureau.csv | 1,716,428 |
| bureau_balance.csv | 27,299,925 |
| previous_application.csv | 1,670,214 |
| installments_payments.csv | 13,605,401 |
| POS_CASH_balance.csv | 10,001,358 |
| credit_card_balance.csv | 3,840,312 |

## Cabinet (11 agents) — see `.claude/agents/`
**Veto holders**: @data-architect (grain/model) · @scope-guardian (stack/scope, FB1-FB7).
**Build**: @senior-data-engineer (warehouse/ T-SQL + notebooks + Data Factory) · @data-quality-steward
(inline assertions + Purview DQ) · @product-owner (BRD/KPIs) · @business-analyst (DRD +
resume-claim reconciliation) · @data-platform-engineer (Data Factory/Fabric infra) ·
@documentation-sherpa (docs/ADR upkeep) · @finops-agent (Fabric F-SKU + OneLake storage watch) ·
@infra-reality-agent (Fabric Spark node-pool sizing vs. parent repo's AWS Glue baseline —
`migration/benchmarks/INFRA_BASELINE.md`).
**Teaching**: @cikgu (English-first, mental-model → ETL use-case → production bug → debug →
syntax LAST) — NOT a build agent; runs `learning/CURRICULUM.md` drills on `drill/*` branches,
never `main`.

## Migration provenance
This repo's governance framework (this file, `tests/`, `.claude/`, `docs/`, `scripts/`) is a 1:1
port of the parent repo `home-credit-pipeline`, retargeted to the Fabric stack per
`migration/ADR/ADR-006-*`. `migration/` holds the pre-migration design record: the decision ADRs
(005/006/007), real pre-migration benchmarks (`migration/benchmarks/`), the validation/parity
protocol (`migration/validation/`), the dual-run plan (`migration/staging/`), and the gate
sign-off register (`migration/governance/SIGN_OFF.md`). **No Fabric resource has been
provisioned** — ADR-005 stays Proposed until Gate 0 in `migration/governance/SIGN_OFF.md` is
signed.

## What NOT to commit
`.env*`, `data/`, `*.parquet`, raw Kaggle CSVs — keep cost figures estimate-only.

## Token Discipline
1. Checkpoint first: read `PROJECT_STATUS.md` "▶ RESUME HERE" before reading code.
2. Use `architecture/REPO_MAP.md` instead of re-grepping the whole repo for "where is X".
3. Read only files in the current module — max ~3 files/turn.
