# DQD: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port, pending Phase 5 sign-off
> Great Expectations replaced by inline notebook assertions + Purview DQ catalog (ADR-006 §5)

## Bronze Layer — Inline Assertions
| Check | Rule | Severity |
|-------|------|----------|
| application_train row count | = 307,511 (staging) | CRITICAL |
| ingestion_ts | NOT NULL | CRITICAL |
| SK_ID_CURR | NOT NULL | CRITICAL |

## Silver Layer — Inline Assertions (hard FAIL gate)
| Check | Rule | Severity |
|-------|------|----------|
| DAYS_BIRTH masked | != original value | CRITICAL |
| DAYS_EMPLOYED masked | != original value | CRITICAL |
| DAYS_EMPLOYED anomaly | 365243 → NULL | HIGH |
| SK_ID_CURR | UNIQUE per table | HIGH |

## Gold Suite (warehouse/ T-SQL THROW assertion procs, dbt retired per ADR-008)
| Check | Rule | Severity |
|-------|------|----------|
| fact_loan_application.SK_ID_CURR | NOT NULL, UNIQUE | CRITICAL |
| dim_applicant.is_current | Only 1 True per applicant | CRITICAL |
| FK: fact → dim_applicant | Referential integrity | CRITICAL |

## Purview DQ (catalog/lineage — descriptive, NOT a gate)
Purview DQ scans registered OneLake tables for profiling (completeness, uniqueness, null
rates) and populates the Fabric Data Catalog with lineage and quality scores. It complements
the inline assertion gate above rather than replacing it — Purview DQ cannot return a
synchronous pass/fail for Data Factory pipeline branching (ADR-006 §5).
