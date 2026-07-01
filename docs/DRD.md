# DRD: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port, pending Phase 2 sign-off

## Source Tables (7 files — unchanged from parent repo)
| File | Rows (approx) | Primary Key | Notes |
|------|--------------|-------------|-------|
| application_train.csv | 307,511 | SK_ID_CURR | Primary fact source |
| bureau.csv | 1,716,428 | SK_ID_BUREAU | Credit bureau records |
| bureau_balance.csv | 27,299,925 | SK_ID_BUREAU | Monthly bureau status |
| previous_application.csv | 1,670,214 | SK_ID_PREV | Past loan applications |
| installments_payments.csv | 13,605,401 | SK_ID_PREV | Payment history |
| POS_CASH_balance.csv | 10,001,358 | SK_ID_PREV | POS loan balance |
| credit_card_balance.csv | 3,840,312 | SK_ID_PREV | Credit card balance |

## Known Data Issues
| Issue | Table | Strategy |
|-------|-------|----------|
| XNA values | application_train (ORGANIZATION_TYPE) | Treat as NULL |
| 365243 magic number | DAYS_EMPLOYED | Flag as anomaly, sentinel→NULL BEFORE SHA-256 (ADR-002, DI-002) |
| High cardinality | OCCUPATION_TYPE | NULL handling required |

## Ingestion Pattern
Static snapshot CSV — simulate CDC via native Delta MERGE upsert in the Fabric Spark Silver
notebook (ADR-004 — no downstream dedup backstop needed, unlike the parent repo's Snowpipe
COPY-INTO-only constraint).

## Sign-off Gate
| Agent | Status |
|-------|--------|
| BA | PENDING |
| DA | PENDING |
| SDE | PENDING |
| DPE | PENDING |
| DQS | PENDING |
| PM | PENDING |
