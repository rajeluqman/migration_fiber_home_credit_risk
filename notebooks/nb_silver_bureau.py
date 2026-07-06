"""Fabric Spark Notebook — Silver transform for bureau.csv.

Ports the parent repo's `glue/glue_silver_bureau.py`. Grain: SK_ID_BUREAU.
No PII columns on this table (DAYS_BIRTH/DAYS_EMPLOYED live only on
application_train) — no ADR-002 masking applies here. Runs after
`nb_silver_application.py` per the Data Factory dependency chain
(docs/PIPELINE_SPEC.md 5.2).
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from notebooks.silver_common import dedup_latest, merge_into_silver

KEY_COLS = ["SK_ID_BUREAU"]


def transform(bronze_df: DataFrame) -> DataFrame:
    df = dedup_latest(bronze_df, KEY_COLS)
    df = (
        df.withColumn("DAYS_CREDIT", F.col("DAYS_CREDIT").cast("int"))
        .withColumn("AMT_CREDIT_SUM", F.col("AMT_CREDIT_SUM").cast("float"))
        .withColumn("AMT_CREDIT_SUM_DEBT", F.col("AMT_CREDIT_SUM_DEBT").cast("float"))
    )
    return df


def run(spark: SparkSession, bronze_path: str, silver_path: str) -> None:
    bronze_df = spark.read.format("delta").load(bronze_path)
    merge_into_silver(spark, transform(bronze_df), silver_path, KEY_COLS)


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    run(spark, bronze_path="Tables/bronze_bureau", silver_path="Tables/silver_bureau")
