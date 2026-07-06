"""ADR-010 Tier 0 — local pre-parity proof for nb_silver_application.py.

Local PySpark 3.5 + delta-spark harness (ADR-010 D1/D2, FB8). Proves, before
any Fabric CU is spent: dedup keeps the latest row per SK_ID_CURR, PII mask
order (DI-002/ADR-002) is sentinel-NULL BEFORE SHA-256, XNA -> NULL, and the
ADR-004 native Delta MERGE upsert both branches + is idempotent on re-run.
"""
from __future__ import annotations

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pyspark.sql import Row  # noqa: E402

from notebooks.nb_silver_application import SENTINEL_DAYS_EMPLOYED, run, transform  # noqa: E402
from notebooks.silver_common import merge_into_silver  # noqa: E402


def _bronze_rows(spark, rows):
    return spark.createDataFrame([Row(**r) for r in rows])


def test_dedup_keeps_latest_ingestion_ts(spark):
    df = _bronze_rows(
        spark,
        [
            dict(
                SK_ID_CURR=100001,
                DAYS_BIRTH=-9000,
                DAYS_EMPLOYED=-500,
                ORGANIZATION_TYPE="Business Entity Type 3",
                AMT_CREDIT=100000.0,
                ingestion_ts="2026-01-01T00:00:00Z",
            ),
            dict(
                SK_ID_CURR=100001,
                DAYS_BIRTH=-9000,
                DAYS_EMPLOYED=-600,
                ORGANIZATION_TYPE="Business Entity Type 3",
                AMT_CREDIT=120000.0,
                ingestion_ts="2026-02-01T00:00:00Z",
            ),
        ],
    )
    out = transform(df).collect()
    assert len(out) == 1
    assert out[0]["AMT_CREDIT"] == 120000.0  # the later ingestion_ts row survived


def test_pii_mask_order_sentinel_before_hash(spark):
    """DI-002/ADR-002: sentinel row must mask to NULL, never sha256('365243')."""
    df = _bronze_rows(
        spark,
        [
            dict(
                SK_ID_CURR=100002,
                DAYS_BIRTH=-9000,
                DAYS_EMPLOYED=SENTINEL_DAYS_EMPLOYED,
                ORGANIZATION_TYPE="XNA",
                AMT_CREDIT=50000.0,
                ingestion_ts="2026-01-01T00:00:00Z",
            ),
            dict(
                SK_ID_CURR=100003,
                DAYS_BIRTH=-8000,
                DAYS_EMPLOYED=-1200,
                ORGANIZATION_TYPE="Self-employed",
                AMT_CREDIT=75000.0,
                ingestion_ts="2026-01-01T00:00:00Z",
            ),
        ],
    )
    out = {r["SK_ID_CURR"]: r for r in transform(df).collect()}

    sentinel_row = out[100002]
    forbidden_digest = hashlib.sha256(str(SENTINEL_DAYS_EMPLOYED).encode()).hexdigest()
    assert sentinel_row["DAYS_EMPLOYED_MASKED"] is None
    assert sentinel_row["DAYS_EMPLOYED_MASKED"] != forbidden_digest
    assert sentinel_row["ORGANIZATION_TYPE"] is None  # XNA -> NULL

    normal_row = out[100003]
    assert normal_row["DAYS_EMPLOYED_MASKED"] == hashlib.sha256(b"-1200").hexdigest()
    assert normal_row["DAYS_BIRTH_MASKED"] == hashlib.sha256(b"-8000").hexdigest()


def test_merge_both_branches_and_idempotent_rerun(spark, tmp_delta_dir):
    """ADR-004: MERGE must update matched rows AND insert unmatched rows, and a
    byte-identical re-run of the same source must not create duplicate rows."""
    bronze_path = os.path.join(tmp_delta_dir, "bronze_application_train")
    silver_path = os.path.join(tmp_delta_dir, "silver_application")

    v1 = _bronze_rows(
        spark,
        [
            dict(
                SK_ID_CURR=1,
                DAYS_BIRTH=-9000,
                DAYS_EMPLOYED=-500,
                ORGANIZATION_TYPE="School",
                AMT_CREDIT=10000.0,
                ingestion_ts="2026-01-01T00:00:00Z",
            ),
        ],
    )
    v1.write.format("delta").save(bronze_path)
    run(spark, bronze_path=bronze_path, silver_path=silver_path)

    silver_v1 = spark.read.format("delta").load(silver_path)
    assert silver_v1.count() == 1
    assert silver_v1.filter("SK_ID_CURR = 1").collect()[0]["AMT_CREDIT"] == 10000.0

    # Idempotency re-run: re-merge the exact same source again -> no duplicate row.
    run(spark, bronze_path=bronze_path, silver_path=silver_path)
    silver_rerun = spark.read.format("delta").load(silver_path)
    assert silver_rerun.count() == 1

    # New batch: 1 update (matched branch) + 1 new applicant (not-matched branch).
    v2 = _bronze_rows(
        spark,
        [
            dict(
                SK_ID_CURR=1,
                DAYS_BIRTH=-9000,
                DAYS_EMPLOYED=-500,
                ORGANIZATION_TYPE="School",
                AMT_CREDIT=99999.0,
                ingestion_ts="2026-03-01T00:00:00Z",
            ),
            dict(
                SK_ID_CURR=2,
                DAYS_BIRTH=-7000,
                DAYS_EMPLOYED=-100,
                ORGANIZATION_TYPE="Kindergarten",
                AMT_CREDIT=20000.0,
                ingestion_ts="2026-03-01T00:00:00Z",
            ),
        ],
    )
    v2.write.format("delta").mode("append").save(bronze_path)
    run(spark, bronze_path=bronze_path, silver_path=silver_path)

    final = spark.read.format("delta").load(silver_path)
    rows = {r["SK_ID_CURR"]: r for r in final.collect()}
    assert final.count() == 2  # matched-update did not duplicate SK_ID_CURR=1
    assert rows[1]["AMT_CREDIT"] == 99999.0  # matched branch updated in place
    assert rows[2]["AMT_CREDIT"] == 20000.0  # not-matched branch inserted


def test_merge_into_silver_requires_no_duplicate_key_after_repeated_calls(spark, tmp_delta_dir):
    """Guards against an insert-only MERGE (ADR-004's named failure mode)."""
    silver_path = os.path.join(tmp_delta_dir, "silver_direct")
    df = _bronze_rows(spark, [dict(SK_ID_CURR=42, val="a")])
    merge_into_silver(spark, df, silver_path, ["SK_ID_CURR"])
    merge_into_silver(spark, df, silver_path, ["SK_ID_CURR"])
    merge_into_silver(spark, df, silver_path, ["SK_ID_CURR"])

    out = spark.read.format("delta").load(silver_path)
    assert out.count() == 1
