# Source CSV Baseline — Pre-Migration Ground Truth

> Every number here is the verified raw-CSV row count from the parent repo's evidence
> trail. Source: `PROJECT_STATUS.md` (parent repo) lines ~49-54, "Row counts verified
> (`wc -l` on the downloaded CSVs before Flow-B delete) — all 7 match README.md 'Source
> Tables' exactly."

**Evidence method:** `wc -l` on each downloaded CSV before Flow-B upload-and-delete
(2026-06-30, Phase 1 Step 8 in the parent repo). Re-verified by a second independent
session (`PROJECT_STATUS.md` ~73-76: "independently re-verified live").

**Total:** 58,441,149 rows across 7 files. This is the "58.4M rows" figure cited in
`CLAUDE.md` §"Source Tables" and the portfolio resume claim.

## Table-by-table

| CSV file | Row count | PK column | Notes |
|---|---|---|---|
| application_train.csv | **307,511** | `SK_ID_CURR` | Main applicant table; grain = one row per loan application |
| bureau.csv | **1,716,428** | `SK_ID_BUREAU` | Credit bureau records per applicant |
| bureau_balance.csv | **27,299,925** | composite (`SK_ID_BUREAU`, `MONTHS_BALANCE`) | Largest source table; post-filter Silver count is 610,965 (see SILVER_BASELINE) |
| previous_application.csv | **1,670,214** | `SK_ID_PREV` | Prior loan applications |
| installments_payments.csv | **13,605,401** | composite (`SK_ID_PREV`, `NUM_INSTALMENT_NUMBER`) | Post-dedup Silver count is 12,861,994 |
| POS_CASH_balance.csv | **10,001,358** | composite (`SK_ID_PREV`, `MONTHS_BALANCE`) | |
| credit_card_balance.csv | **3,840,312** | composite (`SK_ID_PREV`, `MONTHS_BALANCE`) | |
| **TOTAL** | **58,441,149** | — | — |

## Sample baseline (Phase-1 dev run only, NOT the migration parity target)
The Phase-1 local-dev run used a stratified 1.5% sample (`scripts/smart_sample.py`,
seed=42, frac=0.015). Sample rows are NOT the migration parity target — the Fabric
migration must match the full-scale numbers above, not the sample.

| File | Sample rows | Default rate | Source |
|---|---|---|---|
| application_train | 4,612 | 0.080659 | `PROJECT_STATUS.md` ~58-60 |
| bureau | 21,799 | — | same |
| bureau_balance | 211,766 | — | same |
| previous_application | 21,393 | — | same |
| installments_payments | 172,406 | — | same |
| POS_CASH_balance | 127,601 | — | same |
| credit_card_balance | 46,923 | — | same |

Full-scale default_rate = 0.080729 (`PROJECT_STATUS.md` ~59); sample captures it to
4 decimal places (0.080659), confirming the stratified sampler preserves the target
distribution — but again, migration parity is against the full-scale 307,511 rows, not
the sample.
