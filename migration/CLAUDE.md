# Fabric Migration Framework — Directory Context

> Auto-loaded when working inside `fabric-migration/`. This folder is a **standalone governance
> framework**, built deliberately outside every glob `tests/boundary_contract.py` and
> `.claude/hooks/governance_guard.py` scan (`glue/`, `dbt_home_credit/`, `airflow/dags/`,
> `requirements.txt`, `docs/ADR/`) — so building it here does NOT trip the AWS/Snowflake
> boundary contract in the parent repo. It is meant to be lifted wholesale into a **new,
> dedicated repo** once the owner is ready to act on it (Option A from the 2026-06-30 discussion:
> evaluate/design here first, migrate the folder later, don't fight the live contract while
> designing).

## What this folder is NOT
- It is **not** a decision to migrate. No code in the parent repo (`glue/`, `dbt_home_credit/`,
  `gold/`, `airflow/`) has been touched. `tests/boundary_contract.py` / `tests/identity_contract.py`
  still pass unchanged — verify with `python ../tests/boundary_contract.py` from here if in doubt.
- It is **not** wired into `.claude/settings.json` hooks yet. `governance/boundary_contract_fabric.py`
  is a portable script meant to be wired into the *new* repo's hooks, not this one.

## Scope decided so far (2026-06-30 design session)
- **Target = fully Fabric-native ecosystem.** Every layer maps to a Microsoft Fabric service —
  Data Factory pipelines, OneLake Lakehouse, Fabric Spark Notebook, Fabric Warehouse (T-SQL),
  Purview DQ, Data Activator, Teams alerting, Power BI Direct Lake. See `ADR/ADR-006-*`.
- **One named exception, flagged not silenced:** dbt Core is third-party OSS, not a Fabric
  service. ADR-006 resolves this explicitly — read it before assuming dbt survives the migration.
- **Tech-stack choice itself is locked, not re-litigated per document.** Per owner instruction
  (2026-06-30): "semua benda wajib masuk dalam ADR ... kecuali tech stack" — the *decision* to go
  fully Fabric is settled; what's documented exhaustively is the **process** around it (gates,
  sign-off, validation, benchmarks, idempotency), not a repeated stack debate in every file.

## File index
| File | Purpose |
|---|---|
| `PROJECT_STATUS.md` | Resume-here tracker for this design effort (mirrors parent repo's pattern) |
| `ADR/ADR-005-fabric-full-migration-decision.md` | Why migrate at all, scope, veto sign-off block |
| `ADR/ADR-006-fabric-native-service-mapping.md` | Per-layer service mapping + the dbt exception, justified |
| `ADR/ADR-007-validation-parity-protocol.md` | How parity + idempotency get proven before cutover |
| `governance/SIGN_OFF.md` | Gate structure, who must approve what, before which step |
| `governance/boundary_contract_fabric.py` | Stdlib contract enforcing Fabric-only imports/config (for the new repo) |
| `benchmarks/SOURCE_BASELINE.md` | Real source-CSV row counts (pre-migration ground truth) |
| `benchmarks/SILVER_BASELINE.md` | Real Silver-layer row counts, full-scale, AWS Glue (pre-migration) |
| `benchmarks/SNOWFLAKE_STAGING_BASELINE.md` | Real Snowflake STAGING load row/PK/null counts |
| `benchmarks/INFRA_BASELINE.md` | Real Glue DPU/time/memory headroom numbers |
| `benchmarks/COST_BASELINE.md` | Real $ figures, pre-migration economics baseline |
| `validation/PARITY_TEST_PLAN.md` | Methodology: how Fabric output gets proven == these benchmarks |
| `validation/parity_check.py` | Runnable skeleton comparing two row/PK/null-count sets |
| `staging/DUAL_RUN_PLAN.md` | Parallel-run plan before any cutover/teardown of the AWS/Snowflake side |

## Read-before-touch rule (inherited from parent CLAUDE.md)
Every number in `benchmarks/` is cited `file:line` back to the parent repo's `PROJECT_STATUS.md`,
`INFRA_LIMITS_LOG.md`, or `COST_LOG.md` — not recalled from memory, not estimated. If a benchmark
file doesn't cite a line, treat it as "(unverified)" and re-check the source before trusting it.
