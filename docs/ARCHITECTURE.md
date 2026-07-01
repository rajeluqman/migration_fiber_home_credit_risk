# Architecture: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port; no real Fabric provisioning yet
> (`migration/governance/SIGN_OFF.md` Gate 0 unsigned). Per-layer decisions and rationale
> live in `migration/ADR/ADR-006-fabric-native-service-mapping.md` — read that first.

## Stack
| Layer | Tool | Notes |
|-------|------|-------|
| Storage | OneLake (Fabric) | Bronze + Silver + Gold, one logical lake, native ACID/time-travel |
| Bronze | OneLake Lakehouse (Delta, native) | ingested via Fabric Notebook, orchestrated by Data Factory |
| Silver | Fabric Spark Notebook (Runtime 1.3 = Spark 3.5) | SHA-256 masking, transforms, native Delta MERGE |
| Silver→Gold bridge | Native Delta MERGE (`MERGE INTO ... ON SK_ID_CURR`) | ADR-004 — no Snowpipe-style COPY-INTO-only restriction (that constraint is gone) |
| Gold | dbt Core + `dbt-fabric` adapter + Fabric Warehouse (T-SQL) | Kimball Star Schema — dbt is a NAMED EXCEPTION, third-party OSS (ADR-006 §4) |
| Orchestration | Data Factory pipeline (drag-drop canvas) | 3 chained pipelines, replaces Airflow |
| Quality | Inline notebook assertions (gate) + Purview DQ (catalog, not a gate) | ADR-006 §5 — two-layer design |
| BI | Power BI Direct Lake | reads Gold OneLake Delta directly, no import/refresh cycle |
| Analytics | SQL Analytics Endpoint (auto on every Lakehouse) | query layer only, replaces Databricks Serverless SQL |

## CRITICAL Constraint
Spark ONLY inside `notebooks/` (Fabric Spark runtime) — no standalone PySpark elsewhere.
No AWS SDK, no Snowflake connector, no Airflow, no Slack SDK — these are the platforms Fabric
replaced (`tests/boundary_contract.py` FB1-FB6). dbt Core is the one named exception to
"Fabric-only" (ADR-006 §4), flagged not silenced.

## Data Flow
application_train.csv (307k)  ─┐
bureau.csv (1.7M)              ├─→ Kaggle API → Fabric Notebook → OneLake Bronze (Delta)
bureau_balance.csv (27M)       ├─→ Fabric Spark Silver Notebook → SHA-256 mask → Delta MERGE
installments_payments.csv      ├─→ dbt-fabric Gold → Fabric Warehouse → Power BI Direct Lake
POS_CASH_balance.csv           ├─→
credit_card_balance.csv        ─┘

## Migration provenance
This is a re-platform of the parent repo `home-credit-pipeline` (AWS Glue + Snowflake +
Databricks + Airflow + Slack + Great Expectations), not a re-design. See
`migration/ADR/ADR-005-fabric-full-migration-decision.md` for why, and
`migration/ADR/ADR-006-fabric-native-service-mapping.md` for the full per-layer mapping table
and consequences (8 of 9 layers fully Fabric-native, dbt is the one exception).
