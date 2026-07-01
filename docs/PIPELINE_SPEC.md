# Pipeline SPEC: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port, pending Phase 3 sign-off

## Bronze Layer
Input  : 7 CSV files from Kaggle Competition API (via Fabric Notebook)
Output : OneLake Bronze Lakehouse, `bronze.{table}` (Delta, partitioned by ingestion_date)
Logic  : Store as-is + ingestion_ts, source_file, batch_id, env

## Silver Layer (Fabric Spark Notebook)
Input  : `bronze.{table}`
Output : `silver.{table}`

Transforms:
1. DEDUP       : Keep latest ingestion_ts per SK_ID_CURR
2. TYPE CAST   : DAYS_BIRTH → Integer, AMT_CREDIT → Float
3. NULL HANDLE : DAYS_EMPLOYED = 365243 → NULL + flag
                 ORGANIZATION_TYPE = 'XNA' → NULL
4. PII MASK    : SHA-256(DAYS_BIRTH), SHA-256(DAYS_EMPLOYED) — sentinel→NULL BEFORE hashing (ADR-002, DI-002)
5. SCD PREP    : Add is_current, start_date, end_date for dim_applicant
6. IDEMPOTENCY : `MERGE INTO silver.{table} ON <key> WHEN MATCHED THEN UPDATE WHEN NOT
                 MATCHED THEN INSERT` — native Fabric Spark Delta MERGE (ADR-004), no
                 downstream `QUALIFY ROW_NUMBER()` dedup backstop required

## Gold Layer (dbt-fabric)
stg_application.sql             → clean + cast (T-SQL dialect — no QUALIFY, rewrite as subquery)
stg_bureau.sql                  → clean + cast
int_applicant_attributes.sql    → feeds snap_applicant snapshot
int_credit_risk_features.sql    → join fact tables
fact_loan_application.sql       → grain: SK_ID_CURR
dim_applicant.sql               → grain: SK_ID_CURR (SCD2, from snap_applicant)
fact_bureau_credit.sql          → grain: SK_ID_BUREAU
fact_installment_payment.sql    → grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER
mart_credit_risk_summary.sql    → KPI aggregations

## KPIs
default_rate            = COUNT(TARGET=1) / COUNT(*)
avg_credit_amount       = AVG(AMT_CREDIT) GROUP BY loan_type
bureau_delinquency_rate = SUM(bad_bureau_records) / COUNT(bureau_records)

## 5. Orchestration (Data Factory — replaces Airflow)

### 5.1 Pipeline chain
Three Data Factory pipelines, chained via `Execute Pipeline` activities (wait-on-completion):
`bronze_ingestion` → `silver_transforms` → `gold_dbt`. See `pipelines/`.

### 5.2 Silver notebook dependency chain
`silver_transforms` runs 5 Notebook activities. `nb_silver_bureau` depends on
`nb_silver_application` completing first (referential-integrity assertion); the other 3
notebook tasks only depend on `nb_silver_application`. All 4 downstream notebook tasks fan in
to the Silver inline-assertion gate, which then triggers Gold:

```
nb_application >> nb_bureau
nb_application >> [nb_prev_app, nb_installments, nb_balance]
[nb_bureau, nb_prev_app, nb_installments, nb_balance] >> silver_assertion_gate >> trigger_gold
```
