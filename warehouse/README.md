# Fabric Warehouse T-SQL (Gold layer)

Replaces the retired `dbt_fabric/` tree (ADR-008 — retire dbt, Option B). No dbt, no
third-party transformation framework; Data Factory invokes these stored procs directly.

| Folder | Was (dbt) | Now |
|---|---|---|
| `staging/` | `models/staging/*.sql` (views) | `CREATE OR ALTER VIEW` |
| `intermediate/` | `models/intermediate/*.sql` (views) | `CREATE OR ALTER VIEW` |
| `mart/` | `models/mart/*.sql` (tables) | table DDL + `usp_build_*` procs |
| `scd2/` | `snapshots/snap_applicant.sql` (`dbt snapshot`) | `usp_scd2_merge_dim_applicant` (primary, MERGE) + `usp_scd2_fallback_dim_applicant` (2-step atomic fallback, C5) |
| `dq/` | dbt `assert_*` tests | `THROW`-based assertion procs, wired as Data Factory FAIL-branch gates |

Binding conditions C1–C8 and the grain-proof requirement live in
`docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md`. Side-by-side proof of the NULL-safe change
detection (C3), the one-current THROW gate (C4), and fallback atomicity (C5) is in
`warehouse/PROOF_C3_C4_C5.md`.
