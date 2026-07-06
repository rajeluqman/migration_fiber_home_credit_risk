# BRD: Home Credit Risk Pipeline (Fabric)
> Document  : Business Requirements Document v1.0 (Fabric re-platform)
> Phase     : 1 — BRD
> Status    : SIGNED OFF (parent repo) — carried forward, Fabric layer additions DRAFT
> Owner     : BA (Business Analyst)
> Date      : 2026-06-30

---

## 1. Business Context

Home Credit serves unbanked and underbanked populations who lack traditional credit histories.
The organisation relies on alternative data (bureau records, payment histories, previous
applications) to assess creditworthiness. This document carries forward the parent repo's
signed-off BRD unchanged in business substance — the Fabric migration (ADR-005) is a
platform consolidation, not a new business requirement.

**Business Problem:**
Build a scalable, auditable data pipeline that ingests 7 source tables (300k+ loan application
records), applies data quality gating and PII masking, and surfaces credit risk KPIs in a
governed Gold layer — enabling the Risk Team to identify default-risk segments and the
Compliance Team to demonstrate GDPR-aligned data handling. Now consolidated onto one platform
(Microsoft Fabric) instead of four (AWS + Snowflake + Databricks + Power BI).

**Resume Entry Being Proven (Fabric variant):**
> "Re-platformed a 58M-row credit risk pipeline from a 4-vendor AWS/Snowflake/Databricks stack
> to a fully Fabric-native architecture (OneLake, Fabric Spark, Fabric Warehouse T-SQL, Power BI
> Direct Lake), eliminating cross-cloud egress and consolidating to a single billing/IAM surface."

---

## 2. Stakeholders

| # | Stakeholder       | Role              | Primary Data Need                                       | Priority |
|---|-------------------|-------------------|-----------------------------------------------------------|----------|
| 1 | Risk Team         | Primary consumer  | Default rate by segment (loan type, income, employment) | High     |
| 2 | Compliance        | Audit & oversight | PII masking evidence + SCD Type 2 audit trail           | High     |
| 3 | Portfolio Mgmt    | Secondary consumer| Loan portfolio health KPIs, credit amount distribution  | Medium   |
| 4 | Data Engineering  | Pipeline owner    | Schema alignment, data quality checks, pipeline uptime  | High     |

---

## 3. Business Requirements — MoSCoW Priority (unchanged substance, Fabric mechanism)

### Must Have (blocking downstream, Phase 1 scope)

| # | Requirement | Business Value | Success Metric |
|---|-------------|---------------|----------------|
| BR-01 | Ingest all 7 source CSV tables from Kaggle to OneLake Bronze | Baseline for all analytics | Row count match: Bronze = source ± 0 |
| BR-02 | Apply PII masking (SHA-256) on quasi-identifiers (DAYS_BIRTH, DAYS_EMPLOYED) before Silver layer | GDPR alignment, no raw PII in analytics | Inline assertion: masked ≠ original values |
| BR-03 | Implement SCD Type 2 for dim_applicant (start_date, end_date, is_current) | Compliance audit trail for applicant history | is_current=True count = unique SK_ID_CURR |
| BR-04 | Calculate Default Rate KPI in Gold layer (fact_loan_application) | Core risk metric for Risk Team | Formula verified vs manual SQL count |
| BR-05 | Inline notebook assertion + Purview DQ suite at Bronze, Silver, Gold layers | Data quality gating — no bad data downstream | Assertion log + Purview DQ catalog entry per layer |
| BR-06 | Quarantine bad rows — do not block pipeline for non-critical failures | Pipeline resilience | Quarantine table populated for HIGH/MEDIUM severity |

### Should Have (important, not blocking Phase 1 sign-off)

| # | Requirement | Business Value |
|---|-------------|---------------|
| BR-07 | Bureau delinquency rate KPI (integration of bureau.csv) | Enriched risk view per applicant |
| BR-08 | Data Factory pipeline orchestration with Slack pass/fail alerts (ADR-013 — was Teams) | Operational visibility |
| BR-09 | Income-to-Credit Ratio metric per segment | Risk signal beyond default flag |

### Could Have (Phase 2 backlog)

| # | Requirement |
|---|-------------|
| BR-10 | Previous application count per applicant (fact_bureau_credit enrichment) |
| BR-11 | Credit card balance trend analysis (credit_card_balance.csv integration) |
| BR-12 | POS cash balance delinquency trend |

### Won't Have (out of scope — explicitly excluded)

| Exclusion | Reason |
|-----------|--------|
| ML prediction model | Not data engineering scope. Resume entry is pipeline, not ML. |
| Real-time streaming / Kafka | Source data is static CSV — CDC simulation via Delta MERGE, not streaming |
| New tool suggestions outside Fabric stack boundary | ADR-006 locks the service mapping; `tests/boundary_contract.py` enforces it |

---

## 4. KPIs — Explicit Formulas (unchanged, Gold layer now Fabric Warehouse)

| # | KPI | Explicit Formula | Grain | Frequency | Source Table |
|---|-----|-----------------|-------|-----------|-------------|
| KPI-01 | Default Rate | `COUNT(SK_ID_CURR WHERE TARGET=1) / COUNT(SK_ID_CURR) * 100` | Overall + per loan type | Daily | fact_loan_application |
| KPI-02 | Avg Credit Amount by Loan Type | `AVG(AMT_CREDIT) GROUP BY NAME_CONTRACT_TYPE` | Per loan type | Daily | fact_loan_application |
| KPI-03 | Bureau Delinquency Rate | `COUNT(SK_ID_BUREAU WHERE CREDIT_DAY_OVERDUE > 0) / COUNT(SK_ID_BUREAU) * 100` | Overall | Daily | fact_bureau_credit |
| KPI-04 | Income-to-Credit Ratio | `AVG(AMT_INCOME_TOTAL / NULLIF(AMT_CREDIT, 0))` | Per segment | Daily | fact_loan_application + dim_applicant |
| KPI-05 | Avg Days Employed (masked proxy) | `AVG(DAYS_EMPLOYED_MASKED_HASH)` — presence validation only, not numeric aggregation | Per income bracket | Weekly | dim_applicant |

---

## 5. Data Sources Overview (unchanged from parent repo)

| # | File | Rows (approx) | Description | Pipeline Layer |
|---|------|---------------|-------------|---------------|
| 1 | application_train.csv | 307,511 | Primary loan applications — TARGET variable | Bronze → Silver → Gold (fact_loan_application, dim_applicant) |
| 2 | bureau.csv | 1,716,428 | Bureau credit records per applicant | Bronze → Silver → Gold (fact_bureau_credit) |
| 3 | bureau_balance.csv | 27,299,925 | Monthly bureau balance statuses | Bronze → Silver (supporting bureau aggregation) |
| 4 | previous_application.csv | 1,670,214 | Previous loan applications at Home Credit | Bronze → Silver (Should Have — Phase 2 Gold) |
| 5 | installments_payments.csv | 13,605,401 | Installment payment records | Bronze → Silver → Gold (fact_installment_payment) |
| 6 | POS_CASH_balance.csv | 10,001,358 | POS and cash loan balance history | Bronze (Could Have integration) |
| 7 | credit_card_balance.csv | 3,840,312 | Credit card balance history | Bronze (Could Have integration) |

---

## 6. Business Rules

| # | Rule | Owner | Enforced At |
|---|------|-------|-------------|
| BR-RULE-01 | TARGET column: 0 = repaid, 1 = defaulted. NULL TARGET rows = quarantine. | DQS | Silver inline assertion |
| BR-RULE-02 | SK_ID_CURR must be unique in application_train (1 application per row) | DQS | Bronze inline assertion |
| BR-RULE-03 | bureau.SK_ID_CURR must exist in application_train (referential integrity) | DQS | Silver inline assertion |
| BR-RULE-04 | AMT_CREDIT > 0 always. Zero or negative = quarantine. | DQS | Silver inline assertion |
| BR-RULE-05 | DAYS_BIRTH and DAYS_EMPLOYED masked via SHA-256 before Silver write | DE | Fabric Spark Silver notebook |
| BR-RULE-06 | SCD Type 2: only one is_current=True record per SK_ID_CURR in dim_applicant | AE | warehouse/ T-SQL Gold (ADR-008) |

---

## 7. Out of Scope

- Real-time data ingestion (source is static CSV, no CDC available)
- ML model development or scoring pipeline
- New tools not in the Fabric stack boundary (ADR-006)
- bureau_balance.csv Gold integration (deferred — 27M rows, memory risk)

---

## 8. Sign-off Gate — Phase 1

Carried forward from parent repo (BA ✅ | PO ✅ | DQS ✅ | PM ✅, 2026-05-12). Fabric-specific
additions in this document are DRAFT pending @scope-guardian and @data-architect review of
`migration/ADR/ADR-006-fabric-native-service-mapping.md`.
