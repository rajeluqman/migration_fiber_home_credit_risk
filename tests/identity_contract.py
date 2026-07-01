#!/usr/bin/env python3
"""Identity contract — deterministic gate over the SCD2 applicant grain.

Ported 1:1 from the parent repo's tests/identity_contract.py, retargeted to this repo's
dbt project root (`dbt_fabric/` not `dbt_home_credit/`). Encodes @data-architect's "exactly
1 is_current=TRUE row per applicant" SCD2 guarantee statically, WITHOUT requiring a live
Fabric Warehouse connection — it checks the dbt SOURCE (snapshot config + mart alias SQL),
not warehouse data. This is unchanged by the Fabric migration (ADR-005: re-platform, not
re-grain) — only the dbt project root path changes.

Stdlib only. Exit 0 = contract holds. Exit 1 = hard violation.

Rules:
  ID1  snap_applicant.sql must declare unique_key='applicant_id' and strategy='check'
       (SCD2-via-check, not timestamp — ADR-001 locked this so a stray strategy swap is caught)
  ID2  dim_applicant.sql (mart alias) must reference snap_applicant and derive is_current
       from dbt_valid_to (the dbt-snapshot-native SCD2 columns), not a hand-rolled flag
  ID3  every fact model declaring a grain comment must reference a real SK_ID_* column name
       in its grain line (catches a renamed/typo'd grain comment going stale vs the SQL)

Run:  python tests/identity_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DBT_ROOT = REPO / "dbt_fabric"
SNAPSHOT = DBT_ROOT / "snapshots" / "snap_applicant.sql"
MART_DIM = DBT_ROOT / "models" / "mart" / "dim_applicant.sql"
MART_DIR = DBT_ROOT / "models" / "mart"

GRAIN_COMMENT_RE = re.compile(r"--\s*grain", re.IGNORECASE)
SK_ID_RE = re.compile(r"SK_ID_\w+|sk_id_\w+", re.IGNORECASE)


def check() -> list[str]:
    errors: list[str] = []

    # ID1
    if not SNAPSHOT.exists():
        errors.append(f"ID1: {SNAPSHOT.relative_to(REPO)} missing — SCD2 snapshot not found")
    else:
        text = SNAPSHOT.read_text()
        if "unique_key='applicant_id'" not in text and 'unique_key="applicant_id"' not in text:
            errors.append("ID1: snap_applicant.sql unique_key is not 'applicant_id' (grain drift)")
        if "strategy='check'" not in text and 'strategy="check"' not in text:
            errors.append("ID1: snap_applicant.sql strategy is not 'check' (SCD2 strategy drift from ADR-001)")

    # ID2
    if not MART_DIM.exists():
        errors.append(f"ID2: {MART_DIM.relative_to(REPO)} missing — dim_applicant mart model not found")
    else:
        text = MART_DIM.read_text()
        if "snap_applicant" not in text:
            errors.append("ID2: dim_applicant.sql does not reference snap_applicant (SCD2 source broken)")
        if "dbt_valid_to" not in text:
            errors.append("ID2: dim_applicant.sql does not derive is_current from dbt_valid_to "
                           "(hand-rolled current-flag risks drifting from the snapshot)")

    # ID3 — every mart SQL file with a grain comment must name a real-looking SK_ID column
    if MART_DIR.exists():
        for sql_file in sorted(MART_DIR.glob("*.sql")):
            for lineno, line in enumerate(sql_file.read_text().splitlines(), 1):
                if GRAIN_COMMENT_RE.search(line) and not SK_ID_RE.search(line):
                    errors.append(
                        f"ID3: {sql_file.relative_to(REPO)}:{lineno}: grain comment present "
                        f"but no SK_ID_* column named — grain comment may be stale: {line.strip()!r}"
                    )

    return errors


def main() -> int:
    errors = check()
    if errors:
        print(f"\n❌ IDENTITY CONTRACT FAILED — {len(errors)} violation(s):", file=sys.stderr)
        for e in errors:
            print(f"   • {e}", file=sys.stderr)
        print("\n   See docs/DATA_MODEL.md + docs/ADR/ADR-001-kimball-star-schema.md. Fix before proceeding.",
              file=sys.stderr)
        return 1
    print("✅ identity contract OK (SK_ID_CURR / SCD2 grain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
