#!/usr/bin/env python3
"""Doc-reference contract — deterministic gate against documentation drift.

Retargeted per ADR-008 (retire dbt, Gold = Fabric Warehouse T-SQL under `warehouse/`, not
`dbt_fabric/`). Fabric-repo path roots: `notebooks/`, `pipelines/`, `migration/`, `warehouse/`.
Proves every model/path a Markdown doc references ACTUALLY EXISTS, so doc drift fails the build
instead of misleading the next reader.

Stdlib only ($0, no deps). Exit 0 = every checked reference resolves. Exit 1 = drift.

What it checks:
  C1  MODEL refs — backtick-wrapped tokens shaped like a warehouse object (prefix
      fact_/fct_/dim_/stg_/int_/snap_/bridge_/mart_) must be a real file under
      warehouse/**/*.sql.
  C2  PATH refs — backtick tokens and []() link targets that point at a repo path
      (notebooks/ warehouse/ docs/ tests/ pipelines/ .claude/ scripts/ migration/
      architecture/ learning/) must exist on disk.

Run:  python tests/doc_reference_contract.py
      python tests/doc_reference_contract.py path/to/FILE.md ...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WAREHOUSE_ROOT = REPO / "warehouse"

MODEL_TOKEN = re.compile(r"^(?:fact|fct|dim|stg|int|snap|bridge|mart)_[a-z0-9_]+$")
PATH_ROOTS = ("notebooks/", "warehouse/", "docs/", "tests/", "pipelines/", ".claude/",
              "scripts/", "migration/", "architecture/", "learning/")

# Intentionally-not-yet-existing names a doc may legitimately reference. Each entry MUST
# carry a reason so the allowlist can't quietly rot into a dumping ground.
ALLOW: dict[str, str] = {
    "docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md": "cross-repo reference to parent repo's ADR, superseded by ADR-004-onelake-merge-idempotency.md in this repo",
    "dim_loan_type": "Gate 0 tracked gap (docs/ADR/ADR-005:92, PROJECT_STATUS.md) — never built as a dbt or warehouse/ object, not a grain violation (J-001)",
    "dim_credit_status": "Gate 0 tracked gap (docs/ADR/ADR-005:92, PROJECT_STATUS.md) — never built as a dbt or warehouse/ object, not a grain violation (J-001)",
}


def _known_objects() -> set[str]:
    return {p.stem for p in WAREHOUSE_ROOT.rglob("*.sql")} if WAREHOUSE_ROOT.exists() else set()


def _default_docs() -> list[Path]:
    docs = [p for p in sorted((REPO / "docs").glob("*.md"))]
    adr = sorted((REPO / "docs" / "ADR").glob("*.md")) if (REPO / "docs" / "ADR").exists() else []
    migration_adr = sorted((REPO / "migration" / "ADR").glob("*.md")) if (REPO / "migration" / "ADR").exists() else []
    return docs + adr + migration_adr


def check(docs: list[Path]) -> list[str]:
    known = _known_objects()
    errors: list[str] = []

    backtick = re.compile(r"`([^`]+)`")
    link = re.compile(r"\]\(([^)]+)\)")

    for doc in docs:
        if not doc.exists():
            errors.append(f"{doc}: doc file does not exist")
            continue
        rel = doc.relative_to(REPO)
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for tok in backtick.findall(line):
                tok = tok.strip()
                if MODEL_TOKEN.match(tok) and tok not in known and tok not in ALLOW:
                    errors.append(
                        f"{rel}:{lineno}  C1 model `{tok}` referenced but no "
                        f"warehouse/**/{tok}.sql exists (drift)"
                    )

            candidates = backtick.findall(line) + link.findall(line)
            for cand in candidates:
                cand = cand.strip().split("#", 1)[0].strip()
                if cand.startswith(("http://", "https://", "s3://", "mailto:")):
                    continue
                # strip :NNN line-number suffix (e.g. "docs/ADR/ADR-004.md:96")
                if re.match(r"^(.+\.(?:md|py|sql|yml|yaml|json|sh)):\d+$", cand):
                    cand = cand.rsplit(":", 1)[0]
                if not cand.startswith(PATH_ROOTS):
                    continue
                if "*" in cand or "{" in cand:
                    continue
                if not (REPO / cand).exists():
                    errors.append(f"{rel}:{lineno}  C2 path `{cand}` referenced but not found on disk")

    return errors


def main(argv: list[str]) -> int:
    docs = [Path(a) for a in argv[1:]] if len(argv) > 1 else _default_docs()
    docs = [d if d.is_absolute() else (REPO / d) for d in docs]
    errors = check(docs)
    if errors:
        print(f"DOC-REFERENCE CONTRACT: {len(errors)} drift violation(s)\n")
        for e in errors:
            print(f"  ✗ {e}")
        print("\nFix the doc or add a reasoned entry to ALLOW. Drift is a lie waiting to mislead.")
        return 1
    print(f"DOC-REFERENCE CONTRACT: OK — {len(docs)} doc(s), all model/path references resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
