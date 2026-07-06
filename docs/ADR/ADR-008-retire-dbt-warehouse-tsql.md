# ADR-008: Retire dbt — Gold/Mart Layer as Fabric Warehouse T-SQL Stored Procedures

**Status:** **Accepted 2026-07-01** (Gate 0.5 signed — @data-architect + @scope-guardian + Owner;
`migration/governance/SIGN_OFF.md`). Build-phase execution authorised per the same-PR checklist
below; grain-proof conditions C3/C4/C5 due in that PR. **Supersedes ADR-006 §4** ("dbt Core retained — NAMED
EXCEPTION"). Exercises the pre-authorised "Option B" fallback in
`migration/ADR/ADR-006-fabric-native-service-mapping.md` §4.
**Date:** 2026-07-01
**Owner:** Raja Ahmad Luqman (single-dev).
**Design-gate review:** all three reviewers returned APPROVE-conditional 2026-07-01
(`MIGRATION_JOURNEY.md` J-006). This ADR incorporates their binding conditions.

## Context
ADR-006 §4 kept dbt Core (with the `dbt-fabric` adapter) as the **one named third-party
exception** in an otherwise Fabric-native stack, and flagged "Option B — full native rebuild,
no dbt" as an available fallback "if the owner's Fabric-only requirement is meant to be absolute
rather than pragmatic." The Owner has now ruled it **absolute**: zero third-party tooling. This
ADR exercises Option B.

dbt was never load-bearing for the **grain** — it was load-bearing for **enforcing** it (the
`snapshot` SCD2 engine, `unique_key`, and test-as-code). Retiring dbt therefore does not change
the star schema; it moves that enforcement from a proven engine into T-SQL that must be
hand-written and hand-proven. That is where the risk lives, and the conditions below exist to
close it.

## Decision
The Gold/mart layer is built by **Fabric Warehouse T-SQL stored procedures**, invoked by Data
Factory — no dbt, no third-party transformation framework. This stays entirely inside the
already-approved ADR-006 mapping (summary-table row 4, the "Exception (dbt)" cell now reads
"Yes / native").

Concretely, the retired `dbt_fabric/` tree maps to a new `warehouse/` T-SQL tree:
- **Staging/intermediate** (`stg_*`, `int_*`) → T-SQL views or CTAS procs.
- **Marts** (`dim_applicant` + the 3 facts) → build procs, tables land as Delta in OneLake
  automatically (read by Power BI Direct Lake, unchanged).
- **SCD2** (was `snap_applicant.sql`, `dbt snapshot`, `strategy: check`) → a 2-step
  `UPDATE`(expire) + `INSERT`(new version) T-SQL proc. **Amended 2026-07-06 (J-021,
  `migration/governance/GATE3_ARCHITECT_REVIEW_J021.md`):** the originally-primary MERGE-based
  proc is retired — Fabric Warehouse does not support the `OUTPUT` clause on any statement,
  confirmed against real Fabric Warehouse compute, making the MERGE proc's design (which needed
  `OUTPUT ... INTO @touched`) structurally impossible on this engine, not merely immature. The
  2-step fallback, which never used `OUTPUT` or a table variable, is now the **sole** SCD2
  mechanism. This is the same "if MERGE proves immature" contingency this ADR always named — the
  trigger turned out to be OUTPUT-unsupported rather than MERGE-unsupported specifically. The
  retired proc is archived at `migration/superseded/dim_applicant_scd2_merge.sql`, not deleted.
- **Tests** (dbt `assert_*`) → T-SQL assertion stored procs that `THROW`, wired as Data Factory
  FAIL-branch gates (mirrors the Silver inline-assertion pattern, ADR-006 §5).
- **Surrogate keys** (dbt `md5` macro) → `HASHBYTES('SHA2_256', ...)`.

**Grain and identity are unchanged** (re-platform, not re-grain — ADR-005): 3 fact grains stay
locked per `docs/DATA_MODEL.md`; SCD2 identity stays `applicant_id`; the tracked-column set and
the one-current invariant are preserved exactly (see C2/C4).

## Binding conditions (from @data-architect — each is a veto trigger if absent)
- **C1 — Supersede + same-PR doc fix.** This ADR cites its supersession of ADR-006 §4; the build
  PR must amend `docs/DATA_MODEL.md` (the "dbt snapshot" SCD2-mechanism sentence goes false the
  moment dbt is retired) in the same PR, naming the stored proc + the tracked-col list verbatim.
- **C2 — The 4 tracked columns are the SCD2 contract.** Change detection compares exactly
  `name_income_type, name_education_type, name_family_status, cnt_children` and nothing else —
  never `SELECT *`. Changing this set requires a new ADR.
- **C3 — NULL-safe change detection is mandatory.** T-SQL `old.col <> new.col` returns UNKNOWN
  when either side is NULL, silently missing a version cut on a NULL transition. The proc MUST use
  NULL-safe comparison, in **pure-predicate form**:
  `(a<>b) OR (a IS NULL AND b IS NOT NULL) OR (a IS NOT NULL AND b IS NULL)`. **Corrected
  2026-07-06 (J-021):** an earlier version of this condition stated the compact form
  `((a<>b) OR ((a IS NULL) <> (b IS NULL)))` — this is **invalid T-SQL on any SQL Server-family
  engine** (confirmed live against real Fabric Warehouse compute: SQL Server has no boolean type
  for an `IS NULL` predicate to evaluate to a value that `<>` can compare), not a valid-but-terse
  restatement. The predicate form above is what dbt's own generated SQL actually produces (see
  `warehouse/PROOF_C3_C4_C5.md`) and is what C3 always intended. A side-by-side proof against dbt
  output on a NULL-transition row is required, not assumed.
- **C4 — One-current invariant guarded by a THROW gate, both directions, every run.** A post-MERGE
  assertion proc `THROW`s if any `applicant_id` has **>1** current row OR **0** current rows.
  "Exactly one", not "at most one". Wired as a Data Factory FAIL branch.
- **C5 — The 2-step fallback must be atomic.** The expire+insert pair runs in one transaction with
  rollback on failure; otherwise a partial failure leaves an applicant with zero current rows and
  downstream fact→dim joins drop them silently. If Fabric Warehouse transaction semantics across
  the pair are unverified, C4's zero-current check is the mandatory backstop and blocks the run.
- **C6 — HASHBYTES surrogate key must be deterministic and collision-safe.** Pin explicit
  `CONVERT(...)` with fixed style codes for every non-string key input (no implicit `CONCAT_WS`
  coercion), and `ISNULL(col, '∅')` NULL→sentinel before hashing (`CONCAT_WS` skips NULLs →
  collisions). The surrogate key MUST NOT be the SCD2 change-detection / MERGE match key —
  identity stays `applicant_id`.
- **C7 — PII order stays upstream; Gold does no PII hashing.** DAYS_EMPLOYED/DAYS_BIRTH arrive
  pre-masked from Silver (ADR-002 order lives in the notebook). Gold T-SQL performs no re-hashing
  and no sentinel handling; any `HASHBYTES` in Gold is for surrogate keys only. Hashing a raw PII
  value in Gold is prohibited (it would reintroduce the ADR-002 out-of-order hazard in a new layer).
- **C8 — Fact grain uniqueness asserted too.** Extend the THROW-assertion pattern (C4) to a
  uniqueness check on each of the 3 fact grain keys, paying down the test-as-code safety net dbt
  provided.

## Scope conditions (from @scope-guardian)
- Removing dbt is scope **reduction**, not creep (ADR-006 §4 pre-authorised it). No new data-plane
  connector, no new vendor SDK, no AWS/Snowflake/Databricks/Airflow/Great-Expectations
  reintroduced. (Slack was later re-admitted for pipeline-failure alerting only — ADR-013,
  2026-07-06 — after Teams proved unusable; unrelated to this dbt-retirement ADR.)
- `dbt_fabric/` is retired **fully** (deleted or archived under `migration/` labelled
  "superseded"), not left half-alive next to `warehouse/`.
- **FB5 rewrite** (both `tests/boundary_contract.py` and
  `migration/governance/boundary_contract_fabric.py`): flip from a dbt-adapter allow-list to a
  **dbt-absence check** — no `profiles.yml`/`dbt_project.yml` anywhere, and `import dbt` added to
  the deny list.

## Folded improvements (Fabric better than a 1:1 port — J-005)
- Silver PII hashing uses native vectorised `F.sha2(col, 256)`, not a row-wise Python UDF.
- Surrogate key `HASHBYTES('SHA2_256', ...)` over the parent's `md5`.
- DQ assertion results also written to a Delta `dq_results` table for Data Activator trend-watching.
- PII columns classified in Purview (the parent had zero cataloguing).

## Same-PR execution checklist (build phase, after final sign-off)
1. Create `warehouse/` T-SQL tree (staging views, mart procs, SCD2 MERGE proc, DQ THROW procs).
2. Retire `dbt_fabric/` per scope condition.
3. Rewrite FB5 in both boundary-contract copies; update the printed rule list + docstrings.
4. Amend `docs/DATA_MODEL.md` (SCD2 mechanism sentence), `CLAUDE.md` (Stack table Gold row +
   FB5 line), `docs/ARCHITECTURE.md` (stack boundary).
5. Fix the pre-existing doc-reference drift + the mis-stated contract-status line flagged in J-001.
6. Regenerate `architecture/REPO_MAP.md`.

## What this is NOT
Not a re-grain. Not a redesign of the star schema. Not a change to identity, the tracked-column
set, or the PII mask order. Not a reopening of orchestration (Data Factory stays the orchestrator).
No extra marts or columns smuggled in during the rewrite.

## Consequences
**(+)** Zero third-party tooling in the transform stack — the Fabric-only goal is met literally.
**(+)** Demonstrates T-SQL SCD2 competency alongside PySpark; clean Spark-only-in-Silver boundary.
**(−)** dbt's test-as-code, lineage, and snapshot ergonomics are lost and rebuilt by hand — this is
  optimal *within* the Fabric-only constraint, not globally optimal.
**(−)** SCD2/idempotency correctness now rests on hand-written T-SQL; C3/C4/C5 are the load-bearing
  guards and will be re-checked against a side-by-side proof before gate sign-off.
**(−)** Fabric Warehouse `MERGE` maturity is unverified — the 2-step fallback exists for this.
  **Resolved 2026-07-06 (J-021):** confirmed against real Fabric Warehouse compute that `OUTPUT`
  is unsupported on any statement, which is the specific reason the MERGE-based proc cannot work
  — the 2-step fallback (`dim_applicant_scd2_fallback.sql`) is now the sole SCD2 mechanism.

## Sign-off (drafted-text review complete 2026-07-01; Owner GO pending)
- [x] **@data-architect** — 2026-07-01 APPROVE of the drafted text; C1–C8 verified line-by-line.
  Signature remains contingent on the C3 NULL-safe proof + C4 invariant gate + C5 atomicity landing
  as a side-by-side dbt comparison in the build PR.
- [x] **@scope-guardian** — 2026-07-01 APPROVE; dbt fully retired, FB5 rewrite, supersede §4 confirmed.
- [x] **Owner** — GO 2026-07-01.
