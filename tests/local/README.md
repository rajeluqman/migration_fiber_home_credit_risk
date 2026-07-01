# `tests/local/` — Local-First Silver Dev/Test Harness (ADR-010, FB8)

This directory is the **only** location outside `notebooks/` where standalone PySpark is
permitted (boundary rule **FB8**, `docs/ADR/ADR-010-local-first-dev-and-fabric-trial.md`).

## Rules (enforced by `tests/boundary_contract.py`)
- **Every file here must cite `ADR-010`** — otherwise the FB6 Spark ban applies and CI fails.
- Files are **dev/test-only**: never referenced by a Data Factory pipeline (`pipelines/*.json`),
  never deployed to Fabric.
- The FB1–FB4 SDK bans still apply (no AWS / Snowflake / Airflow / Slack SDK).

## Purpose
Prove Silver transform logic (PII-mask order DI-002, XNA→NULL, dedup keys, MERGE upsert
branches, and the ADR-007 idempotency re-run) on a **sample** (50k–100k rows) using local
PySpark 3.5 + `delta-spark` — the same engine as Fabric Runtime 1.3 — **before** any Fabric
capacity is provisioned or CU spent. This is ADR-007 **Tier 0** (local pre-parity), a
precondition for, not a substitute for, the full-scale Tiers 1–5 on the real Fabric run.
