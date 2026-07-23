# Cost Log — Home Credit Risk Pipeline (Fabric)

> Owner: @finops-agent. Estimate-only — never real account-linked $ figures in committed files.

## Pre-migration baseline (parent repo, real spend)
See `migration/benchmarks/COST_BASELINE.md` for the full AWS + Snowflake baseline this
migration must compare against before Gate 0 sign-off (`migration/governance/SIGN_OFF.md`
condition: "@finops-agent — Fabric CU cost estimate vs. benchmarks/COST_BASELINE.md current
spend is acceptable").

## Fabric cost surface (post-migration, not yet measured)
| Surface | Status |
|---------|--------|
| Fabric capacity unit (CU) consumption per notebook/pipeline run | Not yet measured — no Fabric workspace provisioned |
| OneLake storage growth (Bronze + Silver + Gold Delta) | Not yet measured |
| dbt-fabric Warehouse query CU usage | Not yet measured |

## Eliminated cost lines (confirmed by the migration decision, ADR-005/006)
- AWS (S3 + Glue DPU-hours) — eliminated
- Snowflake compute credits — eliminated
- Databricks Serverless SQL — eliminated

**No entries below this line yet** — this log populates once a real Fabric workspace exists
and the first notebook/pipeline run produces an actual CU consumption number.

## 2026-07-02 — J-016 first real Fabric compute attempt (@data-platform-engineer)
Capacity Trial FTL4, East Asia (`Trial-20260702T085611Z-xO09DEI98U6FiBpG5Fa_Ew`), workspace
`home-credit-risk-dev`. 6 real Fabric Notebook items created (`nb_bronze_ingest` +
5 `nb_silver_*`, see `MIGRATION_JOURNEY.md` J-016 for item IDs). 2 `RunNotebook` Spark job
instances submitted against `nb_bronze_ingest`
(`5109f7c9-daff-436f-be2e-e419b5a42ae8`, `01c2051a-7ec3-4727-b47c-53689b446b19`) — **both failed
in <2s at Livy-session creation** with `[TooManyRequestsForCapacity]` HTTP 430, `isRetriable:
false`, before any Spark executor was allocated. Exact CU consumption **not obtainable** in this
sandbox (unverified) — no Capacity Metrics API / Log Analytics access wired up, and the SP's role
(workspace Contributor) doesn't expose a capacity-metrics endpoint via `fab api`. Best-available
proxy: net Spark compute time actually run is effectively **zero** (failure was pre-execution);
item CRUD (create/import/delete of 7 Notebook items total) is metadata-only, not billed Spark CU
under Fabric's billing model. Full detail: `MIGRATION_JOURNEY.md` J-016.

## 2026-07-02 (session 2) — J-017 retry, still throttled (@data-platform-engineer)
Owner said "retry" — re-authenticated `fab` (`fab auth login` as `home-credit-fabric-sp`,
confirmed `fab auth status` → `Logged In: True`), confirmed capacity `Trial-20260702T085611Z-...`
still `Active`/`FTL4` (no resize) and all 6 Fabric Notebook items still present
(`fab api -X get workspaces/{id}/items`). Submitted 3 more `RunNotebook` jobs against
`nb_bronze_ingest` (`d56abc42-a29e-4b1b-8554-737b5e5a7f3d`) with real cooldown gaps between
attempts (~5 min after attempt 3, ~8 min after attempt 4):
- Attempt 3: job `56d19605-5d5e-4be8-ae16-39c16befa5a5`, started `23:29:23Z`, failed `23:29:24Z`
  (~1.4s) — same `[TooManyRequestsForCapacity]` HTTP 430, `isRetriable: false`.
- Attempt 4: job `516f61b6-9121-473f-88d1-5de064e8ebd6`, started `23:35:33Z`, failed `23:35:34Z`
  (~1.0s) — identical error.
- Attempt 5 (final, per task's 5-attempt cap): job `e4916913-678f-4f22-bf2d-5daa04e44d4d`,
  started `23:45:31Z`, held `NotStarted` for ~60s (longer queue than prior attempts, but still
  pre-execution), failed `23:45:32.9Z` (~1.4s) — same identical error text, `isRetriable: false`.
Combined with the 2 prior-session attempts (J-016), that is **5 total `RunNotebook` submissions
against real Fabric compute, all 5 failed identically at Livy-session creation** — zero Spark
executor time billed in any attempt (failure occurs before executor allocation). CU consumption:
not obtainable via `fab api` in this sandbox (unverified — no Capacity Metrics/Log Analytics
endpoint reachable with the current SP role); wall-clock proxy is ~5 job submissions × <2s each
of pre-execution Livy-session attempt time, i.e. effectively zero billed Spark CU. No OneLake
storage growth from this session (no writes occurred). **Status: still throttled** — this is
consistent with the FTL4 Trial SKU's low burst/concurrency ceiling, not a wiring defect; per the
task brief, stopping at 5 attempts rather than looping indefinitely. Next decision (Owner call,
not mine): wait for a longer cooldown window (e.g. hours, not minutes) or size up off the Trial
SKU. Full detail: `MIGRATION_JOURNEY.md` J-017.

## 2026-07-05 — J-018 CU baseline correction + attempt 6, still throttled (@senior-data-engineer)
**CU baseline correction (independent of retry work):** earlier sessions misread the `FTL4` SKU
string as "4 CU" — corrected via real citation
(`https://learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity`, accessed 2026-07-03):
Fabric **Trial capacity = 64 CU, F64-equivalent, 8 Power BI v-cores**. `FTL4` is just the Trial
SKU's internal identifier, unrelated to the CU-table value. Full detail + scope caveat (CU is
compute-power, not a documented concurrency limit) in `migration/benchmarks/INFRA_BASELINE.md`.
**Retry attempt 6:** re-authenticated `fab` (session token had expired since J-017, 3 days
prior). Confirmed capacity unchanged (`Active`/`FTL4`) and all 6 workspace Notebook items
unchanged before retrying. Submitted 1 more `RunNotebook` job against `nb_bronze_ingest`
(job `b0404f35-19ac-4783-85bb-0afbc676d2f1`, submitted 2026-07-05T09:06:04Z) — **failed
identically** at Livy-session creation (2.2s), same `[TooManyRequestsForCapacity]` HTTP 430,
`isRetriable:false`, even after a ~3-day cross-session gap. Waited a further ~20 min and
submitted **attempt 7** (job `e94a51ab-7d3f-4779-bfe7-692d945aae79`, submitted
2026-07-05T09:26:43Z) — also **failed identically** (1.9s, same error). Combined with the 5
prior attempts (J-016/J-017): **7/7 total `RunNotebook` submissions failed**, all pre-execution,
so real Spark CU billed remains effectively zero across all 7 (still unverified against a real
Capacity Metrics API — `admin/capacities/{id}`, `admin/capacities/{id}/usage`,
`capacities/{id}/metrics` all probed live this session, all `404`). Stopped at 7 (within the
8-new-attempt session cap) — the pattern across gaps from 4 minutes to ~3 days is now
unambiguous enough that further short-gap retries are unlikely to add information; see
methodology note in `migration/benchmarks/INFRA_BASELINE.md`. Full detail:
`MIGRATION_JOURNEY.md` J-018.

## 2026-07-05 (session 3) — J-019 root cause fixed, Bronze materializes for real (@senior-data-engineer)
**Root cause (Owner-sourced lead, confirmed against real API):** the workspace's auto-provisioned
"Starter Pool" (`GET workspaces/{id}/spark/pools`) was `nodeSize: Medium`, autoscale 1-10 nodes —
oversized for the 64-CU FTL4 Trial capacity, causing admission-time rejection (HTTP 430) before
any Spark executor started, on all 7 prior attempts (J-016/017/018).
**Fix:** created a custom **Small, autoscale-disabled (1 fixed node)** Spark pool
(`POST workspaces/{id}/spark/pools` → `201`, `id: 18c24a87-e291-477c-b74c-5dc2837d6595`) and set
it as the workspace default pool (`PATCH workspaces/{id}/spark/settings` → `200`, confirmed via
follow-up `GET`).
**Retry attempt 8** (one attempt, per task cap) against `nb_bronze_ingest` — job
`c91bcee4-f5d3-4824-810e-0ef2a091a276`, submitted `09:29:52Z`, ran for real (`NotStarted` →
`InProgress` → `Completed`, `endTimeUtc 09:39:09Z`) — **~9.5 minutes of real Spark execution, the
first non-zero real Spark CU spend in this project's history.** 8/8 total attempts across all
sessions; first success.
**Verification cost:** a throwaway `nb_bronze_verify` Notebook item was created to get real row
counts (no ODBC/`pyodbc` available in-sandbox for the SQL Analytics Endpoint, `fab table` exposes
schema but not counts) — ran via `fab job run` sync, ~4.6 minutes of Spark time
(`09:58:21Z`→`10:02:57Z`), output read via `fab cp`, then the item + its `Files/verify_counts`
output were deleted (`fab rm -f`) to leave no untracked workspace artifacts.
**Result:** all 7 `bronze_*` Delta tables materialized with exact row-count parity to source CSVs
(307,511 / 1,716,428 / 27,299,925 / 1,670,214 / 13,605,401 / 10,001,358 / 3,840,312 — 7/7 match)
and all required tag columns (`ingestion_ts`/`source_file`/`batch_id`/`env`) present. Real Spark
CU billed: still unverified against a real Capacity Metrics API in this sandbox (same limitation
as J-016/017/018) — wall-clock (~14.1 minutes total real Spark time across both jobs) logged
instead, explicitly tagged (unverified) for CU. **Status: Gate 2 condition G1 (row-count parity)
PASSED for real** — first real data in the Fabric workspace. Full detail: `MIGRATION_JOURNEY.md`
J-019.

## 2026-07-05 (session 4) — J-020 all 5 Silver notebooks run for real, Gate 2 G2-G5/G8 PASSED (@senior-data-engineer)
Guard re-verified before submitting: `GET workspaces/{id}/spark/settings` → `defaultPool.name:
"SmallFixedPool"` (no drift from ADR-012). All 5 Silver `RunNotebook` jobs submitted sequentially
against the `SmallFixedPool` (1 fixed Small node), each polled to a terminal `Completed` status
(not assumed from `202`):
| Notebook | Job ID | Start (UTC) | End (UTC) | Wall-clock |
|---|---|---|---|---|
| nb_silver_application | `19769637-139c-46d7-b44a-b89a799b6698` | 15:06:37 | 15:10:56 | ~4.3 min |
| nb_silver_bureau | `37aae960-872f-48a0-8f1e-b3eaa7a803c2` | 15:11:34 | 15:15:47 | ~4.2 min |
| nb_silver_installments | `a8f9f4ff-3a61-495d-9a3f-9df729a8ced8` | 15:16:36 | 15:21:27 | ~4.9 min |
| nb_silver_previous_application | `6e6b1be9-77f4-4642-b010-a17e5a240b7c` | 15:22:05 | 15:26:44 | ~4.6 min |
| nb_silver_balance_tables | `4ff37426-2416-4cd1-82ee-0d922ed26144` | 15:27:11 | 15:33:35 | ~6.4 min |
**Total: ~24.4 minutes real Spark execution across all 5 Silver notebooks — no throttle, no OOM,
no failure at any point, including the 27M-row `bureau_balance` table** (the infra-risk case
flagged in ADR-012/`migration/benchmarks/INFRA_BASELINE.md` — the single fixed Small node held up
at full scale).
**Verification cost:** a throwaway `nb_silver_verify_gate2` Notebook item (reads all 7 `silver_*` +
2 `bronze_*` tables for G2/G3/G4/G5 evidence) ran ~7 min (`15:36:59Z`→`15:43:58Z`); a second
throwaway `nb_silver_verify_g8` (post-idempotency-rerun count check) ran ~4.4 min
(`15:52:20Z`→`15:56:44Z`). The G8 idempotency re-run itself (`nb_silver_application` re-submitted)
ran ~5 min (`15:46:18Z`→`15:51:19Z`). Both verify items and their `Files/verify_*` outputs were
deleted after reading results (`fab api -X delete` + `fab rm -f`) — workspace left with only the
original 6 items (Bronze + 5 Silver), confirmed via a follow-up `GET workspaces/{id}/items`.
**Session total: ~40.8 minutes of real Spark execution** (24.4 Silver + 7 + 5 + 4.4 verify/G8).
Real Spark CU billed: still unverified against a Capacity Metrics API in this sandbox (same
limitation as J-016...J-019) — wall-clock logged instead, tagged (unverified) for CU. **Status:
Gate 2 conditions G2 (PK uniqueness), G3 (null-PK=0), G4 (PII mask), G5 (dedup counts), G8
(idempotency) all PASSED for real** against actual Fabric compute. Full detail:
`MIGRATION_JOURNEY.md` J-020.

## 2026-07-05 (session 5) — J-021 Gold Trial Warehouse: real T-SQL execution surface stood up,
## blocked mid-deploy on 3 real Fabric Warehouse dialect/syntax findings (@senior-data-engineer)
Created the Fabric Trial Warehouse item (`home_credit_warehouse`, id
`83f15106-6972-4cbd-8984-1eebdb07d733`) — none existed before this session (ADR-010 D3 pre-step).
**Tooling gap solved for real** (same category as J-019's Livy-surface gap): `fab` CLI has no
query-execution surface for `.Warehouse` (`fab desc .warehouse` — only
`acl/cd/exists/get/ls/mkdir/rm/set/table schema`, no `job`/`query`). Installed Microsoft
`msodbcsql18` (apt, `packages.microsoft.com`) + `pyodbc`, authenticated via `az account
get-access-token --resource https://database.windows.net/` (same SP already used for `fab`) and
`SQL_COPT_SS_ACCESS_TOKEN` AAD-token connection attribute — confirmed live against
`frwtimofqvjenjz3faaeyuzpzy-*.datawarehouse.fabric.microsoft.com`: `SELECT @@VERSION` returned
`Microsoft Azure SQL Data Warehouse (RTM) - 12.0.2000.8`. (A pure-python TDS client, `python-tds`,
was tried first to avoid the proprietary driver — failed: Fabric's SQL endpoint requires the
newer strict/TLS-first TDS handshake that `python-tds` 1.17.1 doesn't implement.) Confirmed
cross-database query from the Warehouse to the Lakehouse SQL endpoint works (`SELECT COUNT(*) FROM
home_credit_lakehouse.dbo.silver_application` → `307511`, exact match to Bronze/Silver row count)
— both items share one logical SQL endpoint server, so `database.schema.table` 3-part names
resolve across them with no extra wiring. Created a `silver` schema + 3 shim views in the
Warehouse (`silver.silver_application`, `silver.silver_bureau`, `silver.silver_installments` →
`home_credit_lakehouse.dbo.silver_installments_payments`) so `warehouse/staging/stg_application.sql`
etc. resolve unmodified — this is wiring, not a logic change.
**Deployed clean:** all 3 staging/intermediate views, all 4 DQ `THROW` assertion procs, all 4
mart `usp_build_*` wrapper procs (the CREATE TABLE guards inside 4 of the mart `.sql` files did
NOT deploy — see below).
**3 real findings against live Fabric Warehouse compute, none previously verified (all
tagged "(unverified)" in ADR-008/PROOF_C3_C4_C5.md until this session):**
1. **`BINARY(32)` is not a supported column type** in Fabric Warehouse (error 24574) — blocks
   `CREATE TABLE dbo.dim_applicant` / `fact_bureau_credit` / `fact_installment_payment` /
   `fact_loan_application`, all 4 of which type the HASHBYTES surrogate key (ADR-008 C6) as
   `BINARY(32)`. No Gold table exists yet as a result.
2. **Table variables are not supported** (`DECLARE @t TABLE (...)` → error 15871, "TYPE 'table' is
   not supported") — blocks `usp_scd2_merge_dim_applicant` (`DECLARE @touched TABLE` in
   `warehouse/scd2/dim_applicant_scd2_merge.sql:30`), independent of finding 3 below.
3. **The C3 NULL-safe pattern itself is invalid T-SQL, not just a Fabric gap** — `(a IS NULL) <>
   (b IS NULL)` treats two `IS NULL` predicates as comparable values via `<>`, which is not valid
   syntax in any SQL Server-family engine (bisected down to a minimal repro:
   `SELECT 1 WHERE (('a' <> 'b' OR (('a' IS NULL) <> ('b' IS NULL))))` fails identically —
   "Incorrect syntax near '<'.", error 102). This affects both
   `warehouse/scd2/dim_applicant_scd2_merge.sql` and `dim_applicant_scd2_fallback.sql` identically
   across all 4 tracked columns — neither SCD2 proc compiled. The dbt-generated SQL quoted as the
   "same logically identical" comparison in `warehouse/PROOF_C3_C4_C5.md:52-60` actually combines
   `is null`/`not (... is null)` as full boolean predicates joined with `and`/`or`/`not` — never as
   sub-expression values compared with `<>`. ADR-008 C3's "compact form" is not equivalent to what
   it claims to reproduce.
**Session wall-clock:** ~25 min real T-SQL DDL/DML against the Trial Warehouse (all sample-scale,
metadata-only DDL + one 307,511-row cross-db COUNT — negligible CU by the ADR-010 D3 design
intent). Real CU still unverified against a metering API in this sandbox (same limitation carried
since J-016). **Stopped per this session's explicit governance instruction** ("Do NOT modify
grain/SCD2 logic. If warehouse/ code conflicts with ADR-001/008, STOP and surface it to
@data-architect") — findings 2 and 3 are SCD2-logic-level bugs, not infra wiring, so fixing them
requires @data-architect sign-off before any `warehouse/scd2/*.sql` edit. Full detail:
`MIGRATION_JOURNEY.md` J-021.

## 2026-07-06 (session 6) — J-022 Gate 3 CLOSED: @data-architect APPROVE-CONDITIONAL, all 6
## conditions applied, Gold build run for real against full Silver data (@senior-data-engineer)
@data-architect reviewed the 6 J-021 findings + browser-validated fixes (Owner independently
reproduced findings 4/5/3 live in the Fabric browser SQL editor, confirming no drift from my
pyodbc session) — verdict **APPROVE-CONDITIONAL**, written to
`migration/governance/GATE3_ARCHITECT_REVIEW_J021.md`. No veto triggered (no re-grain, no
identity change, no tracked-column-set change). 6 blocking conditions applied this session:
1. Type/hash fixes applied uniformly (VARBINARY(32)/VARCHAR/DATETIME2(6)/explicit
   `CONVERT(VARBINARY(32), HASHBYTES(...))`) across all 4 mart `CREATE TABLE`s + the fallback
   proc's hash site.
2. `usp_build_dim_applicant` repointed to `usp_scd2_fallback_dim_applicant`.
3. `dim_applicant_scd2_merge.sql` retired, archived at
   `migration/superseded/dim_applicant_scd2_merge.sql` (not deleted — historical record).
4. Same-PR doc amendments: `docs/DATA_MODEL.md:36-42`, `docs/ADR/ADR-008-*.md` (SCD2 mechanism +
   consequences sections), `warehouse/README.md`.
5. Corrected the invalid "compact form" C3 text in ADR-008 and `warehouse/PROOF_C3_C4_C5.md` to
   the pure-predicate form.
6. Proved the one-current invariant + NULL-transition + C5 rollback path on real data (below).
All 4 static contracts re-verified green after the doc/test edits (`identity_contract.py` updated
to check the sole surviving SCD2 proc; 2 stale doc-reference-contract violations in
`docs/OPS_RUNBOOK.md`/`docs/PIPELINE_SPEC.md` fixed).

**Real Gold build run against full Silver data (first time, real Fabric Warehouse compute):**
- `usp_build_dim_applicant` (→ `usp_scd2_fallback_dim_applicant`): ~6.2s wall-clock, 307,511 rows
  inserted (all brand-new — first-ever load into an empty table), 307,511 distinct `applicant_id`,
  307,511 `is_current=1` rows, **zero** one-current violations. **G7 confirmed at full scale.**
- `usp_build_fact_loan_application`: ~4.1s, 307,511 rows = 307,511 distinct `SK_ID_CURR`.
- `usp_build_fact_bureau_credit`: ~6.9s, 1,716,428 rows = 1,716,428 distinct `SK_ID_BUREAU`
  (exact match to the bureau.csv baseline).
- `usp_build_fact_installment_payment`: ~39.7s, 12,861,994 rows = 12,861,994 distinct
  `(SK_ID_PREV, NUM_INSTALMENT_NUMBER)` (exact match to the deduped Silver count from J-020).
  **G6 confirmed** — all 3 fact grains unique, row counts exact vs. Silver source.
**Total Gold build wall-clock: ~56.9 seconds** against the full real dataset (58.4M-row source
scale, though the Warehouse tables themselves top out at the 12.9M-row installment fact) —
negligible CU by ADR-010 D3's design intent (sample/small-scale dev on the Trial capacity).

**Condition 6 evidence (all via scratch-table copies of real data — the sandbox's safety
classifier blocked a direct UPDATE against the real `dim_applicant` table mid-session, correctly
flagging it as an unauthorized write to shared production state; pivoted to copying real
applicant 100002's actual row into a `_scratch_test` table instead, same evidentiary value, zero
risk to real data):**
- NULL-transition: copied real applicant 100002 (`cnt_children=0`) into scratch tables, corrupted
  only the scratch copy's current-row `cnt_children` to `NULL`, ran a scratch-copy of the fixed
  SCD2 logic — result: 2 rows, expired (`cnt_children=NULL`) + new current (`cnt_children=0`,
  matching the real source value). Confirms the C3 predicate-form fix on real-data values, not
  only the earlier synthetic Stage-C test.
- C5 rollback path: same scratch setup, ran a proc identical to the fallback except for a
  deliberate `RAISERROR` inserted between Step 1 (`UPDATE`) and Step 2 (`INSERT`) — confirmed the
  `UPDATE` fired inside the transaction (matched the NULL-transition condition) and then
  `ROLLBACK` fully restored the pre-UPDATE state (`is_current=1` unchanged) after the forced
  failure, rather than leaving the applicant with zero current rows. This was the one piece
  `PROOF_C3_C4_C5.md` had flagged as untestable before a real Warehouse existed — now closed.
- C4 both-direction THROW: scratch copies of `dim_applicant`/`int_applicant_attributes` —
  confirmed `usp_assert_dim_applicant_one_current`'s logic throws error 51001 on an injected
  >1-current row and error 51002 on an injected 0-current row.
- C8 fact-grain THROW: scratch copy of `fact_loan_application` with an injected duplicate
  `SK_ID_CURR` — confirmed the grain-assertion logic throws error 51012.
All scratch objects dropped after each test; final sanity check confirmed real production tables
unchanged throughout (`dim_applicant`/`fact_*` row counts identical before and after all scratch
testing).

**Session wall-clock:** ~57s real Gold build execution + incidental scratch-table DDL/DML
(negligible CU, all sample-scale). Real CU still unverified against a metering API in this
sandbox (unchanged limitation since J-016). **Gate 3 (G6, G7) — both conditions now PASSED
against real Fabric Warehouse compute.** Full detail: `MIGRATION_JOURNEY.md` J-022.

## 2026-07-06 (session 7) — Gate 4: real Data Factory pipelines, real end-to-end run
- ~24 min real Fabric Spark compute: first end-to-end attempt (`bronze_ingestion` job
  `6b4d41d0...`), failed partway on 2 of 4 parallel-fanout Silver notebooks
  ([TooManyRequestsForCapacity] concurrency limit on SmallFixedPool's single fixed node) —
  `nb_bronze_ingest` + `nb_silver_application` + 2 of 4 fanout notebooks did complete for real
  before the failure.
- ~37 min real Fabric Spark + Warehouse compute: second attempt after switching the DAG to serial
  (`silver_transforms` job `c813bd3a...`, 06:08:21-06:45:10 UTC) — all 5 Silver notebooks +
  `gold_warehouse` (4 Script-activity EXECs) completed successfully.
- Incidental: ~6 throwaway `.DataPipeline` items created/schema-validated/deleted during API
  discovery (zz_test_pipeline, zz_test_pipeline2, zz_target_pipeline, zz_test_script,
  zz_test_invoke) — negligible cost, no compute run except zz_test_script's single `SELECT 1`
  and zz_test_invoke (schema-validated only, not executed).
- 2 Connection objects created (Warehouse SQL, FabricDataPipelines) — no compute cost, metadata
  only.
- Real CU still unverified against a metering API — `admin/capacities` now `403
  InsufficientScopes` (endpoint exists, SP lacks the Fabric Admin API permission grant), clearer
  diagnosis than J-016's `404` but still unresolved. See MIGRATION_JOURNEY.md J-023, G11.

## 2026-07-06 (session 7 cont.) — G9 Slack alert wiring + fire-tests
- 1 local urllib POST to Slack webhook (connectivity test) — no Fabric compute.
- 2 throwaway pipeline runs (Script `THROW` → WebActivity→Slack; and InvokePipeline[Failed]→
  WebActivity→Slack) — seconds each, negligible CU, both deleted after.
- 1 Fabric `WebForPipeline` connection + reused the existing Warehouse/InvokePipeline connections
  — metadata only, no compute cost.
- Production alert wired into `silver_transforms` (`notify_slack_gold_failure`) — no run cost until
  a real Gold failure triggers it. See MIGRATION_JOURNEY.md J-025.
