"""Fabric Spark Notebook — Silver transform for application_train.

Implements docs/PIPELINE_SPEC.md Silver Layer transforms 1-6 at SK_ID_CURR
grain. Ports the parent repo's `glue/glue_silver_application.py` logic
unchanged onto Fabric Runtime 1.3 (Spark 3.5) per ADR-005.

Masking order is fixed by ADR-002 (DI-002): DAYS_EMPLOYED sentinel 365243 ->
NULL happens BEFORE SHA-256 hashing, never the reverse (reversing it would
hash every unemployed/retired applicant to the same fixed digest, leaking a
categorical signal — see ADR-002 "Why this order").

SCD2 prep here only stamps is_current/start_date/end_date for the downstream
Gold build (`warehouse/scd2/dim_applicant_scd2_merge.sql`, ADR-008); Silver
does not enforce the one-current invariant — that is the Gold THROW gate
(ADR-008 C4).
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from notebooks.silver_common import dedup_latest, merge_into_silver, null_sentinel, sha256_mask

KEY_COLS = ["SK_ID_CURR"]
SENTINEL_DAYS_EMPLOYED = 365243


def transform(bronze_df: DataFrame) -> DataFrame:
    df = dedup_latest(bronze_df, KEY_COLS)

    df = df.withColumn("DAYS_BIRTH", F.col("DAYS_BIRTH").cast("int")).withColumn(
        "AMT_CREDIT", F.col("AMT_CREDIT").cast("float")
    )

    # DI-002: sentinel -> NULL first ...
    df = null_sentinel(df, "DAYS_EMPLOYED", SENTINEL_DAYS_EMPLOYED)
    df = df.withColumn(
        "ORGANIZATION_TYPE",
        F.when(F.col("ORGANIZATION_TYPE") == "XNA", None).otherwise(F.col("ORGANIZATION_TYPE")),
    )

    # ... THEN hash what remains (ADR-002 order is load-bearing, not cosmetic).
    df = sha256_mask(df, "DAYS_BIRTH", "DAYS_BIRTH_MASKED")
    df = sha256_mask(df, "DAYS_EMPLOYED", "DAYS_EMPLOYED_MASKED")

    df = (
        df.withColumn("is_current", F.lit(True))
        .withColumn("start_date", F.to_date(F.col("ingestion_ts")))
        .withColumn("end_date", F.lit(None).cast("date"))
    )
    return df


def run(spark: SparkSession, bronze_path: str, silver_path: str) -> None:
    bronze_df = spark.read.format("delta").load(bronze_path)
    merge_into_silver(spark, transform(bronze_df), silver_path, KEY_COLS)


if __name__ == "__main__":
    spark = SparkSession.builder.getOrCreate()
    run(spark, bronze_path="Tables/bronze_application_train", silver_path="Tables/silver_application")
