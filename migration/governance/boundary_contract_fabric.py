#!/usr/bin/env python3
"""Fabric-stack boundary contract — portable gate for the new dedicated Fabric repo.

Wire into the new repo's CI and .claude/hooks/ (analogous to the parent repo's
tests/boundary_contract.py + .claude/hooks/governance_guard.py pattern).

Enforced rules:
  FB1  no boto3/botocore import (AWS SDK — stack is Fabric/Azure, not AWS)
  FB2  no snowflake-connector-python / snowflake.connector import (Gold is Fabric Warehouse)
  FB3  no apache-airflow / airflow import (orchestration is Data Factory, not Airflow)
  FB4  [LIFTED 2026-07-06 — ADR-013] previously banned slack_sdk/slackclient (alerting was
       Teams). Teams proved unusable in this MSA-rooted Fabric trial tenant (Power Platform BAP
       blocks first-party OAuth; requires paid M365 licence — MIGRATION_JOURNEY.md J-023). Owner
       overrode a @scope-guardian VETO (J-024) and re-admitted Slack as the pipeline-failure
       alerting channel (a plain Incoming Webhook POST — no SDK imported). FB1-FB3 are unaffected
       and remain hard bans; only Slack is re-admitted, only for alerting.
  FB5  dbt-absence — no profiles.yml/dbt_project.yml anywhere, no `import dbt` (ADR-008: dbt
       retired entirely, Gold is Fabric Warehouse T-SQL stored procedures under warehouse/)
  FB6  no pyspark standalone import outside notebooks/ (Spark only inside Fabric notebooks)
  FB7  capacity-lifecycle control-plane carve-out (ADR-009) — the only permitted component
       outside the Fabric workspace boundary is a single external directory (automation/ or
       infra/) that: (a) every file cites ADR-009, (b) only one such directory exists (not
       both), (c) the same FB1-FB3 SDK bans still apply inside it. The literal "3 actions on
       1 named resource" hard-cap is a design constraint enforced by @scope-guardian review at
       Gate 1 build time — not statically countable from file contents alone, so this contract
       does not claim to enforce it by itself.

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
    "automation/*.py",
    "automation/**/*.py",
    "infra/*.py",
    "infra/**/*.py",
]
PY_GLOBS_NOTEBOOKS = ["notebooks/*.py"]

DBT_DENYLIST_FILENAMES = {"profiles.yml", "dbt_project.yml"}

IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_.]+)")

ALWAYS_DENY: dict[str, str] = {
    "boto3": "FB1 — stack is Fabric/Azure, AWS SDK not permitted",
    "botocore": "FB1 — stack is Fabric/Azure, AWS SDK not permitted",
    "snowflake": "FB2 — Gold compute is Fabric Warehouse (T-SQL), Snowflake connector not permitted",
    "airflow": "FB3 — orchestration is Data Factory pipelines, Airflow not permitted",
    # FB4 Slack ban LIFTED 2026-07-06 (ADR-013) — Slack re-admitted as the alerting channel after
    # Teams proved unusable in this tenant; alert is a plain webhook POST, no slack_sdk imported.
    "dbt": "FB5 — dbt is retired entirely (ADR-008); Gold is Fabric Warehouse T-SQL under warehouse/",
}

NOTEBOOKS_ONLY_DENY: dict[str, str] = {
    "pyspark": (
        "FB6 — Spark is only permitted inside notebooks/ "
        "(Fabric Spark runtime); standalone PySpark outside notebooks/ is not permitted"
    ),
}

FB7_CONTROL_PLANE_DIRS = ("automation", "infra")


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


def _scan_dbt_absence(errors: list[str]) -> None:
    for path in REPO.rglob("*"):
        if path.is_file() and path.name in DBT_DENYLIST_FILENAMES:
            errors.append(
                f"{path.relative_to(REPO)}: FB5 — dbt is retired (ADR-008); "
                f"'{path.name}' must not exist anywhere in the repo"
            )


def _scan_fb7(errors: list[str]) -> None:
    present = [d for d in FB7_CONTROL_PLANE_DIRS if (REPO / d).is_dir()]
    if len(present) > 1:
        errors.append(
            f"FB7 — more than one external control-plane directory found {present}; "
            "ADR-009 authorises exactly one (Logic App control-plane component only)"
        )
    for dirname in present:
        root = REPO / dirname
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(REPO)
            text = path.read_text(errors="ignore")
            if "ADR-009" not in text:
                errors.append(
                    f"{rel}: FB7 — external control-plane file does not cite ADR-009 "
                    "(migration/governance/SIGN_OFF.md Gate 0.5); presumed scope creep"
                )
            for banned in ("boto3", "botocore", "snowflake", "airflow"):
                if re.search(rf"^\s*(?:import|from)\s+{banned}\b", text, re.MULTILINE):
                    errors.append(
                        f"{rel}: FB7 — external control-plane dir must still honour the FB1-FB3 "
                        f"bans; found banned import '{banned}'"
                    )


def check() -> list[str]:
    errors: list[str] = []

    for pattern in PY_GLOBS_ALL:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, {**ALWAYS_DENY, **NOTEBOOKS_ONLY_DENY})

    for pattern in PY_GLOBS_NOTEBOOKS:
        for path in REPO.glob(pattern):
            _scan_python(path, errors, ALWAYS_DENY)

    _scan_dbt_absence(errors)
    _scan_fb7(errors)

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
            "\n   See docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md (FB5) and "
            "docs/ADR/ADR-009-capacity-lifecycle-automation.md (FB7) for the allowed service "
            "mapping. Fix before proceeding.",
            file=sys.stderr,
        )
        return 1
    print(
        "✅ fabric boundary contract OK "
        "(no AWS SDK, no Snowflake connector, no Airflow, dbt absent, "
        "FB4 Slack-ban lifted per ADR-013, FB7 control-plane carve-out clean)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
