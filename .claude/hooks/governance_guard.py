#!/usr/bin/env python3
"""Governance hook — makes Claude check governed docs/ADRs BEFORE and AFTER touching governed
files. Ported 1:1 from the parent repo's `.claude/hooks/governance_guard.py`, retargeted to
this repo's real files (Fabric notebooks / `warehouse/` T-SQL, not Glue/dbt-snowflake).
Retargeted again per ADR-008 (dbt retired — Gold governed paths are now `warehouse/mart/`,
`warehouse/scd2/`, not `dbt_fabric/models/mart/`, `dbt_fabric/snapshots/`).

Wired in .claude/settings.json for Edit|Write|MultiEdit:
  • PreToolUse  → inject a "STOP, read these docs first" reminder when the target file is
                  under governance (non-blocking context nudge).
  • PostToolUse → auto-run the matching contract test(s) after the edit; exit 2 with the
                  failure so Claude is FORCED to see and fix it (hard block).

Contracts wired, by owner (CLAUDE.md governance axes):
  - tests/identity_contract.py               — @data-architect, SK_ID_CURR + SCD2 grain fidelity
  - tests/boundary_contract.py                — @scope-guardian (Spark only inside notebooks/, no
                                                 AWS/Snowflake/Airflow/Slack, dbt absent, FB7/FB8)
  - migration/governance/boundary_contract_fabric.py — @scope-guardian, portable copy of the
                                                 boundary contract (Gate 1, SIGN_OFF.md); run
                                                 alongside tests/boundary_contract.py wherever
                                                 the latter is run, since it is meant to be
                                                 lifted verbatim into a dedicated Fabric repo.

Stdlib only. Never crashes the tool call on its own bug (any internal error → exit 0).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

IDENTITY_MSG = (
    "dim_applicant grain = SK_ID_CURR, SCD2 via a T-SQL MERGE proc (ADR-008 C2/C3 check-column "
    "comparison); exactly 1 is_current=TRUE row per applicant at all times (ADR-001 + DATA_MODEL.md)."
)
BOUNDARY_MSG = (
    "no standalone PySpark outside notebooks/, no AWS/Snowflake/Airflow/Slack "
    "reintroduced, no new ingestion connector beyond the Kaggle API, no dbt reintroduced (FB5)."
)
ERD_MSG = "Clean-ERD/Kimball doctrine: 1 table = 1 grain = 1 entity, SCD strategy locked per dim (ADR-001)."

# (path substring, docs to cite, reminder message, contract scripts to run post-edit)
# Contract scripts are given as paths relative to REPO root (Gate 1: migration/governance/
# boundary_contract_fabric.py is wired alongside tests/boundary_contract.py for every boundary
# rule, since it is the portable copy meant to be lifted verbatim into a dedicated Fabric repo).
BOUNDARY_SCRIPTS = ("tests/boundary_contract.py", "migration/governance/boundary_contract_fabric.py")
IDENTITY_SCRIPTS = ("tests/identity_contract.py",)

RULES: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("notebooks/", "ADR-002 (PII mask order) + docs/ARCHITECTURE.md", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("warehouse/mart/", "ADR-001 + docs/DATA_MODEL.md (.claude/agents/data-architect.md)", ERD_MSG, IDENTITY_SCRIPTS),
    ("warehouse/scd2/", "ADR-001 SCD2 strategy + docs/DATA_MODEL.md + ADR-008 C2-C6", IDENTITY_MSG, IDENTITY_SCRIPTS),
    ("warehouse/dq/", "ADR-008 C4/C8 (THROW assertion gates)", IDENTITY_MSG, IDENTITY_SCRIPTS),
    ("pipelines/", "docs/ARCHITECTURE.md + docs/PIPELINE_SPEC.md (Data Factory chaining)", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("requirements.txt", "docs/ARCHITECTURE.md stack boundary (no Spark outside notebooks/, no AWS/Snowflake/Airflow/Slack, no dbt)", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("automation/", "docs/ADR/ADR-009-capacity-lifecycle-automation.md (FB7 carve-out)", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("infra/", "docs/ADR/ADR-009-capacity-lifecycle-automation.md (FB7 carve-out)", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("migration/governance/", "ADR-006 §4 (Option B) + ADR-008/009 (FB5/FB7) — portable contract copy", BOUNDARY_MSG, BOUNDARY_SCRIPTS),
    ("docs/ADR/", "ADR numbering + docs/DATA_MODEL.md cross-references", ERD_MSG, ()),
]


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except (ValueError, OSError):
        return path or ""


def _matches(rel: str) -> list[tuple[str, str, str, tuple[str, ...]]]:
    return [r for r in RULES if r[0] in rel]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    event = data.get("hook_event_name", "")
    rel = _rel((data.get("tool_input") or {}).get("file_path", ""))
    matches = _matches(rel)
    if not matches:
        return 0

    if event == "PreToolUse":
        lines = [f"⚠️ GOVERNED FILE: {rel} is under governance. Before editing, confirm against:"]
        for _, docs, msg, _ in matches:
            lines.append(f"  - {docs}: {msg}")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "\n".join(lines)}}))
        return 0

    if event == "PostToolUse":
        contracts: list[str] = []
        for _, _, _, scripts in matches:
            for s in scripts:
                if s not in contracts:
                    contracts.append(s)

        failures = []
        for script in contracts:
            proc = subprocess.run(
                [sys.executable, str(REPO / script)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                failures.append(f"--- {script} ---\n{proc.stdout}{proc.stderr}")

        if failures:
            sys.stderr.write("Contract check FAILED after your edit — fix before continuing:\n" + "\n".join(failures))
            return 2  # feeds stderr back to Claude as a blocking error
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # never let a hook bug break the user's tool call
        raise SystemExit(0)
