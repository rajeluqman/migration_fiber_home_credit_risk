# Data Model: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port
> Paradigm: Kimball — Star Schema (LOCKED, unchanged from parent repo — ADR-001/ADR-005)

## Paradigm Decision
Chosen  : Kimball — Star Schema
Reason  : Analytics aggregation, Fabric Spark manageable joins, Fabric Warehouse cost
          predictable, resume entry alignment. Migration is a compute/storage re-platform,
          not a re-grain (ADR-005) — this decision carries forward unchanged from the parent
          repo's AWS/Snowflake stack.

## Why Not OBT
OBT rejected — bureau_balance 27M rows + installments 13M rows nested Arrays = memory risk.
Kimball Star Schema = safer for a bounded Fabric Spark node pool. Sizing math in ADR-003.

## Fact Tables
### fact_loan_application
- Grain   : 1 row = 1 loan application (SK_ID_CURR) — LOCKED
- Source  : application_train.csv
- Pattern : Snapshot → Delta MERGE upsert (native in Fabric Spark, ADR-004)

### fact_installment_payment
- Grain   : 1 row = 1 installment payment record (SK_ID_PREV + NUM_INSTALMENT_NUMBER) — LOCKED
- Source  : installments_payments.csv
- Pattern : Append + dedup

### fact_bureau_credit
- Grain   : 1 row = 1 bureau credit record per applicant (SK_ID_BUREAU) — LOCKED
- Source  : bureau.csv
- Pattern : Snapshot → Delta MERGE

## Dimension Tables
### dim_applicant — SCD TYPE 2 — LOCKED (resume proof)
- Columns : applicant_id, income, employment, start_date, end_date, is_current
- Source  : application_train.csv
- Mechanism: `dbt snapshot`, `strategy: check`, unchanged by the Fabric migration — the
  dbt-fabric adapter is dialect-agnostic for snapshot logic (ADR-006 §4)

### dim_loan_type — SCD TYPE 1
- Columns : loan_type_id, loan_type_name
- Source  : NAME_CONTRACT_TYPE from application_train

### dim_credit_status — SCD TYPE 1
- Columns : status_id, status_code, status_description
- Source  : Credit bureau status codes

## Sign-off Gate
| Agent | Status |
|-------|--------|
| DA | PENDING |
| DPE | PENDING |
| SDE | PENDING |
| AE | PENDING |
| PM | PENDING |
