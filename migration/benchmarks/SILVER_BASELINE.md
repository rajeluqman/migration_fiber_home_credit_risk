# Silver Layer Baseline — Full-Scale AWS Glue Output (Pre-Migration)

> Every number here is from the parent repo's real Glue Silver run evidence.
> Source: `PROJECT_STATUS.md` ~771-788 ("Real row counts verified for all 7 Silver tables
> via a local PySpark+S3A read") and `INFRA_LIMITS_LOG.md` rows for the two OOM-risk tables.

**Evidence method:** real AWS Glue job runs (G.1X×2, Glue 4.0 = Spark 3.3), full 58.4M
row source, output written to `s3://home-credit-risk-staging/silver/` as Delta tables,
verified via `SELECT COUNT(*)` / `COUNT(DISTINCT pk)` / PySpark `.count()` post-run
(not assumed from `COPY INTO` return values alone — both methods agreed).

**Migration parity target:** the Fabric Silver notebooks must produce these exact counts
before Gate 2 of `governance/SIGN_OFF.md` can close.

## Silver table output counts (full-scale)

| Silver table | Row count | Source row count | Δ | Why |
|---|---|---|---|---|
| silver_application | **307,511** | 307,511 | 0 | 100% passthrough; no filter, dedup preserves all rows (PK `SK_ID_CURR` already unique in source) |
| silver_bureau | **1,716,428** | 1,716,428 | 0 | 100% passthrough; `SK_ID_BUREAU` unique in source |
| silver_bureau_balance | **610,965** | 27,299,925 | −26,688,960 | `MONTHS_BALANCE = 0` filter (current-month snapshot only) + dedup; see note below |
| silver_previous_application | **1,670,214** | 1,670,214 | 0 | 100% passthrough |
| silver_installments | **12,861,994** | 13,605,401 | −743,407 | dedup on `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)` — 94.5% retention, 5.46% dedup rate |
| silver_pos_cash | **10,001,358** | 10,001,358 | 0 | 100% passthrough |
| silver_credit_card | **3,840,312** | 3,840,312 | 0 | 100% passthrough |

**Source citations:**
- silver_application, silver_bureau, silver_bureau_balance (610,965):
  `INFRA_LIMITS_LOG.md` row "Glue OOM risk, full-scale bureau_balance — RESOLVED":
  "Output verified: silver_bureau 1,716,428 rows (100% passthrough), silver_bureau_balance
  610,965 rows (post MONTHS_BALANCE=0 filter + dedup)."
- silver_installments (12,861,994):
  `INFRA_LIMITS_LOG.md` row "Glue OOM risk, full-scale installments_payments — RESOLVED":
  "Output verified: silver_installments 12,861,994 rows (94.5% retained, dedup on
  (SK_ID_PREV, NUM_INSTALMENT_NUMBER) — 5.46% dedup rate, PROJECT_STATUS.md:782)."
- silver_previous_application, silver_pos_cash, silver_credit_card:
  `PROJECT_STATUS.md` ~771-788: "Real row counts verified for all 7 Silver tables."

## PII masking state (silver_application)
Source: `PROJECT_STATUS.md` ~129-131: "PII masking confirmed present on silver_application
(`DAYS_BIRTH_MASKED`/`DAYS_EMPLOYED_MASKED` populated, raw `DAYS_BIRTH`/`DAYS_EMPLOYED`
dropped from the Delta schema)."

| Column | State in Silver |
|---|---|
| `DAYS_BIRTH` | **ABSENT** (dropped) |
| `DAYS_EMPLOYED` | **ABSENT** (dropped) |
| `DAYS_BIRTH_MASKED` | **PRESENT** (sentinel→NULL→SHA-256, per ADR-002 order) |
| `DAYS_EMPLOYED_MASKED` | **PRESENT** (sentinel→NULL→SHA-256, per ADR-002 order) |

The Fabric Silver notebook `nb_silver_application` must produce the same column
presence/absence — verified by the inline notebook assertion (ADR-006 §5 "Layer 1")
before Gate 2 can close.

## bureau_balance filter note
The 27.3M → 610,965 reduction (~97.8% drop) is expected business logic, not data loss.
The Silver job filters to `MONTHS_BALANCE = 0` (current-month state only) and then
deduplicates — this is the same transform the current `glue/glue_silver_balance_tables.py`
applies. The Fabric notebook must apply the identical filter before the count is compared.
Do NOT compare the Fabric run against the 27,299,925 raw source count.

## GX suite results at sample scale (informational only)
Source: `PROJECT_STATUS.md` ~127-128: "GX silver_suite (FAIL gate): ALL PASS
(silver_application 3/3 expectations incl. PII-mask check; silver_bureau +
silver_bureau_balance SK_ID_BUREAU uniqueness)."
These were run at 4,612-applicant sample scale. The full-scale Fabric run must pass
the same assertions (reimplemented as inline notebook cells per ADR-006 §5) at the
307,511-applicant scale.
