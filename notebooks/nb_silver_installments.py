"""Fabric Spark Notebook — Silver transform for installments_payments.csv.

Ports the parent repo's `glue/glue_silver_installments.py`. Grain:
(SK_ID_PREV, NUM_INSTALMENT_NUMBER) — matches `fact_installment_payment`'s
grain in docs/PIPELINE_SPEC.md. Depends only on `nb_silver_application.py`
completing (docs/PIPELINE_SPEC.md 5.2). No PII masking applies to this table.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from notebooks.silver_common import dedup_latest, merge_into_silver

KEY_COLS = ["SK_ID_PREV", "NUM_INSTALMENT_NUMBER"]


def transform(bronze_df: DataFrame) -> DataFrame:
    df = dedup_latest(bronze_df, KEY_COLS)
    df = df.withColumn("AMT_INSTALMENT", F.col("AMT_INSTALMENT").cast("float")).withColumn(
        "AMT_PAYMENT", F.col("AMT_PAYMENT").cast("float")
    )
    return df


def run(spark: SparkSession, bronze_path: str, silver_path: str) -> None:
    bronze_df = spark.read.format("delta").load(bronze_path)
    merge_into_silver(spark, transform(bronze_df), silver_path, KEY_COLS)


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    run(
        spark,
        bronze_path="Tables/bronze_installments_payments",
        silver_path="Tables/silver_installments_payments",
    )
