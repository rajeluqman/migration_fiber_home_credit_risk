"""Fabric Spark Notebook — Bronze materialization from Landing (ADR-011).

Reads the byte-for-byte CSVs staged in `Files/landing/{env}/{batch_id}/` and
materializes each of the 7 modeled source tables into typed-enough Delta
`bronze.{table}`, tagged with ingestion_ts/source_file/batch_id/env and
partitioned by ingestion_date, per docs/PIPELINE_SPEC.md "Bronze Layer".
Kaggle is never called here — Bronze replays from Landing only (ADR-011).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

SOURCE_TABLES = [
    "application_train",
    "bureau",
    "bureau_balance",
    "previous_application",
    "installments_payments",
    "POS_CASH_balance",
    "credit_card_balance",
]


def ingest_one(
    spark: SparkSession,
    landing_dir: str,
    bronze_root: str,
    table: str,
    batch_id: str,
    env: str,
) -> DataFrame:
    """Parse one Landing CSV into a tagged Bronze Delta table, append-only."""
    source_file = f"{table}.csv"
    ingestion_ts = datetime.now(timezone.utc)

    df = (
        spark.read.option("header", True).option("inferSchema", True)
        .csv(f"{landing_dir}/{source_file}")
        .withColumn("ingestion_ts", F.lit(ingestion_ts).cast("timestamp"))
        .withColumn("ingestion_date", F.to_date(F.lit(ingestion_ts)))
        .withColumn("source_file", F.lit(source_file))
        .withColumn("batch_id", F.lit(batch_id))
        .withColumn("env", F.lit(env))
    )

    bronze_path = f"{bronze_root}/bronze_{table.lower()}"
    (
        df.write.format("delta")
        .mode("append")
        .partitionBy("ingestion_date")
        .save(bronze_path)
    )
    return df


def run_all(
    spark: SparkSession, landing_dir: str, bronze_root: str, batch_id: str, env: str
) -> dict[str, DataFrame]:
    return {
        table: ingest_one(spark, landing_dir, bronze_root, table, batch_id, env)
        for table in SOURCE_TABLES
    }


if __name__ == "__main__":
    # Fabric notebook entrypoint. batch_id/env are Data Factory notebook-activity
    # parameters at runtime, not hardcoded (docs/PIPELINE_SPEC.md 5.1).
    spark = SparkSession.builder.getOrCreate()
    batch_id = sys.argv[1] if len(sys.argv) > 1 else "unknown_batch"
    env = sys.argv[2] if len(sys.argv) > 2 else "dev"
    run_all(
        spark,
        landing_dir=f"Files/landing/{env}/{batch_id}",
        bronze_root="Tables",
        batch_id=batch_id,
        env=env,
    )
