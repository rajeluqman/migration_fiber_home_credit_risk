# Parity Test Plan

> Operationalises ADR-007's validation protocol. Tells you exactly which commands to run,
> in which order, against which manifests, to satisfy Gate 2 conditions G1–G5 and G8
> (idempotency) in `governance/SIGN_OFF.md`.

## Step 0 — Capture the pre-migration manifest (run ONCE, before any Fabric work)

From the current AWS/Snowflake stack, generate the reference manifest. Run against the
`HOME_CREDIT_RISK.STAGING.*` tables for the 4 tables that exist there, and against the
Silver Delta output for all 7:

```python
# Run from the parent repo after the last Glue Silver run completes.
# Produces: benchmarks/silver_manifest_YYYYMMDD.json
import json, datetime
manifest = {
    "generated": datetime.date.today().isoformat(),
    "source": "AWS Glue Silver + Snowflake STAGING",
    "tables": {
        "silver_application":    {"row_count": 307511,   "pk": "SK_ID_CURR",  "pk_distinct": 307511,  "pk_nulls": 0},
        "silver_bureau":         {"row_count": 1716428,  "pk": "SK_ID_BUREAU","pk_distinct": 1716428, "pk_nulls": 0},
        "silver_bureau_balance": {"row_count": 610965,   "pk": "SK_ID_BUREAU","pk_distinct": 610965,  "pk_nulls": 0},
        "silver_installments":   {"row_count": 12861994, "pk": "SK_ID_PREV+NUM_INSTALMENT_NUMBER", "pk_distinct": 12861994, "pk_nulls": None},
        "silver_previous_application": {"row_count": 1670214,  "pk": "SK_ID_PREV", "pk_distinct": None, "pk_nulls": None},
        "silver_pos_cash":       {"row_count": 10001358, "pk": None, "pk_distinct": None, "pk_nulls": None},
        "silver_credit_card":    {"row_count": 3840312,  "pk": None, "pk_distinct": None, "pk_nulls": None},
    }
}
with open("benchmarks/silver_manifest_baseline.json", "w") as f:
    json.dump(manifest, f, indent=2)
```

The 4 Snowflake-STAGING tables have PK/null data from live queries — the 3 remaining
tables have row_count only (from `SILVER_BASELINE.md`; Snowflake PKs were never captured
because the tables were never loaded to STAGING, see `SNOWFLAKE_STAGING_BASELINE.md` gap
note).

## Step 1 — Run Fabric Silver notebooks and capture Fabric manifest

After all 5 Fabric Spark notebooks complete their first full run, run the equivalent
manifest capture against the OneLake Lakehouse:

```python
# Run from the new Fabric repo (inside a notebook or local PySpark session
# pointed at the Fabric Lakehouse endpoint).
# Produces: fabric_run/silver_manifest_YYYYMMDD.json
from pyspark.sql import SparkSession
import json, datetime

spark = SparkSession.builder.getOrCreate()
tables = {
    "silver_application":    ("SK_ID_CURR",  None),
    "silver_bureau":         ("SK_ID_BUREAU", None),
    "silver_bureau_balance": ("SK_ID_BUREAU", None),
    "silver_installments":   (None, ("SK_ID_PREV", "NUM_INSTALMENT_NUMBER")),
    "silver_previous_application": ("SK_ID_PREV", None),
    "silver_pos_cash":       (None, None),
    "silver_credit_card":    (None, None),
}
manifest = {"generated": datetime.date.today().isoformat(), "source": "Fabric OneLake Silver", "tables": {}}
for table_name, (pk_col, composite_pk) in tables.items():
    df = spark.read.format("delta").load(f"abfss://<workspace>@onelake.dfs.fabric.microsoft.com/<lakehouse>.Lakehouse/Tables/silver/{table_name}")
    row_count = df.count()
    pk_distinct = df.select(pk_col).distinct().count() if pk_col else None
    pk_nulls = df.filter(f"{pk_col} IS NULL").count() if pk_col else None
    manifest["tables"][table_name] = {"row_count": row_count, "pk": pk_col or str(composite_pk), "pk_distinct": pk_distinct, "pk_nulls": pk_nulls}
with open("fabric_run/silver_manifest_run1.json", "w") as f:
    json.dump(manifest, f, indent=2)
```

## Step 2 — Run parity_check.py (Tier 1-3 gate)

```bash
python validation/parity_check.py \
    benchmarks/silver_manifest_baseline.json \
    fabric_run/silver_manifest_run1.json
```

Expected: all green, exit 0. Any exit 1 = hard block on Gate 2, do not proceed.

## Step 3 — PII mask check (Tier 4, silver_application only)

The inline assertion in `nb_silver_application` (last cell) must already have run and
logged PASS. Additionally verify manually:

```sql
-- Run in Fabric Warehouse or Lakehouse SQL endpoint
SELECT COUNT(*) FROM silver.silver_application WHERE DAYS_BIRTH IS NOT NULL;
-- Expected: 0

SELECT COUNT(*) FROM silver.silver_application WHERE DAYS_BIRTH_MASKED IS NULL;
-- Expected: 0 (all rows have the masked value)
```

## Step 4 — Dedup counts check (Tier 5)

```bash
# Included in parity_check.py output for these two tables.
# Additionally verify the filter logic directly:
# silver_bureau_balance must be 610,965 NOT 27,299,925 — the MONTHS_BALANCE=0 filter
# must have been applied.  If the notebook produced 27.3M rows, the filter was missed.
```

## Step 5 — Idempotency test (G8, mandatory before Gate 2 closes)

```bash
# 1. Run all 5 Silver notebooks a SECOND TIME against the same source data.
# 2. Capture manifest run2:
#    fabric_run/silver_manifest_run2.json
# 3. Run:
python validation/parity_check.py \
    --idempotency \
    fabric_run/silver_manifest_run1.json \
    fabric_run/silver_manifest_run2.json
```

Expected: identical row/PK counts both runs, exit 0. A higher row count in run2
indicates the MERGE INTO is inserting instead of upserting (ADR-007 idempotency failure
mode — MERGE clause missing `WHEN MATCHED THEN UPDATE`).

## Acceptance criteria summary

| Tier | Check | Tool | Pass condition |
|---|---|---|---|
| T1 | Row count match | `parity_check.py` | delta == 0 for all 7 tables |
| T2 | PK uniqueness | `parity_check.py` | pk_distinct == row_count for 4 keyed tables |
| T3 | Null PK | `parity_check.py` | pk_nulls == 0 for 4 keyed tables |
| T4 | PII mask | Manual SQL + notebook log | `DAYS_BIRTH` absent, `DAYS_BIRTH_MASKED` present |
| T5 | Dedup counts | `parity_check.py` | bureau_balance = 610,965; installments = 12,861,994 |
| G8 | Idempotency | `parity_check.py --idempotency` | run2 counts == run1 counts |
