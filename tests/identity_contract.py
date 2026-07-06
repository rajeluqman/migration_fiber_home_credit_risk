#!/usr/bin/env python3
"""Identity contract — deterministic gate over the SCD2 applicant grain.

Retargeted per ADR-008 (retire dbt, Gold = Fabric Warehouse T-SQL stored procedures under
warehouse/, not dbt_fabric/). Encodes @data-architect's "exactly 1 is_current=TRUE row per
applicant" SCD2 guarantee statically, WITHOUT requiring a live Fabric Warehouse connection — it
checks the T-SQL SOURCE (the SCD2 procs + mart table/proc), not warehouse data. Grain and
identity are unchanged by the dbt retirement (ADR-008: re-platform of the enforcement mechanism,
not a re-grain) — only where the SCD2 logic lives changes.

Stdlib only. Exit 0 = contract holds. Exit 1 = hard violation.

Rules:
  ID1  The SCD2 proc (warehouse/scd2/dim_applicant_scd2_fallback.sql — sole mechanism as of
       J-021; the MERGE-based proc is retired, archived at
       migration/superseded/dim_applicant_scd2_merge.sql, because Fabric Warehouse does not
       support the OUTPUT clause on any statement) must match on `applicant_id` (never
       `applicant_sk` — C6: the surrogate key is not the match key) and must compare exactly
       the 4 tracked columns from ADR-008 C2 (name_income_type, name_education_type,
       name_family_status, cnt_children) — a stray column swap or `SELECT *` is caught here.
  ID2  warehouse/mart/dim_applicant.sql must declare the SCD2 columns natively
       (start_date/end_date/is_current) and its build proc must call one of the
       warehouse/scd2/ procs — not a hand-rolled current-flag disconnected from the SCD2 engine.
  ID3  every warehouse/mart/*.sql file declaring a grain comment must reference a real SK_ID_*
       column name in its grain line (catches a renamed/typo'd grain comment going stale vs the
       SQL).

Run:  python tests/identity_contract.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WAREHOUSE_ROOT = REPO / "warehouse"
SCD2_FALLBACK = WAREHOUSE_ROOT / "scd2" / "dim_applicant_scd2_fallback.sql"
MART_DIM = WAREHOUSE_ROOT / "mart" / "dim_applicant.sql"
MART_DIR = WAREHOUSE_ROOT / "mart"

TRACKED_COLS = [
    "name_income_type",
    "name_education_type",
    "name_family_status",
    "cnt_children",
]

GRAIN_COMMENT_RE = re.compile(r"--\s*grain", re.IGNORECASE)
SK_ID_RE = re.compile(r"SK_ID_\w+|sk_id_\w+", re.IGNORECASE)
MATCH_KEY_RE = re.compile(r"\bapplicant_id\s*=\s*\w+\.applicant_id\b|\btgt\.applicant_id\s*=\s*src\.applicant_id\b", re.IGNORECASE)
ON_CLAUSE_LINE_RE = re.compile(r"\bON\b", re.IGNORECASE)


def _check_scd2_proc(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"ID1: {path.relative_to(REPO)} missing — SCD2 engine not found")
        return
    text = path.read_text()
    if not MATCH_KEY_RE.search(text):
        errors.append(
            f"ID1: {path.relative_to(REPO)} does not match/merge on applicant_id "
            "(grain drift — identity must stay applicant_id, ADR-008 C6)"
        )
    for line in text.splitlines():
        if ON_CLAUSE_LINE_RE.search(line) and "applicant_sk" in line.lower():
            errors.append(
                f"ID1: {path.relative_to(REPO)} appears to use applicant_sk in a match/merge ON "
                "clause — the surrogate key must NOT be the SCD2 match key (ADR-008 C6)"
            )
    for col in TRACKED_COLS:
        if col not in text:
            errors.append(
                f"ID1: {path.relative_to(REPO)} does not reference tracked column '{col}' "
                "(ADR-008 C2 pins exactly these 4 columns for change detection)"
            )


def check() -> list[str]:
    errors: list[str] = []

    # ID1 — the sole SCD2 proc must honour C2/C6
    _check_scd2_proc(SCD2_FALLBACK, errors)

    # ID2
    if not MART_DIM.exists():
        errors.append(f"ID2: {MART_DIM.relative_to(REPO)} missing — dim_applicant mart model not found")
    else:
        text = MART_DIM.read_text()
        if "is_current" not in text or "start_date" not in text or "end_date" not in text:
            errors.append(
                "ID2: warehouse/mart/dim_applicant.sql does not declare the native SCD2 columns "
                "(start_date/end_date/is_current)"
            )
        if "usp_scd2_merge_dim_applicant" not in text and "usp_scd2_fallback_dim_applicant" not in text:
            errors.append(
                "ID2: warehouse/mart/dim_applicant.sql build proc does not call a "
                "warehouse/scd2/ engine (SCD2 source broken)"
            )

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
        print("\n   See docs/DATA_MODEL.md + docs/ADR/ADR-001-kimball-star-schema.md + "
              "docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md. Fix before proceeding.",
              file=sys.stderr)
        return 1
    print("✅ identity contract OK (SK_ID_CURR / SCD2 grain)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
