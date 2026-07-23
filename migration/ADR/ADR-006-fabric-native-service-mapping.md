# ADR-006: Fabric-Native Service Mapping (All Layers)

**Status:** Proposed — pending ADR-005 sign-off before any provisioning.
**Date:** 2026-06-30
**Owner:** Raja Ahmad Luqman

## Context
ADR-005 decided to migrate fully to the Microsoft Fabric ecosystem. This ADR decides
**which specific Fabric service replaces each current component**, resolves the dbt
exception, and resolves the data-quality gating approach. Every service chosen must be
native to Fabric or the Microsoft 365 tenant — no third-party tooling unless explicitly
named as a flagged exception here.

## Per-Layer Decisions

### 1. Ingestion orchestration (replaces `bronze/download_dataset.py` + Airflow)
**Decision: Fabric Data Factory pipeline (drag-drop canvas) orchestrates a Fabric Notebook
that runs the Kaggle download script.**

- Data Factory is the native orchestration layer in Fabric — ADF canvas, identical
  drag-drop UX the user already knows, native Fabric workspace citizen.
- Kaggle API has no Fabric-native connector (verified: Fabric Data Factory connector
  catalog does not list Kaggle as of 2026-06-30). The download logic (`download_dataset.py`
  style) therefore lives inside a **Fabric Notebook** invoked as a pipeline activity —
  this keeps compute inside the Fabric workspace boundary. The Kaggle API call is an
  external HTTP call, not a new Fabric service; it is the unavoidable external boundary
  acknowledged in ADR-005 §"Scope (out)".
- **Drag-drop scope:** pipeline-level orchestration (sequence activities, handle pass/fail
  branching, send alerts) is all drag-drop in Data Factory. **The transform and download
  logic itself stays in notebooks/code** — Dataflows Gen2 (the low-code alternative) is
  NOT used for Silver-layer transform because PII DI-002 SHA-256 sentinel-before-NULL
  ordering, XNA→NULL normalisation, dedup and Delta MERGE semantics cannot be faithfully
  expressed in a drag-drop Power Query canvas without risking silent misapplication of the
  mask-order constraint.

### 2. Bronze/Silver/Gold storage (replaces S3 Delta + Snowflake)
**Decision: OneLake Lakehouse (Delta format, native) for all three medallion layers.**

- OneLake is Fabric's single unified storage — one logical data lake per tenant, Delta
  Parquet by default, ACID + time travel preserved. S3 Delta and Snowflake are both
  replaced by one storage surface.
- No cross-cloud egress: every Fabric engine (Spark notebook, Warehouse SQL endpoint,
  Power BI Direct Lake) reads the same OneLake path — zero data copies between layers.
- Bronze Lakehouse, Silver Lakehouse, and Gold Lakehouse/Warehouse are separate Fabric
  items in the same workspace, maintaining medallion separation without separate billing.

### 3. Silver transform compute (replaces 5 AWS Glue PySpark jobs)
**Decision: 5 Fabric Spark Notebooks (one per Glue job) — PySpark code ports ~1:1.**

- Fabric Runtime 1.3 = Spark 3.5 (Glue 4.0 = Spark 3.3) — API surface is the same
  engine family, minor version ahead. Delta Lake integration is native in Fabric Spark
  (no `DATALAKE_FORMATS=delta` env-var workaround, no manual `--conf` classpath).
- Idempotency improvement over the current stack: Fabric Spark can execute
  `MERGE INTO <delta_table> ON SK_ID_CURR ...` directly in the notebook — no
  Snowpipe-style COPY-INTO-only restriction (see `docs/ADR/ADR-004-*:90-96` for the
  original workaround this eliminates). Upstream idempotency no longer needs a downstream
  dbt `QUALIFY ROW_NUMBER()` dedup as a backstop — see ADR-007 for how this gets proven.
- Each notebook maps to one Glue job: `nb_silver_application`, `nb_silver_bureau`,
  `nb_silver_balance_tables`, `nb_silver_installments`, `nb_silver_previous_application`.
- Notebooks are scheduled via Data Factory pipeline activities (see §1), replacing the
  3 chained Airflow DAGs.

### 4. Gold/mart transform (replaces dbt Core + Snowflake)
> ⚠️ **PROPOSED SUPERSESSION (2026-07-01):** the Owner ruled "Fabric-only" absolute, exercising
> the "Option B" fallback below. This §4 decision (dbt retained) is superseded by
> `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` (**Accepted 2026-07-01**, Gate 0.5). Original text
> left intact per ADR discipline.

**Decision: dbt Core retained with `dbt-fabric` adapter (type: fabric) — NAMED EXCEPTION.**

- dbt Core is NOT a Fabric-native service. It is third-party OSS. This is the one
  explicit exception to the "Fabric-only" rule, logged here rather than silently kept.
- **Why retained:** Fabric Warehouse supports T-SQL and has a `dbt-fabric` adapter
  (`dbt-microsoft-fabric`, PyPI, actively maintained). The Kimball star schema, 5 mart
  models, and the SCD2 `dbt snapshot` strategy (`snap_applicant.sql`, `strategy: check`,
  `unique_key: applicant_id`) have no equivalent native-Fabric rebuild path at comparable
  fidelity — Fabric has no built-in SCD2 snapshot service; a pure T-SQL stored-proc
  rebuild of the same SCD2 logic is feasible but is a materially larger rebuild than a
  profile/adapter swap.
- **What changes:** `dbt_home_credit/profiles.yml` → adapter `type: fabric`, target
  Fabric Workspace endpoint. Model SQL files will need dialect review (Snowflake SQL →
  T-SQL): date functions, `QUALIFY` clause, `FLATTEN`, `LATERAL FLATTEN` — these do not
  exist in T-SQL and must be rewritten. The `boundary_contract_fabric.py` enforces
  `type: fabric` (not snowflake) in the new repo's profiles.
- **Option B (full native rebuild, no dbt):** replace dbt with Fabric Warehouse stored
  procedures + Data Factory pipeline execution. Achieves "zero third-party tooling" but
  loses test-as-code, snapshot strategy, and schema.yml lineage documentation. Not
  recommended; flagged as an available path if the owner's "Fabric-only" requirement is
  meant to be absolute rather than pragmatic.

### 5. Data quality gating (replaces Great Expectations)
**Decision: Two-layer DQ — inline notebook assertions (gating) + Purview DQ (catalog/lineage).**

- Great Expectations is third-party OSS — not Fabric-native. Replacing it with
  **Purview DQ** alone is not viable as a hard FAIL gate: Purview DQ rules run as scans
  against a registered data asset, they do not return a synchronous pass/fail boolean a
  Data Factory pipeline can branch on (confirmed design review, 2026-06-30).
- **Layer 1 — inline notebook assertions (the gate):** each Silver/Gold notebook includes
  a final cell that computes the same checks as the current GX suites
  (`bronze_suite` WARN-only, `silver_suite` FAIL-block) using plain PySpark/Python
  `assert` statements — no GX library dependency. The notebook exits non-zero on
  assertion failure; the Data Factory pipeline's activity outcome routes to a
  Teams-notification failure branch. This exactly replicates the current WARN/FAIL
  gate semantics without GX as a runtime dependency.
- **Layer 2 — Purview DQ (descriptive, not gating):** Purview DQ scans registered
  OneLake tables for profiling (completeness, uniqueness, null rates), populates the
  Fabric Data Catalog with lineage and quality scores. This is observability, not a
  hard gate. It complements Layer 1 rather than replacing it.

### 6. Pipeline alerting (replaces Slack webhook / `SlackWebhookOperator`)
> **⚠️ SUPERSEDED for the pass/fail-alert channel by ADR-013 (2026-07-06)** (`docs/ADR/ADR-013-slack-alerting-override.md`).
> Teams proved genuinely unusable in the real MSA-rooted Fabric trial tenant (Power Platform BAP
> blocks first-party OAuth + needs a paid M365 licence — `MIGRATION_JOURNEY.md` J-023). Owner
> overrode a @scope-guardian VETO (J-024) and re-admitted a Slack Incoming Webhook for
> pipeline-failure alerting, lifting the FB4 Slack ban. Original Teams rationale kept below for the
> migration record; the current alerting channel is Slack.

**Decision (superseded — see banner): Data Activator + Teams — fully M365/Fabric native.**

- **Pass/fail pipeline alerts:** Data Factory pipeline failure branch → Teams channel
  via a built-in Office 365 Outlook/Teams connector activity (native, no webhook token).
  This replicates the current `BashOperator` curl-to-Slack functionality natively.
- **Metric-threshold alerts (Data Activator):** Data Activator reads a Fabric
  Real-Time Intelligence eventstream or a Power BI semantic model and fires a reflex
  action (Teams notification / email) when a monitored metric crosses a threshold —
  e.g. default-rate drift, Silver row-count outside expected range. This is the layer
  that goes *beyond* what Slack webhooks could do (data-condition awareness, not just
  pipeline-status awareness).
- Slack is **removed entirely** — it is a third-party service outside the Fabric/M365
  ecosystem, and Teams (same M365 tenant as the Fabric workspace) covers both the
  pass/fail and the metric-threshold use cases natively.

### 7. Serving / query layer (replaces Databricks Serverless SQL)
**Decision: Fabric SQL Analytics Endpoint (auto-provisioned on every Lakehouse).**

- Every Lakehouse in Fabric automatically exposes a read-only SQL endpoint — no
  provisioning, no separate cluster, no per-query credit. This replaces Databricks
  Serverless SQL completely at zero marginal cost.
- Databricks is **removed entirely** — its only role in the current stack is query-only
  (`tests/boundary_contract.py` ST2), and the SQL endpoint provides the same
  capability natively.

### 8. BI (Power BI Direct Lake — no change in product, big change in mode)
**Decision: Power BI Direct Lake mode against Gold OneLake Delta.**

- Power BI is already in the stack. The change is the *connection mode*: import/refresh
  (current, data copied into the semantic model) → **Direct Lake** (reads Delta files
  directly from OneLake, no copy, no refresh schedule). Zero latency between a Gold model
  update and what the dashboard shows.
- This is the single highest-visible end-user benefit of the Fabric migration and
  requires no BI rebuild — just a semantic model configuration change.

## Full mapping summary

| Current component | Fabric replacement | Native? |
|---|---|---|
| `download_dataset.py` + shell | Fabric Notebook (invoked by Data Factory) | Yes |
| Airflow 3 DAGs | Data Factory pipeline (drag-drop) | Yes |
| S3 + Delta (Bronze/Silver/Gold) | OneLake Lakehouse (Delta, native) | Yes |
| AWS Glue PySpark (5 jobs) | Fabric Spark Notebook (5 notebooks) | Yes |
| Snowflake Gold / dbt-snowflake | Fabric Warehouse + dbt-fabric adapter | **Exception (dbt)** |
| Great Expectations (GX) | Inline notebook assertions + Purview DQ | Yes |
| Slack webhook | ~~Data Activator + Teams connector~~ → **Slack Incoming Webhook** (ADR-013 — Teams unusable in this tenant) + Data Activator | Yes |
| Databricks Serverless SQL | SQL Analytics Endpoint (auto) | Yes |
| Power BI (import mode) | Power BI Direct Lake | Yes |

## Consequences
**(+)** 8 of 9 layers fully Fabric/M365 native.
**(+)** Databricks billing line eliminated entirely.
**(+)** Snowflake billing line eliminated entirely. AWS billing line eliminated entirely.
**(+)** Power BI Direct Lake removes import cycle.
**(+)** Delta MERGE native in Silver notebooks removes ADR-004's idempotency workaround.
**(-)** dbt Core is a retained dependency — one explicit third-party tool in an otherwise
  native stack. If "fully native" means zero third-party, Option B (stored procs) is the
  fallback but at significantly higher rebuild cost.
**(-)** Silver notebook dialect review required — not all Glue PySpark code ports unchanged
  despite the same Spark API (Delta write paths, S3A connector references → OneLake
  paths, `wasbs://` or `abfss://` URIs).
**(-)** dbt T-SQL dialect review required for all mart models — Snowflake SQL constructs
  that don't exist in T-SQL must be rewritten.
