# ADR-002: PII Masking Order — Sentinel-Null Before SHA-256

Status: Accepted (carried forward from parent repo, unchanged by the Fabric migration)
Date  : 2026-06-28 (parent repo); ports verbatim to `notebooks/nb_silver_application.py`
Owner : Data Quality Steward + Senior Data Engineer

## Context
`DAYS_BIRTH` and `DAYS_EMPLOYED` are masked via SHA-256 for GDPR-style compliance. This will
be implemented in `notebooks/nb_silver_application.py` (Fabric Spark Notebook), replacing the
parent repo's `glue/glue_silver_application.py` — same PySpark API surface (Fabric Runtime
1.3 = Spark 3.5, Glue 4.0 = Spark 3.3), same masking logic. `DAYS_EMPLOYED` carries a known
Home Credit dataset anomaly: unemployed/retired applicants are encoded with the sentinel value
`365243` instead of NULL.

## Decision
Masking order is **sentinel-substitution BEFORE hashing**, never the reverse:
1. `365243 → NULL` (DI-002, applies to `DAYS_EMPLOYED` only)
2. `hashlib.sha256(str(value).encode()).hexdigest()` on the remaining non-null values

This ordering is a business-logic rule, not a stack-specific one — it carries forward
unchanged to the Fabric notebook. ADR-005 explicitly scopes the PII mask order as
"re-platformed, not re-designed."

## Why this order, specifically
If SHA-256 ran first, every unemployed/retired applicant's sentinel `365243` would hash to
the **same fixed digest** — turning a data-quality sentinel into a leaked categorical signal
(every row with that exact hash is provably "unemployed/retired"), defeating the purpose of
masking. Nulling the sentinel first removes the value from the hashed domain entirely, so no
inference is possible from the masked column.

## Consequences
(+) The Silver inline assertion gate checks the inverse condition directly:
    `DAYS_EMPLOYED_MASKED not in sha256('365243')` (see `docs/DQD.md` for the full Silver
    gate list) — this replaces the parent repo's GX `silver_suite` check with the same logic,
    no GX library dependency (ADR-006 §5)
(+) `notebooks/nb_silver_application.py` must implement this exact order — a future rewrite
    must replicate the order, not just the output columns
(-) An out-of-order masking bug is silent (column name and type are unchanged; only the
    *meaning* of the masked value differs) — this is exactly why the order needs a named ADR
    and a quality gate, not just a code comment

## Alternatives Rejected
- Mask first, then sentinel-check: rejected — defeats the masking's purpose (see above).
- Drop sentinel rows entirely instead of nulling: rejected — would discard a real population
  segment (unemployed/retired applicants) from `dim_applicant`, breaking BRD KPI coverage.
