# Pipeline SPEC: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port, pending Phase 3 sign-off

## Landing Layer (raw ingress — ADR-011)
Input  : 7 CSV files from Kaggle Competition API (via Fabric Notebook)
Output : OneLake Lakehouse **Files** area, `Files/landing/{env}/{batch_id}/{file}.csv` (raw, unmanaged)
Logic  : Store each CSV **byte-for-byte as received** + SHA-256 checksum + original filename.
         Append-only, immutable — never edited, masked, or typed. Kaggle API is hit **once per
         ingestion, here only** (ADR-011). `{env}` = `ENV` from `.env` (currently always `dev` —
         one Fabric workspace, no separate dev/staging/prod workspaces, ADR-011). This is the
         OneLake Files area of the *same* Lakehouse as Bronze — one storage surface, no new
         service (ADR-006 §2, ADR-011).

## Bronze Layer
Input  : `Files/landing/{env}/{batch_id}/{file}.csv` (the Landing file — NOT the Kaggle API; ADR-011)
Output : OneLake Bronze Lakehouse **Tables**, `bronze.{table}` (Delta, partitioned by ingestion_date)
Logic  : Materialize from Landing — parse CSV → typed Delta + ingestion_ts, source_file, batch_id,
         env (column, not a table/path split — one `bronze.{table}` for all env values).
         Bronze re-materialization replays from Landing, never re-calls Kaggle (ADR-011).

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

## Gold Layer (Fabric Warehouse T-SQL — `warehouse/`, dbt retired per ADR-008)
stg_application.sql                    → view, clean + cast (T-SQL dialect — no QUALIFY)
int_applicant_attributes.sql           → view, feeds the dim_applicant SCD2 build
int_bureau_with_balance.sql            → view, join bureau + bureau_balance
dim_applicant.sql                      → table DDL + `usp_build_dim_applicant` (SCD2, from
                                          `warehouse/scd2/dim_applicant_scd2_fallback.sql`) — grain: SK_ID_CURR
fact_loan_application.sql              → table DDL + `usp_build_fact_loan_application` — grain: SK_ID_CURR
fact_bureau_credit.sql                 → table DDL + `usp_build_fact_bureau_credit` — grain: SK_ID_BUREAU
fact_installment_payment.sql           → table DDL + `usp_build_fact_installment_payment` — grain: SK_ID_PREV + NUM_INSTALMENT_NUMBER

Not yet built (Gate-0 tracked gap, not a violation — same scope as the retired dbt tree):
`dim_loan_type`, `dim_credit_status`, `int_credit_risk_features.sql`, `mart_credit_risk_summary.sql`.

## KPIs
default_rate            = COUNT(TARGET=1) / COUNT(*)
avg_credit_amount       = AVG(AMT_CREDIT) GROUP BY loan_type
bureau_delinquency_rate = SUM(bad_bureau_records) / COUNT(bureau_records)

## 5. Orchestration (Data Factory — replaces Airflow)

### 5.1 Pipeline chain
Three Data Factory pipelines, chained via `Execute Pipeline` activities (wait-on-completion):
`bronze_ingestion` → `silver_transforms` → `gold_dbt`. See `pipelines/`. Within
`bronze_ingestion`, the notebook activity runs two steps in order: **Landing** (Kaggle →
`Files/landing/`, raw) then **Bronze** (Landing → `Tables/bronze_*`, typed Delta) — ADR-011.

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
