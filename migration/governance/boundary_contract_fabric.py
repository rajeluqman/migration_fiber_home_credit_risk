#!/usr/bin/env python3
"""Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo.

Wire into the new repo's CI and .claude/hooks/ (analogous to the parent repo's
tests/boundary_contract.py + .claude/hooks/governance_guard.py pattern).

Enforced rules:
  FB1  no boto3/botocore import (AWS SDK — stack is Fabric/Azure, not AWS)
  FB2  no snowflake-connector-python / snowflake.connector import (Gold is Fabric Warehouse)
  FB3  no apache-airflow / airflow import (orchestration is Data Factory, not Airflow)
  FB4  no slack_sdk / slackclient import (alerting is Teams/Data Activator, not Slack)
  FB5  dbt profiles.yml adapter type must be 'fabric' (not snowflake/bigquery/duckdb/postgres)
  FB6  no pyspark standalone import outside notebooks/ (Spark only inside Fabric notebooks)

Stdlib only. Exit 0 = contract holds. Exit 1 = hard violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PY_GLOBS_ALL = [
    "src/*.py",
    "pipelines/*.py",
    "tests/*.py",
    "scripts/*.py",
]
PY_GLOBS_NOTEBOOKS = ["notebooks/*.py"]

PROFILE_FILES = ["dbt_fabric/profiles.yml", "profiles.yml"]

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_.]+)")
TYPE_RE = re.compile(r"^\s*type:\s*(\S+)")

ALWAYS_DENY: dict[str, str] = {
    "boto3": "FB1 — stack is Fabric/Azure, AWS SDK not permitted",
    "botocore": "FB1 — stack is Fabric/Azure, AWS SDK not permitted",
    "snowflake": "FB2 — Gold compute is Fabric Warehouse (T-SQL), Snowflake connector not permitted",
    "airflow": "FB3 — orchestration is Data Factory pipelines, Airflow not permitted",
    "slack_sdk": "FB4 — alerting is Teams/Data Activator, Slack SDK not permitted",
    "slackclient": "FB4 — alerting is Teams/Data Activator, Slack SDK not permitted",
}

NOTEBOOKS_ONLY_DENY: dict[str, str] = {
    "pyspark": (
        "FB6 — Spark is only permitted inside notebooks/ "
        "(Fabric Spark runtime); standalone PySpark outside notebooks/ is not permitted"
    ),
}

ALLOWED_PROFILE_TYPES = {"fabric"}


def _hits(module: str, deny: dict[str, str]) -> str | None:
    parts = module.lower().split(".")
    for i in range(1, len(parts) + 1):
        prefix = ".".join(parts[:i])
        if prefix in deny:
            return deny[prefix]
    return None


def _scan_python(path: Path, errors: list[str], deny: dict[str, str]) -> None:
    rel = path.relative_to(REPO)
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        m = IMPORT_RE.match(line)
        if not m:
            continue
        reason = _hits(m.group(1), deny)
        if reason:
            errors.append(f"{rel}:{lineno}: banned import '{m.group(1)}' — {reason}")


def _scan_profile_adapter(path: Path, errors: list[str]) -> None:
    rel = path.relative_to(REPO)
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
        m = TYPE_RE.match(line)
        if m and m.group(1) not in ALLOWED_PROFILE_TYPES:
            errors.append(
                f"{rel}:{lineno}: dbt profile adapter type '{m.group(1)}' not in {ALLOWED_PROFILE_TYPES} — "
                "FB5: Gold compute is Fabric Warehouse; adapter must be 'fabric'"
            )


def check() -> list[str]:
    errors: list[str] = []

    for pattern in PY_GLOBS_ALL:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, {**ALWAYS_DENY, **NOTEBOOKS_ONLY_DENY})

    for pattern in PY_GLOBS_NOTEBOOKS:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, ALWAYS_DENY)

    for name in PROFILE_FILES:
        path = REPO / name
        if path.exists():
            _scan_profile_adapter(path, errors)

    return errors


def main() -> int:
    errors = check()
    if errors:
        print(
            f"\n❌ FABRIC BOUNDARY CONTRACT FAILED — {len(errors)} violation(s):",
            file=sys.stderr,
        )
        for e in sorted(set(errors)):
            print(f"   • {e}", file=sys.stderr)
        print(
            "\n   See fabric-migration/ADR/ADR-006-fabric-native-service-mapping.md for the "
            "allowed service mapping. Fix before proceeding.",
            file=sys.stderr,
        )
        return 1
    print(
        "✅ fabric boundary contract OK "
        "(no AWS SDK, no Snowflake connector, no Airflow, no Slack SDK, dbt adapter=fabric)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
