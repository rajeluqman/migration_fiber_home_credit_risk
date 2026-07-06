# Project Status — Home Credit Risk Pipeline (Fabric)

## ▶ RESUME HERE
**Where we are (2026-07-06, `gate-0.5-option-b-adr-008-009`), latest — GATE 4 OPEN, G12 CLOSED,
real end-to-end Data Factory pipeline chain built and run (J-023).**
J-023: Built the 3 real Fabric Data Factory pipelines (`pipelines/` was still `_stub: true`
placeholders) — `bronze_ingestion` → `silver_transforms` → `gold_warehouse`, chained via
`InvokePipeline`. Hit and resolved 2 real platform gaps: (1) SP connection-creation `401` — root
cause was the Fabric-login account (`fabricpipelines@...`) had only capacity-admin, not
tenant-admin, role; Owner assigned Global Admin + enabled 2 tenant settings (SP can
create connections; SP can call Fabric public APIs), unblocking `Script`/`InvokePipeline`
activities. (2) First full run failed on `[TooManyRequestsForCapacity]` — the parallel 4-notebook
Silver fan-out (per `docs/PIPELINE_SPEC.md` §5.2) exceeded `SmallFixedPool`'s single-node
concurrency; Owner-approved fix: serial DAG instead. **Second full run succeeded end-to-end**
(~37 min) — Gold row counts (307,511 / 307,511 / 1,716,428 / 12,861,994) verified via live query
matching the J-022 baseline exactly (idempotent rebuild, no drift). **G12 CLOSED** (CI run
28768336125, PR #2, after fixing a stale `REPO_MAP.md`). **G9 parked** (Teams: both classic
Connectors and the Workflows app are unavailable in this tenant — real M365 licence-tier gap,
same class as J-011). **G10 and G11 remain Owner-action items** (Power BI Direct Lake report
needs Owner to build+screenshot in browser; CU cost needs either an Entra Admin-API permission
grant or the Owner checking the Fabric Capacity Metrics app). Full detail: `MIGRATION_JOURNEY.md`
J-023, cost in `COST_LOG.md` 2026-07-06 (session 7).

**Previous checkpoint (J-022): GATE 3 CLOSED (G6, G7 both PASSED against real Fabric Warehouse
compute, @data-architect APPROVE-CONDITIONAL).**
J-022: @data-architect reviewed the 6 real Fabric Warehouse findings from J-021 (below) plus the
browser-validated fix and returned **APPROVE-CONDITIONAL**
(`migration/governance/GATE3_ARCHITECT_REVIEW_J021.md`) — no veto (no re-grain, no identity
change, tracked-column set unchanged), 6 blocking conditions. All 6 applied this session: type
fixes (`VARBINARY(32)`/`VARCHAR`/`DATETIME2(6)`/explicit `CONVERT(VARBINARY(32),
HASHBYTES(...))`) applied uniformly across all 4 mart tables + the fallback proc;
`usp_build_dim_applicant` repointed to `usp_scd2_fallback_dim_applicant`; the MERGE-based proc
retired (deleted from `warehouse/`, archived at `migration/superseded/dim_applicant_scd2_merge.sql`
— it cannot work on Fabric Warehouse at all, since `OUTPUT` is unsupported on any statement, not
merely immature); same-PR doc amendments to `docs/DATA_MODEL.md`, `docs/ADR/ADR-008-*.md`,
`warehouse/README.md`; the invalid C3 "compact form" corrected to predicate form in ADR-008 and
`warehouse/PROOF_C3_C4_C5.md`. All 4 static contracts re-verified green (`identity_contract.py`
updated to check only the surviving SCD2 proc; 2 stale doc-reference-contract violations fixed).
**Real Gold build then run against the full real Silver dataset for the first time:**
`usp_build_dim_applicant` → 307,511 rows, 307,511 distinct `applicant_id`, 307,511
`is_current=1`, 0 one-current violations (**G7 confirmed at full scale**); all 3 fact procs →
307,511 / 1,716,428 / 12,861,994 rows each exactly matching grain-key distinct-count and Silver
source count (**G6 confirmed**). Condition 6 (prove the invariants on real data, not just
synthetic) was satisfied via scratch-table copies of real applicant 100002's actual data — the
sandbox's safety classifier correctly blocked a direct UPDATE against the real `dim_applicant`
table mid-session (unauthorized write to shared production state), so the NULL-transition, C5
rollback-path (deliberate forced failure — confirmed `ROLLBACK` genuinely restores pre-UPDATE
state), C4 both-direction THROW, and C8 fact-grain THROW were all proven via scratch copies
instead, with real production tables confirmed untouched throughout. `migration/governance/
SIGN_OFF.md` Gate 3 table updated to ☑ CLOSED. Full detail: `MIGRATION_JOURNEY.md` J-022, cost in
`COST_LOG.md` 2026-07-06 (session 6).
**Next action (superseded by J-023 above):** ~~Gate 4 (End-to-End Validation + Alerting) — Data
Factory pipeline wiring...~~ — done in J-023. **Actual next action now:** G10 (Owner builds a
Power BI Direct Lake report over the Gold tables in browser, screenshots it), G11 (either grant
the SP's Entra app registration the Fabric Admin API permission, or Owner checks the Fabric
Capacity Metrics app), G9 stays parked pending a fuller M365 licence. Once G10/G11 close (or are
explicitly accepted as parked like G9), Gate 4 can be marked CLOSED and Gate 5 (AWS/Snowflake
teardown authorisation) can be considered.

**Previous checkpoint (J-021): Gate 3 kickoff, BLOCKED on 3 real Fabric Warehouse findings,
Owner/@data-architect decision needed.**
Fabric Trial Warehouse (`home_credit_warehouse`, id `83f15106-6972-4cbd-8984-1eebdb07d733`)
created for the first time this session (ADR-010 D3 pre-step — none existed before). Solved the
T-SQL execution-surface tooling gap (`fab` CLI has no query verb for `.Warehouse`) via
`msodbcsql18` + `pyodbc` + AAD access-token auth (`SQL_COPT_SS_ACCESS_TOKEN`) — first real T-SQL
ever run against Fabric Warehouse compute in this project, confirmed via `SELECT @@VERSION`.
Confirmed cross-database query from Warehouse → Lakehouse SQL endpoint works with plain 3-part
names (same logical server). Created a `silver`-schema shim (3 views aliasing the real
Lakehouse `dbo.silver_*` tables) so `warehouse/staging|intermediate|mart` SQL resolves unmodified
— wiring only, no logic change. Deployed clean: 3 staging/intermediate views, 4 DQ THROW procs, 4
mart wrapper procs. **Blocked before any Gold table or SCD2 proc could run**, on 3 real findings
against live Fabric Warehouse compute (none previously testable — no Warehouse existed until
now): (1) `BINARY(32)` unsupported column type (error 24574) blocks all 4 mart `CREATE TABLE`
statements (ADR-008 C6 surrogate key); (2) table variables unsupported (error 15871) blocks
`usp_scd2_merge_dim_applicant`'s `DECLARE @touched TABLE`; (3) the ADR-008 C3 "NULL-safe" compact
form `(a IS NULL) <> (b IS NULL)` is invalid T-SQL on any SQL Server-family engine (not just a
Fabric gap) — blocks both SCD2 procs identically across all 4 tracked columns, and the
`warehouse/PROOF_C3_C4_C5.md` claim that this is "logically identical" to dbt's generated SQL does
not hold (dbt's version combines `IS NULL` as predicates joined with AND/OR/NOT, never as values
compared with `<>`). **Stopped per this session's explicit governance instruction** — findings 2/3
are SCD2-logic edits requiring @data-architect sign-off, not infra wiring. Gate 3 (G6, G7) stays
☐ Pending. No `warehouse/*.sql` file was modified this session. Full detail: `MIGRATION_JOURNEY.md`
J-021, cost in `COST_LOG.md` 2026-07-05 (session 5).
**Next action:** Owner + @data-architect review findings 1-3 above and decide the fix for each
(likely `VARBINARY(32)` for #1; a Fabric-supported substitute for the table-variable OUTPUT
pattern for #2; a rewrite of the C3 expression to predicate-form `AND`/`OR`/`NOT` for #3) before
any further Gold T-SQL is run.

**Previous checkpoint (J-020): GATE 2 CLOSED (Owner GO).**
J-020: all 5 Silver notebooks ran for real against the `SmallFixedPool` (guard re-verified no
drift first) — **~24.4 minutes total real Spark execution, no throttle, no OOM**, including
`nb_silver_balance_tables` (the 27M-row `bureau_balance` infra-risk case ADR-012 flagged as
unproven — the single fixed Small node held up fine). Before spending CU, diffed all 5 deployed
Fabric Notebook items against the current (uncommitted) `notebooks/nb_silver_*.py` local files via
`getDefinition` — confirmed byte-identical, no redeploy needed. Built a throwaway
`nb_silver_verify_gate2` Notebook item for real evidence (not assumed from job status): **G2 (PK
uniqueness, all 7 tables) PASS, G3 (null-PK=0, all 7 tables) PASS, G4 (silver_application PII mask,
DI-002/ADR-002 order) PASS** (55,374 sentinel/XNA rows correctly nulled before hashing, zero leaked
as raw-sentinel hash, 5/5 sha256 samples match), **G5 (dedup match, bureau_balance + installments)
PASS** (bureau_balance had zero raw dupes; installments genuinely collapsed 743,407 duplicate rows,
13,605,401→12,861,994 — proves dedup logic actually works, not a no-op). Then re-ran
`nb_silver_application` against byte-identical Bronze data and verified via a second throwaway
notebook: **G8 (idempotency) PASS** — row count unchanged at 307,511, `no_dup_rows: true`. Both
verify items + their `Files/verify_*` outputs deleted after reading results (workspace confirmed
back to the original 6 items). Full detail: `MIGRATION_JOURNEY.md` J-020, cost in `COST_LOG.md`
2026-07-05 (session 4).
**Owner approved 2026-07-05 ("ok approved")** — recorded in `migration/governance/SIGN_OFF.md` as
Owner GO on Gate 2 (G1-G5, G8), with the G4 @data-quality-steward standalone persona review waived
Owner-direct, per the same waiver precedent already used for ADR-011/ADR-012. **Gate 2 outcome:
☑ CLOSED.**
**Next action:** Gold T-SQL dev on the Trial Warehouse (ADR-010 D3) — author/run the
`warehouse/{staging,intermediate,mart,scd2,dq}` T-SQL objects directly against the real Fabric
Trial Warehouse (not a local SQL engine — dialect drift would break zero-rewrite, per ADR-010).
Read `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` (C1-C8) and `warehouse/PROOF_C3_C4_C5.md`
before touching any `warehouse/` file — @data-architect holds veto on grain/SCD2/model changes
there. `dim_applicant` SCD2 MERGE proc is the highest-risk piece (ADR-008 C2/C3, NULL-safe
change-detection). No Fabric Warehouse T-SQL proc has executed against real Fabric compute yet —
this will be the first (Warehouse MERGE maturity currently unverified per
`PROJECT_STATUS.md` "What has NOT happened").

**Previous checkpoint (J-019): BRONZE IS REAL, Gate 2 G1 PASSED.** Owner-sourced fix from a Fabric Community thread (identical HTTP 430 symptom)
confirmed against the real API: the workspace's default "Starter Pool" was `Medium`/autoscale
1-10 nodes — oversized for the 64-CU FTL4 Trial capacity, causing every one of the prior 7
attempts to be rejected at Livy-session admission before any Spark executor started. Created a
custom **Small, autoscale-disabled (1 fixed node)** Spark pool (`POST
workspaces/{id}/spark/pools` → `201`, `id: 18c24a87-e291-477c-b74c-5dc2837d6595`) and set it as
the workspace default (`PATCH workspaces/{id}/spark/settings` → `200`, confirmed via follow-up
`GET`). **Retry attempt 8** against `nb_bronze_ingest` (job
`c91bcee4-f5d3-4824-810e-0ef2a091a276`) ran for real — `NotStarted` → `InProgress` →
`Completed`, ~9.5 minutes of actual Spark execution, no throttle error at any point. **First
success in 8 total attempts.** Verified Bronze materialization with real evidence (not assumed
from job status): all 7 `bronze_*` Delta tables present in the Lakehouse (`fab ls Tables`), all
required tag columns confirmed (`fab table schema` — `ingestion_ts`/`source_file`/`batch_id`/
`env`), and **exact row-count parity to source CSVs on all 7 tables** (307,511 / 1,716,428 /
27,299,925 / 1,670,214 / 13,605,401 / 10,001,358 / 3,840,312 — verified via a throwaway
`nb_bronze_verify` Notebook item run through `fab job run`, output read via `fab cp`, then
deleted along with its `Files/verify_counts` output to leave the workspace clean). **Gate 2
condition G1 (row-count parity) is now PASSED against real Fabric compute** — the first real
data in this project's Fabric workspace. Full detail: `MIGRATION_JOURNEY.md` J-019.
**Next action:** run the 5 Silver notebooks against this same `SmallFixedPool` default (now
proven to admit real Spark sessions on the Trial SKU) as a separate follow-up task — do not
revert to the Starter Pool (this is now a binding constraint, `docs/ADR/ADR-012-fabric-trial-spark-pool-sizing.md`:
verify `spark/settings` default == `SmallFixedPool` before submitting any job). After Silver: idempotency re-run (ADR-007 G8, re-run a Silver
notebook and confirm no duplicate rows via the native Delta `MERGE INTO ... ON SK_ID_CURR`),
then Gate 2 conditions G2-G5/G8 (PK uniqueness, PII-mask check, dedup match), then Gold T-SQL dev
on the Trial Warehouse (ADR-010 D3). Real Spark CU billed is still unverified against a metering
API in this sandbox (`admin/capacities/*`, `capacities/{id}/metrics` all `404` for this
Contributor-role SP, unchanged since J-016) — wall-clock logged instead in `COST_LOG.md`.
**J-018 (previous):** CU baseline
corrected — Fabric Trial capacity is **64 CU / F64-equivalent / 8 Power BI v-cores**, cited to
`learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity` (the `FTL4` SKU string is not "4
CU" — earlier sessions misread it); see `migration/benchmarks/INFRA_BASELINE.md`. Confirmed via
the real API surface that a failed `RunNotebook` job cannot be "resumed" — no resume endpoint
exists (`POST .../jobs/instances/{id}/resume` → `404`), `cancel` only works on active jobs
(`400 JobAlreadyCompleted` on an already-failed job), and since all failures occur at
Livy-session creation (pre-execution), continuing always means a brand-new `RunNotebook`
submission against the same item ID, never a resume. **2 more real attempts made this session**
(attempts 6-7 overall): attempt 6 after a **~3-day cross-session gap** still failed identically
(`[TooManyRequestsForCapacity]` HTTP 430, `isRetriable:false`, 2.2s) — this is the material new
finding, since a materially longer wait than anything tried in J-016/J-017 still didn't clear
the throttle, weakening the "just wait longer" hypothesis. Attempt 7 (~20 min later) also failed
identically. **7/7 total `RunNotebook` submissions against real Fabric compute have now failed**
across 3 sessions — stopped at 7 (within the 8-new-attempt session cap) since the pattern is
unambiguous across 3+ orders of magnitude of cooldown gap. Zero rows materialized against real
Fabric compute; Gate 2 (G1-G5, G8) still entirely unverified. Full methodology (submission→poll
API surface, failure-stage classification, what's NOT measurable in this sandbox — admin/capacity
metrics endpoints all confirmed `404` for the Contributor-role SP, honest sample-size caveat)
written up in `migration/benchmarks/INFRA_BASELINE.md` as a reusable pattern. Full detail:
`MIGRATION_JOURNEY.md` J-018.

**Next action (Owner call, not mine):** attempt 6's ~3-day-gap failure is stronger evidence than
before that this is a structural Trial-tier ceiling, not a short-cooldown/burst-limit issue —
sizing up off the FTL4 Trial SKU to a paid F-SKU is now the more evidence-backed option versus
waiting longer. If Owner still wants to wait, an hours-scale (not day-scale) gap has not actually
been tried yet in isolation (attempt 6 was a multi-day *cross-session* gap, not a clean
controlled hours-scale single test) — that remains untested. Once Bronze actually runs: verify
row counts against the 7 source CSVs (ADR-007 Tier 1-2), then run the 5 Silver notebooks +
idempotency re-run (ADR-007 G8), then Gold T-SQL dev on the Trial Warehouse (ADR-010 D3).
**Previous checkpoint (J-017):** Retried per
Owner GO. Re-authed `fab`, confirmed capacity still `Active`/FTL4 (no resize) and all 6 Fabric
Notebook items still present. Submitted 3 more `RunNotebook` jobs against `nb_bronze_ingest`
with real cooldown gaps (~5 min, then ~8 min) — **all 3 failed identically**
(`[TooManyRequestsForCapacity]` HTTP 430, `isRetriable: false`, failing at Livy-session creation
in ~1-1.4s). Combined with J-016's 2 attempts, that's **5/5 total `RunNotebook` submissions
against real Fabric compute failed with the exact same non-retriable throttle** — stopped at 5
per the task's explicit cap, per Owner instruction not to loop indefinitely. **Zero rows
materialized against real Fabric compute across both sessions** — Gate 2 (G1-G5, G8) is still
entirely unverified against real Fabric; only the local Tier-0 proof from J-015 stands. Cost:
effectively zero real Spark CU spent across all 5 attempts (all failed pre-execution); see
`COST_LOG.md`. Full detail: `MIGRATION_JOURNEY.md` J-017.
**Previous checkpoint (J-016):** First real Fabric compute attempt made (Owner GO). 6 real Fabric
Notebook items created and verified in workspace `home-credit-risk-dev` (`nb_bronze_ingest` + 5
`nb_silver_*`, item IDs in `MIGRATION_JOURNEY.md` J-016), wired to the real Lakehouse + real
Landing batch (`Files/landing/dev/batch_20260702T203311Z/`). 2 `RunNotebook` Spark job
submissions against `nb_bronze_ingest` both failed in <2s at Livy-session creation with the same
error as above. Full detail: `MIGRATION_JOURNEY.md` J-016.
**Earlier checkpoint (J-015):** Bronze notebook
(`notebooks/nb_bronze_ingest.py`) and real Silver transform logic (all 5 `notebooks/nb_silver_*.py`,
previously stubs) are written, per ADR-002 (PII mask order)/ADR-004 (native Delta MERGE
idempotency)/`docs/PIPELINE_SPEC.md`. Proven locally (ADR-007 **Tier 0**, ADR-010 D1/D2): 9/9
`pytest tests/local -q` tests green, using real PySpark 3.5 + `delta-spark`. All 4 static gates
re-verified green after the change. Full detail: `MIGRATION_JOURNEY.md` J-015.
**Next action:** this is an Owner call, not something to force from a session — either (a) wait
for a materially longer cooldown (hours, not minutes — 4/5/8-minute gaps across 2 sessions have
not been enough to clear the FTL4 Trial throttle) and retry `RunNotebook` against
`nb_bronze_ingest` (item `d56abc42-a29e-4b1b-8554-737b5e5a7f3d`) again, or (b) size up off the
Trial SKU to get a real Spark-VCore allocation. The item + job-submission plumbing is fully
proven end-to-end across 5 real attempts; only actual Spark execution is blocked. Once Bronze
actually runs: verify row counts against the 7 source CSVs and required columns (ADR-007 Tier
1-2), then run the 5 Silver notebooks + idempotency re-run (ADR-007 G8), THEN Gold T-SQL dev on
the Trial Warehouse (ADR-010 D3). Gate 2's sign-off conditions (G1-G5, G8 in
`migration/governance/SIGN_OFF.md`) are still ☐ Pending — no real-Fabric evidence exists yet for
any of them.

---

**Where we were (2026-07-02, before J-015):** Gate 2 infra provisioning is
**live and API-verified** — see `MIGRATION_JOURNEY.md` J-011. Fabric Trial capacity started
(60-day, East Asia), workspace `home-credit-risk-dev` (type Fabric Trial) created with the
trial capacity assigned, Lakehouse `home_credit_lakehouse` created inside it (SQL Analytics
Endpoint auto-provisioned, `Success`), Entra ID App Registration `home-credit-fabric-sp` created
with a client secret and granted Contributor on the workspace. `az` CLI and `fab` (Fabric) CLI
installed in the dev container; both authenticated as the service principal and confirmed via
live API calls, not from memory. `.env` populated with real
`FABRIC_WORKSPACE_ID`/`FABRIC_LAKEHOUSE_ID`/`AZURE_TENANT_ID`/`AZURE_CLIENT_ID`/
`AZURE_CLIENT_SECRET`/`ONELAKE_ENDPOINT` (not committed — `.gitignore:5`).
`TEAMS_WEBHOOK_URL` parked — tenant lacks the M365 licence Power Automate's Teams connector
needs; non-blocking for Gate 2.

**Update (2026-07-02, J-012):** real Kaggle dataset pulled into `data/` (gitignored, 7 CSVs,
row counts match baseline exactly) — Silver-logic work is now unblocked on data. Also added
**ADR-011 (Proposed)**: an explicit **Landing** layer ahead of Bronze — raw CSV lands
byte-for-byte in OneLake Lakehouse **Files** (`Files/landing/`), Bronze materializes from Landing
into Delta **Tables** (Kaggle hit once, at Landing only). Same Lakehouse / one storage surface —
refines ADR-006 §2, no scope/grain impact. Docs updated: ARCHITECTURE, PIPELINE_SPEC, CLAUDE.md,
ADR-006 §2 cross-ref; `doc_reference_contract.py` green.

**Update (2026-07-02, J-013):** `env` scoping made concrete — `ENV=dev` in `.env`/`.env.example`,
Landing path is `Files/landing/<env>/<batch_id>/<file>.csv`, Bronze keeps `env` as a Delta column
(not a table/path split). Separate dev/staging/prod **Fabric workspaces** explicitly rejected for
this single-dev project (would burn the $200 trial credit on unused capacity).

**Update (2026-07-02, J-014):** Fabric Trial capacity checked via API (read-only) — `state:
Active`, SKU `FTL4`. Trial SKUs don't support pause/resume like paid F2 (60-day clock runs
regardless); confirmed via API, not assumed. No cost exposure — Owner elected to leave it running.
**First real Landing batch written**: used `fab mkdir`/`fab cp` to push all 7 modeled source CSVs
+ a `manifest.json` (batch_id/env/ingestion_ts/SHA-256 per file) into OneLake
`Files/landing/dev/batch_20260702T203311Z/` — verified back via `fab ls` (8 objects). This is the
first real (non-doc) artifact of ADR-011. Bronze materialization from this batch has **not** run
yet — no Fabric Spark notebook code executed this session.

**Next action:** materialize Bronze from `Files/landing/dev/batch_20260702T203311Z/` (parse CSV →
typed Delta `bronze.{table}`, attach `ingestion_ts`/`source_file`/`batch_id`/`env`, partition by
`ingestion_date`) — then port the 5 Silver notebooks (`glue/glue_silver_*.py` in the parent repo)
into `notebooks/*.py` (real logic, per ADR-010 D1) + a `tests/local/` FB8 harness (ADR-010 D2) —
dialect review per ADR-004/ADR-006 §3, proven locally (PySpark + delta-spark) before touching the
Trial Warehouse. Then run ADR-007 Tier 0 (local pre-parity sample) before spending any real CU.
Gate 2's actual conditions (G1-G5, G8 in `migration/governance/SIGN_OFF.md`) stay ☐ Pending until
that produces parity evidence.

**Do NOT:** assume the Fabric Trial capacity is paused between sessions — as of J-014 it is
confirmed `Active` and, per Trial SKU limits, may not be pausable at all; the day-60/61 expiry
behaviour is still (unverified).

---

**Where we were (2026-07-01, `main`, PR #1 merged):** Full governance-framework port from the
parent repo `home-credit-pipeline` is complete and merged to `main` — CLAUDE.md, 3 static
contracts, 11 agents, 8 docs, ADR-001..004 (Fabric versions), `scripts/gen_repo_map.py`,
`architecture/REPO_MAP.md`, root logs, `learning/`, `.github/workflows/ci.yml`, `dbt_fabric/`
stubs, and `migration/` (the pre-migration design record: ADR-005/006/007, benchmarks, parity
plan, sign-off gates, copied verbatim from the parent repo's `fabric-migration/` folder).

**Gate 0 is SIGNED (2026-07-01)** — all 4 roles approved in `migration/governance/SIGN_OFF.md`:
- @scope-guardian: APPROVE — boundary contract clean, no scope creep.
- @data-architect: APPROVE (conditional) — Kimball grain/SCD2 verified; `dim_loan_type` and
  `dim_credit_status` mart models still not built (tracked gap, not a violation).
- @finops-agent: APPROVE after mitigation — Fabric F2 (~$262/mo) vs ~$0.19 lifetime baseline is
  a real cost increase; **owner has a $200 USD Fabric/Azure trial credit** covering ~76% of
  month one. Accepted with the expectation that F-SKU capacity is paused/deallocated between
  work sessions, not left running continuously.
- Owner: GO.

`docs/ADR/ADR-005-fabric-full-migration-decision.md` status is now **Accepted** (was Proposed).

**PIVOT + Gate 0.5 SIGNED (2026-07-01):** Owner ruled "Fabric-only" **absolute** → exercised
ADR-006 §4 "Option B". Two new ADRs are now **Accepted** (Gate 0.5, 3 personas + Owner):
- `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` — retire dbt entirely; Gold/mart = Fabric
  Warehouse T-SQL stored procedures; SCD2 = A1 T-SQL MERGE proc. Carries binding conditions
  C1–C8 (NULL-safe change detection, both-direction one-current THROW gate, atomic fallback,
  deterministic HASHBYTES SK, Gold does no PII hashing).
- `docs/ADR/ADR-009-capacity-lifecycle-automation.md` — nightly batch, Azure-native resume
  (chicken-and-egg fix), in-Fabric suspend/watchdog + daily kill-switch, FB7 carve-out.

**BUILD PHASE COMPLETE (2026-07-01)** — the ADR-008 "Same-PR execution checklist" has been
executed on branch `gate-0.5-option-b-adr-008-009`: `warehouse/` T-SQL tree created (staging
views, intermediate views, mart procs for `dim_applicant` + 3 facts, primary MERGE SCD2 proc +
2-step atomic fallback, THROW-based DQ procs for C4/C8), `dbt_fabric/` retired (deleted, not
archived), FB5 rewritten to a dbt-absence check + FB7 added in both boundary-contract copies,
`docs/DATA_MODEL.md`/`CLAUDE.md`/`docs/ARCHITECTURE.md` amended, the pre-existing doc-reference
drift (ADR-005:92) and the mis-stated contract-status line fixed, `architecture/REPO_MAP.md`
regenerated. `warehouse/PROOF_C3_C4_C5.md` supplies the required C3/C4/C5 side-by-side proof.
**@data-architect gave a final, non-conditional APPROVE** (C1–C8 verified file:line against
disk) and **@scope-guardian found no scope creep** (3 mechanical checks it couldn't run itself —
`dbt_fabric/` deletion, `warehouse/` tree contents, boundary-contract green — were independently
confirmed). All 4 static gates (`boundary_contract.py`, `identity_contract.py`,
`doc_reference_contract.py`, `gen_repo_map.py --check`) are green. Full trail:
`MIGRATION_JOURNEY.md` J-001…J-009 (this build itself is not yet logged as its own J-entry).

**What has NOT happened:** no Fabric workspace provisioned, no OneLake Lakehouse created, no
Fabric Spark notebook has run against real data, no `warehouse/` T-SQL proc has executed against
a real Fabric Warehouse (Warehouse MERGE maturity stays unverified until then). `.env.example`
lists the vars a real workspace will need (`FABRIC_WORKSPACE_ID`, `FABRIC_LAKEHOUSE_ID`,
`AZURE_TENANT_ID`/`AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET`, `ONELAKE_ENDPOINT`) — none are
populated with real values yet. Known outstanding nit: `.mcp.json` still references a `dbt` MCP
server block (removal blocked by a permission classifier mid-build; harmless but stale — remove
by hand when convenient).

**Gate 1.5 SIGNED (2026-07-01, commit `f1de0b8`, same branch)** — `docs/ADR/ADR-010-local-first-
dev-and-fabric-trial.md` is now **Accepted**. @scope-guardian + @finops-agent both
APPROVE-CONDITIONAL (conditions applied same-commit), Owner GO. Decision: Silver logic is
developed **locally** (PySpark 3.5 + `delta-spark`, zero-rewrite vs. Fabric Runtime 1.3) under
`tests/local/` (new boundary rule **FB8** — cite ADR-010, dev/test-only, statically checked to
never be wired into a `pipelines/*.json` Data Factory pipeline). Gold T-SQL is authored **directly
against Fabric Trial capacity** (not a local SQL engine — dialect drift would break zero-rewrite).
Provisioning order is **Trial capacity first**, paid $200 credit reserved for scale/parity
validation only (ADR-007 gained a new **Tier 0**: local pre-parity on a sample, before any CU is
spent). All 3 contracts (`boundary_contract.py`, `identity_contract.py`,
`doc_reference_contract.py`) green after this change.

**KIV (Owner instruction, 2026-07-01):** the day-60/61 Fabric Trial expiry behaviour
(auto-suspend vs. auto-delete vs. silent bill-through) is flagged **(unverified)** in ADR-010's
"Trial-capacity operational conditions" section — explicitly deferred by the Owner to be resolved
when Gate 2/Trial-provisioning is actually reached, not now.

**Gate 1 SIGNED (2026-07-01, same branch)** — `migration/governance/boundary_contract_fabric.py`
is now wired into `.claude/hooks/governance_guard.py` (runs alongside `tests/boundary_contract.py`
for every governed boundary path, PostToolUse) and into `.github/workflows/ci.yml` (new step,
after the parent `tests/boundary_contract.py` step). All 4 static gates confirmed green after
wiring: `tests/boundary_contract.py`, `migration/governance/boundary_contract_fabric.py`,
`tests/identity_contract.py`, `tests/doc_reference_contract.py`. Gate 1's "new repo" / "lifted-in
folder" conditions are satisfied by this repo's existing state (it already *is* the dedicated
Fabric repo; `migration/` already *is* the lifted-in design-phase record) — see the
reinterpretation note in `migration/governance/SIGN_OFF.md` Gate 1 section. No real Fabric
resource was provisioned as part of this gate (out of scope by design).

**Next action — Gate 2 (Fabric Silver Parity), sequenced per Gate 1.5/ADR-010**: the first real
provisioning step is the **Fabric Trial capacity** (ADR-010 D4), not paid F2 — this requires an
explicit, separate Owner confirmation (uses a work account, possible billing) before being
executed; it is NOT auto-continued from Gate 1 signing. Once authorised: port the 5 Silver
notebooks from the parent repo's `glue/glue_silver_*.py` locally first (dialect review per
ADR-004/ADR-006 §3, proven via `tests/local/` before touching any capacity), then author/run the
`warehouse/` T-SQL Gold procs directly on the Trial Warehouse (dialect + MERGE-maturity review
per ADR-008).

**Do NOT:** provision any real Fabric resource before Gate 1 is signed. Do NOT provision paid F2
before the Fabric Trial capacity is exhausted or a genuine full-scale parity run needs it
(ADR-010 D4). Do NOT leave a real Fabric capacity (trial or paid) running continuously — pause/
deallocate between sessions; the trial's day-61 behaviour is unverified so treat it as disposable,
not as source of truth (code lives in git). Do NOT assume a Fabric Spark node pool sized smaller
than the parent repo's proven AWS Glue G.1X×2 headroom
(`migration/benchmarks/INFRA_BASELINE.md`) is safe without re-verifying against real Fabric
Spark memory behavior.

## Contract status (as of the ADR-008/009 build-phase PR, 2026-07-01)
- `python tests/boundary_contract.py` — ✅ green (FB5 dbt-absence + FB7 carve-out, rewritten this PR)
- `python tests/identity_contract.py` — ✅ green (retargeted to `warehouse/scd2/`, this PR)
- `python tests/doc_reference_contract.py` — ✅ green
- `python scripts/gen_repo_map.py --check` — ✅ green

**Correction (J-001, found 2026-07-01 pre-flight):** the "framework-init commit" snapshot this
section used to describe was NOT actually all-green — `doc_reference_contract.py` was red on
`main` (2 drift violations at `docs/ADR/ADR-005-fabric-full-migration-decision.md:92`, backticked
`dim_loan_type`/`dim_credit_status` with no model on disk) at the time this file claimed all 4
checks passed. Fixed in this PR via `tests/doc_reference_contract.py`'s `ALLOW` list (both names
are a Gate-0-acknowledged tracked gap, never built as a dbt or `warehouse/` object — not a grain
violation). All 4 checks are genuinely green as of this PR; see `MIGRATION_JOURNEY.md` J-001/J-009.

## Open items carried forward from `migration/PROJECT_STATUS.md` (design-phase notes)
1. ~~**dbt exception (ADR-006 §4)**~~ — **RESOLVED 2026-07-01.** Owner ruled "Fabric-only"
   absolute; ADR-006 §4's own "Option B" fallback was exercised via ADR-008 (dbt retired
   entirely, Gold = `warehouse/` T-SQL stored procedures). See build-phase summary above.
2. **Purview DQ is catalog-only, not a gate** — the inline notebook assertion is the real gate
   (ADR-006 §5). Do not treat a green Purview DQ scan as equivalent to a passing assertion.
3. **Snowflake STAGING parity baseline is incomplete** — only 4 of 7 Silver tables have a
   captured baseline (`migration/benchmarks/SNOWFLAKE_STAGING_BASELINE.md` gap note). The
   remaining 3 tables' Fabric parity target is not yet established anywhere.
4. Every Fabric-specific resume/interview claim is "(unverified)" until a real parity run
   (`migration/validation/parity_check.py`) passes — see `INTERVIEW_GUIDE.md`.
