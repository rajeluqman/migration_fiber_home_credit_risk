# Architecture: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port; no real Fabric provisioning yet
> (`migration/governance/SIGN_OFF.md` Gate 0 unsigned). Per-layer decisions and rationale
> live in `migration/ADR/ADR-006-fabric-native-service-mapping.md` — read that first.

## Stack
| Layer | Tool | Notes |
|-------|------|-------|
| Storage | OneLake (Fabric) | Landing + Bronze + Silver + Gold, one logical lake, native ACID/time-travel |
| Landing | OneLake Lakehouse **Files** (`Files/landing/{env}/{batch_id}/`, raw/unmanaged) | raw CSV byte-for-byte + checksum, immutable ingress — Kaggle hit once here; `{env}` = single workspace `dev` tag, not a separate workspace (ADR-011) |
| Bronze | OneLake Lakehouse **Tables** (Delta, native) | materialized *from Landing* (not Kaggle) via Fabric Notebook, orchestrated by Data Factory (ADR-011) |
| Silver | Fabric Spark Notebook (Runtime 1.3 = Spark 3.5) | SHA-256 masking, transforms, native Delta MERGE |
| Silver→Gold bridge | Native Delta MERGE (`MERGE INTO ... ON SK_ID_CURR`) | ADR-004 — no Snowpipe-style COPY-INTO-only restriction (that constraint is gone) |
| Gold | Fabric Warehouse T-SQL stored procedures, `warehouse/{staging,intermediate,mart,scd2,dq}` | Kimball Star Schema — dbt retired entirely (ADR-008, supersedes ADR-006 §4) |
| Orchestration | Data Factory pipeline (drag-drop canvas) | 3 chained pipelines, replaces Airflow |
| Quality | Inline notebook assertions (gate) + Purview DQ (catalog, not a gate) | ADR-006 §5 — two-layer design |
| BI | Power BI Direct Lake | reads Gold OneLake Delta directly, no import/refresh cycle |
| Analytics | SQL Analytics Endpoint (auto on every Lakehouse) | query layer only, replaces Databricks Serverless SQL |

## CRITICAL Constraint
Spark ONLY inside `notebooks/` (Fabric Spark runtime) — no standalone PySpark elsewhere.
No AWS SDK, no Snowflake connector, no Airflow, no Slack SDK — these are the platforms Fabric
replaced (`tests/boundary_contract.py` FB1-FB6). dbt is retired entirely — no `profiles.yml`/
`dbt_project.yml`/`import dbt` anywhere (FB5, ADR-008, supersedes ADR-006 §4). One narrow, fenced
exception remains: a single external Azure-native capacity-lifecycle control-plane component
citing ADR-009 (FB7).

## Data Flow
application_train.csv (307k)  ─┐
bureau.csv (1.7M)              ├─→ Kaggle API → Fabric Notebook → OneLake Landing (Files/, raw) → Bronze (Tables/, Delta)  [ADR-011]
bureau_balance.csv (27M)       ├─→ Fabric Spark Silver Notebook → SHA-256 mask → Delta MERGE
installments_payments.csv      ├─→ warehouse/ T-SQL Gold → Fabric Warehouse → Power BI Direct Lake
POS_CASH_balance.csv           ├─→
credit_card_balance.csv        ─┘

## Migration provenance
This is a re-platform of the parent repo `home-credit-pipeline` (AWS Glue + Snowflake +
Databricks + Airflow + Slack + Great Expectations), not a re-design. See
`migration/ADR/ADR-005-fabric-full-migration-decision.md` for why, and
`migration/ADR/ADR-006-fabric-native-service-mapping.md` for the original full per-layer mapping
table (9 layers, dbt flagged as the one exception at that time). `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`
later exercised that ADR's own "Option B" fallback: dbt is now retired, so the stack is fully
Fabric-native end to end (9 of 9 layers), with one narrow, fenced exception for capacity
lifecycle only (`docs/ADR/ADR-009-capacity-lifecycle-automation.md`, FB7).
