"""Fabric Spark Notebook — Silver transform for previous_application.csv.

Ports the parent repo's `glue/glue_silver_previous_application.py`. Grain:
SK_ID_PREV. Depends only on `nb_silver_application.py` completing
(docs/PIPELINE_SPEC.md 5.2). No PII masking applies to this table.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from notebooks.silver_common import dedup_latest, merge_into_silver

KEY_COLS = ["SK_ID_PREV"]


def transform(bronze_df: DataFrame) -> DataFrame:
    df = dedup_latest(bronze_df, KEY_COLS)
    df = df.withColumn("AMT_CREDIT", F.col("AMT_CREDIT").cast("float")).withColumn(
        "DAYS_DECISION", F.col("DAYS_DECISION").cast("int")
    )
    return df


def run(spark: SparkSession, bronze_path: str, silver_path: str) -> None:
    bronze_df = spark.read.format("delta").load(bronze_path)
    merge_into_silver(spark, transform(bronze_df), silver_path, KEY_COLS)


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    run(
        spark,
        bronze_path="Tables/bronze_previous_application",
        silver_path="Tables/silver_previous_application",
    )
