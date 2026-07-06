"""Shared Silver-transform helpers, used by every `notebooks/nb_silver_*.py`.

Not a pipeline stage of its own — pure functions. In Fabric these are attached
to each notebook as a workspace library/resource; locally (ADR-010 D1) it is
just a normal Python import, same Spark 3.5 API either way (zero rewrite).
"""
from __future__ import annotations

import hashlib

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from pyspark.sql.window import Window


def dedup_latest(df: DataFrame, key_cols: list[str], order_col: str = "ingestion_ts") -> DataFrame:
    """PIPELINE_SPEC Silver #1 — keep the latest `order_col` row per `key_cols`."""
    w = Window.partitionBy(*key_cols).orderBy(F.col(order_col).desc())
    return (
        df.withColumn("_rn", F.row_number().over(w))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )


def null_sentinel(df: DataFrame, col: str, sentinel) -> DataFrame:
    """DI-002 (ADR-002) — sentinel -> NULL. Must run BEFORE any hashing of `col`."""
    return df.withColumn(col, F.when(F.col(col) == sentinel, None).otherwise(F.col(col)))


@F.udf(returnType=StringType())
def _sha256(value):
    if value is None:
        return None
    return hashlib.sha256(str(value).encode()).hexdigest()


def sha256_mask(df: DataFrame, col: str, out_col: str) -> DataFrame:
    """ADR-002 — SHA-256 the current contents of `col` into `out_col`.

    This function only hashes; it has no sentinel knowledge. Callers MUST call
    `null_sentinel` on `col` first if a sentinel value applies (ADR-002 order).
    """
    return df.withColumn(out_col, _sha256(F.col(col)))


def merge_into_silver(
    spark: SparkSession,
    updates: DataFrame,
    silver_path: str,
    key_cols: list[str],
) -> None:
    """ADR-004 — native Delta MERGE upsert.

    Both `whenMatchedUpdateAll` and `whenNotMatchedInsertAll` are mandatory: an
    insert-only MERGE silently reintroduces the duplicate-row failure mode this
    ADR exists to remove (ADR-004 consequences).
    """
    if not DeltaTable.isDeltaTable(spark, silver_path):
        updates.write.format("delta").save(silver_path)
        return

    target = DeltaTable.forPath(spark, silver_path)
    cond = " AND ".join(f"t.{k} = s.{k}" for k in key_cols)
    (
        target.alias("t")
        .merge(updates.alias("s"), cond)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )
