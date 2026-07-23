"""ADR-010 Tier 0 — end-to-end sample proof: real Kaggle CSV sample -> Bronze ->
Silver, for every one of the 5 Silver notebooks (ADR-010 D1/D2, FB8).

Uses a 5k-row sample of the real local CSVs in data/ (gitignored, ADR-010's
"sampled CSV, not the full 58.4M rows") to catch real-schema issues the
synthetic-row tests in test_silver_application.py can't (real dtypes/nulls).
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from notebooks import nb_silver_balance_tables  # noqa: E402
from notebooks import nb_silver_bureau, nb_silver_installments, nb_silver_previous_application

SAMPLE_ROWS = 5000


def _sample_csv(spark, data_dir, filename):
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        pytest.skip(f"{filename} not present locally (data/ is gitignored)")
    return spark.read.option("header", True).option("inferSchema", True).csv(path).limit(SAMPLE_ROWS)


def _bronze_tag(df):
    from pyspark.sql import functions as F

    return (
        df.withColumn("ingestion_ts", F.current_timestamp())
        .withColumn("batch_id", F.lit("test_batch"))
        .withColumn("env", F.lit("dev"))
    )


def test_application_train_sample_end_to_end(spark, data_dir, tmp_delta_dir):
    from notebooks.nb_silver_application import run, transform

    bronze_path = os.path.join(tmp_delta_dir, "bronze_application_train")
    silver_path = os.path.join(tmp_delta_dir, "silver_application")

    df = _bronze_tag(_sample_csv(spark, data_dir, "application_train.csv"))
    df.write.format("delta").save(bronze_path)

    run(spark, bronze_path=bronze_path, silver_path=silver_path)
    silver = spark.read.format("delta").load(silver_path)

    assert silver.count() > 0
    assert silver.filter("ORGANIZATION_TYPE = 'XNA'").count() == 0
    assert "DAYS_BIRTH_MASKED" in silver.columns
    assert "DAYS_EMPLOYED_MASKED" in silver.columns

    # sentinel rows (unemployed/retired) must mask to NULL, never a real hash
    sentinel_masked = transform(df).filter("DAYS_EMPLOYED = 365243").select("DAYS_EMPLOYED_MASKED").distinct().collect()
    assert all(r["DAYS_EMPLOYED_MASKED"] is None for r in sentinel_masked)


def test_bureau_sample_dedup_and_merge(spark, data_dir, tmp_delta_dir):
    bronze_path = os.path.join(tmp_delta_dir, "bronze_bureau")
    silver_path = os.path.join(tmp_delta_dir, "silver_bureau")

    df = _bronze_tag(_sample_csv(spark, data_dir, "bureau.csv"))
    df.write.format("delta").save(bronze_path)

    nb_silver_bureau.run(spark, bronze_path=bronze_path, silver_path=silver_path)
    silver = spark.read.format("delta").load(silver_path)
    assert silver.count() > 0
    assert silver.groupBy("SK_ID_BUREAU").count().filter("count > 1").count() == 0

    # idempotency re-run
    nb_silver_bureau.run(spark, bronze_path=bronze_path, silver_path=silver_path)
    assert spark.read.format("delta").load(silver_path).count() == silver.count()


def test_previous_application_sample_dedup_and_merge(spark, data_dir, tmp_delta_dir):
    bronze_path = os.path.join(tmp_delta_dir, "bronze_previous_application")
    silver_path = os.path.join(tmp_delta_dir, "silver_previous_application")

    df = _bronze_tag(_sample_csv(spark, data_dir, "previous_application.csv"))
    df.write.format("delta").save(bronze_path)

    nb_silver_previous_application.run(spark, bronze_path=bronze_path, silver_path=silver_path)
    silver = spark.read.format("delta").load(silver_path)
    assert silver.count() > 0
    assert silver.groupBy("SK_ID_PREV").count().filter("count > 1").count() == 0


def test_installments_sample_dedup_and_merge(spark, data_dir, tmp_delta_dir):
    bronze_path = os.path.join(tmp_delta_dir, "bronze_installments_payments")
    silver_path = os.path.join(tmp_delta_dir, "silver_installments_payments")

    df = _bronze_tag(_sample_csv(spark, data_dir, "installments_payments.csv"))
    df.write.format("delta").save(bronze_path)

    nb_silver_installments.run(spark, bronze_path=bronze_path, silver_path=silver_path)
    silver = spark.read.format("delta").load(silver_path)
    assert silver.count() > 0
    dup = silver.groupBy("SK_ID_PREV", "NUM_INSTALMENT_NUMBER").count().filter("count > 1").count()
    assert dup == 0


def test_balance_tables_sample_dedup_and_merge(spark, data_dir, tmp_delta_dir):
    bronze_root = tmp_delta_dir
    silver_root = tmp_delta_dir

    bb = _bronze_tag(_sample_csv(spark, data_dir, "bureau_balance.csv"))
    bb.write.format("delta").save(os.path.join(bronze_root, "bronze_bureau_balance"))
    pc = _bronze_tag(_sample_csv(spark, data_dir, "POS_CASH_balance.csv"))
    pc.write.format("delta").save(os.path.join(bronze_root, "bronze_pos_cash_balance"))
    cc = _bronze_tag(_sample_csv(spark, data_dir, "credit_card_balance.csv"))
    cc.write.format("delta").save(os.path.join(bronze_root, "bronze_credit_card_balance"))

    nb_silver_balance_tables.run(spark, bronze_root=bronze_root, silver_root=silver_root)

    bb_silver = spark.read.format("delta").load(os.path.join(silver_root, "silver_bureau_balance"))
    assert bb_silver.count() > 0
    assert bb_silver.groupBy("SK_ID_BUREAU", "MONTHS_BALANCE").count().filter("count > 1").count() == 0

    pc_silver = spark.read.format("delta").load(os.path.join(silver_root, "silver_pos_cash_balance"))
    assert pc_silver.groupBy("SK_ID_PREV", "MONTHS_BALANCE").count().filter("count > 1").count() == 0

    cc_silver = spark.read.format("delta").load(os.path.join(silver_root, "silver_credit_card_balance"))
    assert cc_silver.groupBy("SK_ID_PREV", "MONTHS_BALANCE").count().filter("count > 1").count() == 0
