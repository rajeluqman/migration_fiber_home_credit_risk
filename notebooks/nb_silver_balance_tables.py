"""Fabric Spark Notebook — Silver transform for the balance tables
(bureau_balance.csv, POS_CASH_balance.csv, credit_card_balance.csv).

Ports the parent repo's `glue/glue_silver_balance_tables.py`. bureau_balance
is the 27M-row table — size the Fabric Spark node pool against the parent
repo's proven headroom (`migration/benchmarks/INFRA_BASELINE.md`). Depends
only on `nb_silver_application.py` completing (docs/PIPELINE_SPEC.md 5.2). No
PII masking applies to any of these 3 tables.

Grains:
  bureau_balance       -> (SK_ID_BUREAU, MONTHS_BALANCE)
  POS_CASH_balance     -> (SK_ID_PREV, MONTHS_BALANCE)
  credit_card_balance  -> (SK_ID_PREV, MONTHS_BALANCE)
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession

from notebooks.silver_common import dedup_latest, merge_into_silver

BUREAU_BALANCE_KEYS = ["SK_ID_BUREAU", "MONTHS_BALANCE"]
POS_CASH_KEYS = ["SK_ID_PREV", "MONTHS_BALANCE"]
CREDIT_CARD_KEYS = ["SK_ID_PREV", "MONTHS_BALANCE"]


def transform_bureau_balance(bronze_df: DataFrame) -> DataFrame:
    return dedup_latest(bronze_df, BUREAU_BALANCE_KEYS)


def transform_pos_cash(bronze_df: DataFrame) -> DataFrame:
    return dedup_latest(bronze_df, POS_CASH_KEYS)


def transform_credit_card(bronze_df: DataFrame) -> DataFrame:
    return dedup_latest(bronze_df, CREDIT_CARD_KEYS)


def run(spark: SparkSession, bronze_root: str, silver_root: str) -> None:
    bureau_balance = spark.read.format("delta").load(f"{bronze_root}/bronze_bureau_balance")
    merge_into_silver(
        spark,
        transform_bureau_balance(bureau_balance),
        f"{silver_root}/silver_bureau_balance",
        BUREAU_BALANCE_KEYS,
    )

    pos_cash = spark.read.format("delta").load(f"{bronze_root}/bronze_pos_cash_balance")
    merge_into_silver(
        spark, transform_pos_cash(pos_cash), f"{silver_root}/silver_pos_cash_balance", POS_CASH_KEYS
    )

    credit_card = spark.read.format("delta").load(f"{bronze_root}/bronze_credit_card_balance")
    merge_into_silver(
        spark,
        transform_credit_card(credit_card),
        f"{silver_root}/silver_credit_card_balance",
        CREDIT_CARD_KEYS,
    )


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    run(spark, bronze_root="Tables", silver_root="Tables")
