#!/usr/bin/env python3
"""Parity checker for the Fabric migration.

Compares two row-count manifests (JSON) and asserts Tier 1-3 and idempotency (G8)
conditions from ADR-007. Stdlib only — no PySpark/pandas needed to run this.

Usage:
  # Parity (baseline vs. Fabric run 1):
  python parity_check.py benchmarks/silver_manifest_baseline.json fabric_run/silver_manifest_run1.json

  # Idempotency (Fabric run 1 vs. Fabric run 2):
  python parity_check.py --idempotency fabric_run/silver_manifest_run1.json fabric_run/silver_manifest_run2.json

Exit codes:
  0 = all checks passed
  1 = one or more hard-block conditions failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"❌ File not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text())


def _check_parity(baseline: dict, fabric: dict) -> list[str]:
    """Tier 1-3: row count, PK uniqueness, null PK. Returns list of failure strings."""
    failures: list[str] = []
    b_tables = baseline["tables"]
    f_tables = fabric["tables"]

    all_tables = sorted(set(b_tables) | set(f_tables))
    for tbl in all_tables:
        if tbl not in b_tables:
            failures.append(f"[T1] {tbl}: present in Fabric manifest but missing from baseline")
            continue
        if tbl not in f_tables:
            failures.append(f"[T1] {tbl}: in baseline but missing from Fabric manifest")
            continue

        b = b_tables[tbl]
        f = f_tables[tbl]

        # Tier 1 — row count
        if f["row_count"] != b["row_count"]:
            delta = f["row_count"] - b["row_count"]
            failures.append(
                f"[T1] {tbl}: row_count mismatch — baseline {b['row_count']}, "
                f"Fabric {f['row_count']}, delta {delta:+d}"
            )

        # Tier 2 — PK uniqueness
        if b.get("pk_distinct") is not None and f.get("pk_distinct") is not None:
            if f["pk_distinct"] != f["row_count"]:
                failures.append(
                    f"[T2] {tbl}: PK uniqueness failed — row_count {f['row_count']}, "
                    f"pk_distinct {f['pk_distinct']} (duplicates present)"
                )

        # Tier 3 — null PKs
        if b.get("pk_nulls") is not None and f.get("pk_nulls") is not None:
            if f["pk_nulls"] != 0:
                failures.append(
                    f"[T3] {tbl}: null PK count {f['pk_nulls']} > 0 — PK column has nulls"
                )

    # Tier 5 — dedup-specific counts
    dedup_expected = {
        "silver_bureau_balance": 610965,
        "silver_installments": 12861994,
    }
    for tbl, expected in dedup_expected.items():
        if tbl in f_tables and f_tables[tbl]["row_count"] != expected:
            failures.append(
                f"[T5] {tbl}: dedup row count mismatch — expected {expected}, "
                f"got {f_tables[tbl]['row_count']} "
                f"(check MONTHS_BALANCE=0 filter / (SK_ID_PREV, NUM_INSTALMENT_NUMBER) dedup)"
            )

    return failures


def _check_idempotency(run1: dict, run2: dict) -> list[str]:
    """G8 idempotency: run2 must produce identical counts as run1."""
    failures: list[str] = []
    r1 = run1["tables"]
    r2 = run2["tables"]

    for tbl in sorted(set(r1) | set(r2)):
        if tbl not in r1 or tbl not in r2:
            failures.append(f"[G8] {tbl}: table present in one run manifest but not the other")
            continue

        if r2[tbl]["row_count"] != r1[tbl]["row_count"]:
            delta = r2[tbl]["row_count"] - r1[tbl]["row_count"]
            failures.append(
                f"[G8] {tbl}: idempotency failed — run1 {r1[tbl]['row_count']}, "
                f"run2 {r2[tbl]['row_count']}, delta {delta:+d} "
                f"(positive delta = MERGE is inserting instead of upserting)"
            )

        if r1[tbl].get("pk_distinct") and r2[tbl].get("pk_distinct"):
            if r2[tbl]["pk_distinct"] != r1[tbl]["pk_distinct"]:
                failures.append(
                    f"[G8] {tbl}: PK distinct changed between runs — "
                    f"run1 {r1[tbl]['pk_distinct']}, run2 {r2[tbl]['pk_distinct']}"
                )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Fabric migration parity checker")
    parser.add_argument("manifest_a", help="Baseline manifest (parity) or run1 manifest (idempotency)")
    parser.add_argument("manifest_b", help="Fabric manifest (parity) or run2 manifest (idempotency)")
    parser.add_argument("--idempotency", action="store_true", help="Run idempotency check instead of parity")
    args = parser.parse_args()

    a = _load(args.manifest_a)
    b = _load(args.manifest_b)

    if args.idempotency:
        print(f"Running idempotency check: {args.manifest_a} vs {args.manifest_b}")
        failures = _check_idempotency(a, b)
        label = "IDEMPOTENCY CHECK (G8)"
    else:
        print(f"Running parity check: {args.manifest_a} vs {args.manifest_b}")
        failures = _check_parity(a, b)
        label = "PARITY CHECK (T1-T3, T5)"

    total_tables = len(a.get("tables", {}))
    if failures:
        print(f"\n❌ {label} FAILED — {len(failures)} violation(s) across {total_tables} tables:")
        for f in failures:
            print(f"   • {f}")
        print(
            "\n   See fabric-migration/ADR/ADR-007-validation-parity-protocol.md "
            "and governance/SIGN_OFF.md for the acceptance criteria."
        )
        return 1

    print(f"\n✅ {label} PASSED — {total_tables} tables, all conditions met.")
    print(
        "   Next: update governance/SIGN_OFF.md with the run date and evidence path, "
        "then proceed to the next gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
