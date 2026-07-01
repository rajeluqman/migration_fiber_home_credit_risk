# Fabric Migration — Design-Phase Status

> Resume-safe checkpoint for this design effort. This is NOT the parent repo's
> `PROJECT_STATUS.md` (that one tracks the live AWS/Snowflake build and is untouched).

## ▶ RESUME HERE
**Where we are:** Design-only. Built on branch `feature/gold-dbt-snowflake-sample` (parent repo's
current branch), inside `fabric-migration/` — a folder deliberately outside every CI/hook glob,
so the AWS/Snowflake boundary contract stays green. **Nothing in `glue/`, `dbt_home_credit/`,
`gold/`, `airflow/` has been edited.**

**What exists (2026-06-30):**
- ADR-005, ADR-006, ADR-007 drafted — migration decision, service mapping, validation protocol.
- `governance/SIGN_OFF.md` + `boundary_contract_fabric.py` — gate structure + portable contract
  for the future dedicated repo.
- `benchmarks/*.md` — real pre-migration row/PK/null/cost/infra numbers, pulled from the parent
  repo's own evidence trail (`PROJECT_STATUS.md`, `INFRA_LIMITS_LOG.md`, `COST_LOG.md`,
  `docs/ADR/ADR-004-*`), every figure cited `file:line`. These are the **benchmark to beat** —
  Fabric output must match them before any cutover.
- `validation/PARITY_TEST_PLAN.md` + `parity_check.py` — methodology + runnable skeleton for
  proving Fabric output == these benchmarks, plus an idempotency re-run test.
- `staging/DUAL_RUN_PLAN.md` — parallel-run plan before touching the live AWS/Snowflake side.

**Next action:** Owner reviews this folder → decides if/when to lift it into a new dedicated repo
(per the 2026-06-30 "Option A" decision — design here, migrate folder later, don't fight the live
AWS contract while designing). A second pass (Opus) is expected to recheck/verify this framework
before it's treated as final.

**Do NOT:** touch any governed file in the parent repo (`glue/`, `dbt_home_credit/`, `gold/`,
`airflow/dags/`, `requirements.txt`) as part of this design work. Do NOT begin any real Fabric
provisioning yet — ADR-005's sign-off block is unsigned (Proposed status), and per the parent
repo's own pattern, unsigned ADRs don't authorize infra spend.

## Open items carried forward (not resolved by this design pass)
1. **dbt exception (ADR-006):** dbt Core retained as a named, flagged exception to "Fabric-only,"
   not silently kept. If the owner wants the *literal* full-native reading (no third-party tooling
   at all), ADR-006's "Option B — native rebuild" section is the fallback and needs its own
   sign-off; it is a materially bigger rebuild (no SCD2 snapshot strategy, no test-as-code layer).
2. **Purview DQ as a gating mechanism, not just a catalog:** ADR-006 resolves this by keeping the
   PASS/FAIL gate inline in the Fabric Spark Notebook (plain Python assertions, GX-equivalent
   logic without the GX library) and using Purview DQ for profiling/lineage only. Flagged as a
   deliberate scope choice, not an oversight — see ADR-006 §"Quality gating."
3. **Snowflake STAGING is incomplete today** (only 4 of 7 Silver tables loaded — see
   `benchmarks/SNOWFLAKE_STAGING_BASELINE.md` gap note). The parity benchmark for the remaining 3
   tables (`SILVER_POS_CASH`, `SILVER_CREDIT_CARD`, `SILVER_PREVIOUS_APPLICATION`) does not exist
   yet anywhere in the parent repo — flagged as a benchmark gap, not assumed equal to source counts.
4. **PROD was never populated** in the current Snowflake setup (`PROJECT_STATUS.md:898-902`) —
   this design assumes STAGING-equivalent is the Fabric parity target, matching the parent repo's
   own accepted reading. Confirm with owner before treating this as settled for Fabric too.
