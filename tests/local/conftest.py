"""Local Spark fixtures for the ADR-010 Tier 0 harness (ADR-010, FB8).

Every file under tests/local/ must cite ADR-010 per the FB8 boundary rule
(tests/boundary_contract.py `_scan_fb8`). Local PySpark + delta-spark 3.5,
same engine as Fabric Runtime 1.3 — no dialect drift on promotion (ADR-010 D1).
"""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest


@pytest.fixture(scope="session", autouse=True)
def _java_home():
    # Pin JAVA_HOME to a Spark-3.5-compatible JDK regardless of the shell default.
    for candidate in (
        "/usr/local/sdkman/candidates/java/current",
        os.environ.get("JAVA_HOME", ""),
    ):
        if candidate and os.path.exists(candidate):
            os.environ["JAVA_HOME"] = candidate
            break
    yield


@pytest.fixture(scope="session")
def spark():
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession

    builder = (
        SparkSession.builder.appName("home-credit-silver-tier0")
        .master("local[2]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


@pytest.fixture
def tmp_delta_dir():
    path = tempfile.mkdtemp(prefix="silver_tier0_")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session")
def data_dir():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(repo_root, "data")
