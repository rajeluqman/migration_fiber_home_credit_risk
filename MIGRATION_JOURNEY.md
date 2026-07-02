# Migration Journey — AWS/Snowflake → Fabric (execution log)

> Live journal of the *actual* migration work: each step, the hiccup/risk hit, and how it was
> resolved. Distinct from `DECISION_LOG.md` (the what/who ledger) and `PROJECT_STATUS.md` (the
> resume-here checkpoint). This file answers "what went wrong and how did we solve it" —
> portfolio + interview evidence of real migration judgement, not a clean-room narrative.
>
> Append newest entries at the bottom. Every load-bearing claim carries `file:line` evidence or
> is tagged `(unverified)` until proven against a real Fabric workspace.

---

## J-001 · 2026-07-01 · Pre-flight repo verification (before any build)
**Step:** Verify folder tree + branches against parent repo `home-credit-pipeline` before handing
build work off.
**Hiccups found:**
1. `tests/doc_reference_contract.py` is **RED on `main`** (2 drift violations, `ADR-005:92`
   backticks `dim_loan_type`/`dim_credit_status` which have no model on disk) — yet
   `PROJECT_STATUS.md:49` claims it green. A CI-blocking contract mis-reported as passing.
2. dbt stub gaps beyond the 2 Gate-0-acknowledged marts: missing `stg_bureau`,
   `stg_bureau_balance`, `stg_installments`, `int_installment_payments`, and the
   `generate_surrogate_key` macro (parent has them, `dbt_fabric/` does not).
3. Provenance narrative overstated: parent GitHub repo has **no** `fabric-migration/` folder, no
   `.claude/`, and only `ADR-001` in `docs/ADR/` — so `migration/`, the agent framework, and
   ADR-002/003/004 were authored in *this* repo, not "ported 1:1".
**Resolution:** Deferred fixes into the full-native rework (J-002) since retiring dbt rewrites the
same contract/folder surface anyway. Status-line correction + drift fix folded into ADR-008 work.
**Status:** Open — carried into J-002.

## J-002 · 2026-07-01 · Decision: go 100% Fabric-native, retire dbt (ADR-006 Option B)
**Step:** Owner ruled "Fabric-only" is **literal, not pragmatic** — no third-party tooling at all.
This activates ADR-006 §4 "Option B" (the flagged fallback) and closes the
`DECISION_LOG.md:14-15` pending decision.
**What changes:** Gold/mart layer moves from **dbt Core (`dbt-fabric` adapter)** →
**Fabric Warehouse T-SQL stored procedures**. Great Expectations stays retired (inline PySpark
asserts + Purview DQ, unchanged from ADR-006 §5).
**Hiccup/risk:** This re-opens a signed ADR (ADR-006) — a scope-material change, so it needs a
fresh gate + persona sign-off, not a silent edit. Governance surface to rewrite: new ADR-008
(supersede §4) + ADR-009 (capacity automation), `boundary_contract` FB5 (dbt→no-dbt),
`dbt_fabric/` → `warehouse/`, and the doc-reference/repo-map generators.
**Status:** Open — ADR-008 to be drafted under a gate.

## J-003 · 2026-07-01 · Decision: SCD2 engine = A1 (Warehouse T-SQL MERGE)
**Step:** Chose T-SQL MERGE stored proc in Fabric Warehouse over Spark Delta MERGE (A2) for the
`dim_applicant` SCD2 build.
**Why:** Matches the Fabric reference architecture (Spark→Silver, Warehouse T-SQL→Gold) that
enterprise Fabric shops actually run; cleanest dbt-replacement; keeps the Spark-only-in-Silver
boundary intact; demonstrates both PySpark + T-SQL SCD2 skill.
**Hiccup/risk:** Fabric Warehouse `MERGE` maturity is **(unverified)** — cannot test without a
real workspace. Mitigation: fallback to a 2-step `UPDATE`(expire) + `INSERT`(new version) pattern
that needs no MERGE at all. The "one `is_current=1` per applicant" invariant is not DB-enforced
(Warehouse PK/FK are metadata-only) → must be guarded by a T-SQL assertion proc (`THROW`).
**Status:** **LOCKED by Owner 2026-07-01.** To be written into ADR-008.

## J-004 · 2026-07-01 · Design: capacity auto-off + nightly batch lock
**Step:** Owner accepted "serving goes cold when idle" and asked for a batch-window lock.
**Design:** Data Factory scheduled trigger @ 00:00 (bank-sleep window, ~1h run):
`Resume capacity (Web→Azure REST) → Bronze → Silver → Gold → DQ gate → Suspend → Teams alert`.
A separate **watchdog pipeline** (every 15–30 min) force-suspends the F-capacity if it is
`Running` outside the 00:00–01:30 window and posts a Teams alert — this is the "lock".
Azure Cost Management budget = notify-only alerts (50/80/100% → Teams); the watchdog is the real
control.
**Hiccup/risk:** Resume must precede all work (paused capacity runs nothing); Service Principal
needs Contributor on the capacity for the suspend/resume REST calls. All native, zero third-party.
**Status:** Design agreed — to be specified in ADR-009. **SUPERSEDED in part by J-005 (resume flaw).**

## J-005 · 2026-07-01 · Design re-review: chicken-and-egg in auto-resume + port-vs-optimal
**Step:** Owner asked to re-check all finalized decisions against "what would best-practice Fabric
actually do" rather than a 1:1 AWS port.
**BUG found (blocking J-004):** the nightly design had a **Data Factory scheduled trigger** resume
the F-capacity. But Data Factory runs *on* the Fabric capacity — a **suspended** capacity means the
Fabric scheduler is also dead and cannot fire the pipeline that resumes it. **Resume must come from
OUTSIDE Fabric** (Azure Logic App / Automation runbook / Function timer → ARM `/resume` REST → then
kick the pipeline). Suspend-at-end and the watchdog CAN stay inside Fabric (capacity is live at
those moments). This collides with the strict "Fabric-only" ruling — resume needs one tiny
Azure-native (not third-party) component, or a manual resume. Owner decision pending.
**Port-vs-optimal improvements identified (Fabric should beat a straight port):**
1. PII hash: parent uses a row-wise Python `sha256_udf` (Glue anti-pattern, slow) → use native
   vectorised `F.sha2(col, 256)` in Fabric Spark. Same output, far faster.
2. Silver: parent has 5 hand-copied Glue jobs → option of 1 metadata-driven parameterised notebook
   (config-table + ForEach) — more senior pattern, less duplication. Trades against concept-parity
   readability.
3. DQ: bare `assert` loses GX's declarative reporting → emit assertion results to a Delta
   `dq_results` table so Data Activator can watch trends (better than parent).
4. Purview: classify the PII columns in-catalog (parent had zero cataloguing).
5. Surrogate key: `HASHBYTES('SHA2_256', ...)` over parent's `md5` (collision resistance; still
   deterministic for idempotent MERGE).
**Honest note:** retiring dbt is optimal *within* the Fabric-only constraint, not globally optimal —
we lose dbt's test-as-code / lineage / snapshot ergonomics and rebuild them by hand in T-SQL.
**Resolution (Owner 2026-07-01):** accept **one Azure-native control-plane component** (Logic App /
Automation runbook / Function timer) for capacity **resume** @00:00 → ARM `/resume` → trigger the
Data Factory pipeline. Suspend + watchdog stay inside Fabric. Scope carve-out: strict "Fabric-only"
is relaxed to **"Fabric-only data plane + minimal Azure-native capacity lifecycle control"** — still
zero third-party (all Microsoft/Azure). **@scope-guardian must sign this carve-out in ADR-009.**
**Status:** Resolved — resume = Azure-native; 5 improvements + carve-out to fold into ADR-008/009.

## J-006 · 2026-07-01 · Design-gate review (3 personas) — all APPROVE-conditional
**Step:** Spawned @data-architect, @scope-guardian, @finops-agent to review the ADR-008/009 design
before drafting. All three read the governing docs and returned APPROVE-conditional (no BLOCK).
**@data-architect (ADR-008, grain/SCD2 fidelity) — conditions C1–C8, veto if absent:**
- C1: ADR-008 supersedes ADR-006 §4; amend `docs/DATA_MODEL.md:36-37` (dbt-snapshot claim goes
  false) in the SAME PR.
- C2: pin SCD2 change-detection to exactly the 4 tracked cols; changing the set needs a new ADR.
- C3: **NULL-safe change detection mandatory** — T-SQL `<>` returns UNKNOWN on NULL → missed
  version. Use `IS DISTINCT FROM` emulation / `EXCEPT`. Prove side-by-side vs dbt on a NULL row.
- C4: post-MERGE THROW assertion gate for the one-current invariant, **both directions** (>1 current
  AND 0 current), wired as a Data Factory FAIL branch.
- C5: 2-step UPDATE-expire+INSERT fallback must be **atomic (one txn)**, else C4 zero-current check
  blocks the run.
- C6: HASHBYTES SK must be deterministic — explicit `CONVERT` with fixed style codes + NULL→sentinel
  before hashing (CONCAT_WS skips NULLs → collisions); SK must NOT be the SCD2 match key.
- C7: Gold does NO re-hashing / NO sentinel handling — PII arrives pre-masked from Silver (ADR-002
  stays upstream); HASHBYTES in Gold = surrogate keys only, never PII.
- C8: extend THROW uniqueness asserts to each of the 3 fact grain keys (dbt test-as-code debt).
**@scope-guardian (ADR-008 + ADR-009 scope) — APPROVE-conditional both:**
- dbt removal = scope reduction (ADR-006 §4 pre-authorised Option B). Retire `dbt_fabric/` fully;
  update `CLAUDE.md:58,65-67` + `docs/ARCHITECTURE.md` same PR.
- FB5 rewrite: "adapter allow-list" → "dbt-absence check" (deny any `profiles.yml`/`dbt_project.yml`/
  `import dbt`), in BOTH `tests/boundary_contract.py` and `migration/governance/boundary_contract_fabric.py`.
- Azure-resume carve-out approved NARROW: pick ONE mechanism; component does exactly 2 actions
  (ARM `/resume` + trigger 1 named pipeline); suspend+watchdog stay in Fabric; Managed Identity, no
  secrets in repo. New **FB7** rule to fence the carve-out; ADR-009 needs a "What this is NOT" section.
**@finops-agent (ADR-009 cost) — APPROVE-conditional; Gate-0 pause condition satisfied:**
- Happy-path est. ~$18–22/mo (1.5h/day F2) → ~9–10 months on the $200 credit — better than the
  Gate-0 $62/mo sizing, but rests entirely on the watchdog never failing (est., billing granularity
  unverified).
- Conditions: confirm watchdog fires independent of capacity health (else same J-005 bug); add a
  **daily unconditional hard-stop kill-switch** (Azure Automation, outside Fabric) as 2nd layer; log
  real CU draw into `COST_LOG.md` early; confirm F2 minimum billing increment.
**Status:** Review complete. Next: draft ADR-008 + ADR-009 baking in ALL conditions above + the
same-PR doc amendments, then route drafted text back to the 3 personas for final (non-conditional)
sign-off in `SIGN_OFF.md`.

## J-007 · 2026-07-01 · ADR-008 + ADR-009 drafted (conditions baked in)
**Step:** Drafted `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` (grain/SCD2, conditions C1–C8 +
scope FB5 + folded improvements) and `docs/ADR/ADR-009-capacity-lifecycle-automation.md` (nightly
batch, Logic App resume locked, in-Fabric suspend/watchdog, daily kill-switch, FB7 carve-out,
finops conditions). Added a PROPOSED-supersession pointer to ADR-006 §4 in **both** copies
(docs/ADR + migration/ADR); original §4 text left intact per ADR discipline.
**Cross-reviewer tension surfaced (not silently resolved):** @scope-guardian capped the external
component at 2 actions (resume+trigger); @finops-agent needs a daily external kill-switch (a 3rd
action). ADR-009 proposes "control-plane actions only" and flags it for @scope-guardian's explicit
re-confirmation at final sign-off.
**Verification:** `python tests/doc_reference_contract.py` still shows exactly the 2 pre-existing
J-001 violations (ADR-005:92) — the new ADRs added **zero** new drift. The 2 pre-existing are on
ADR-008's same-PR fix checklist (item 5).
**Deferred to build phase (post final sign-off), NOT done now:** the same-PR doc amendments
(DATA_MODEL/CLAUDE/ARCHITECTURE), FB5/FB7 boundary-contract rewrite, `dbt_fabric/`→`warehouse/`
retire, and the J-001 drift fix — these land together in the build PR so sign-off reviews one
coherent change, not a half-edited tree.
**Status:** ADRs drafted (Status: Proposed). Awaiting final non-conditional sign-off from the 3
personas on the drafted text, then Owner GO → build phase (Sonnet executes against the frozen spec).

## J-008 · 2026-07-01 · Final sign-off — 3 personas APPROVE the drafted ADR text (Owner GO pending)
**Step:** Routed the drafted ADR-008/009 text back to the 3 personas for final gate votes
(review-only, no file edits, to avoid a SIGN_OFF.md write race).
**Verdicts (all APPROVE):**
- @data-architect → APPROVE ADR-008; C1–C8 verified line-by-line. Signature contingent on the
  C3 NULL-safe + C4 invariant + C5 atomicity side-by-side dbt proof landing in the build PR.
- @scope-guardian → APPROVE ADR-008 + ADR-009; **FB7 widening accepted** ("control-plane actions
  only" — resume/suspend/trigger). Hard-cap precedent: 3 actions on 1 named resource; a 4th action
  or 2nd external resource needs a fresh ADR.
- @finops-agent → APPROVE ADR-009; Gate-0 pause condition satisfied by design; billing-increment +
  early CU-logging carried forward as honest pre-build verification items; economic case is
  watchdog+kill-switch-dependent (accepted, on record).
**Recorded:** checked the persona boxes in both ADRs' sign-off blocks (Owner box pending); added a
new **Gate 0.5 — Option B Design Amendment** section to `migration/governance/SIGN_OFF.md`
(3/4 signed, Owner ☐ Pending, outcome OPEN).
**Status:** Gate 0.5 = 3/4 signed. **Awaiting Owner GO.** On GO: ADR-008/009 → Accepted, then the
ADR-008 same-PR build checklist may begin (Sonnet executes against the frozen spec).

## J-009 · 2026-07-01 · Owner GO — Gate 0.5 SIGNED, ADR-008/009 Accepted
**Step:** Owner gave GO. Gate 0.5 fully signed (4/4). Recorded across the governance surface:
- ADR-008 + ADR-009 Status → **Accepted 2026-07-01**; Owner sign-off boxes checked.
- `migration/governance/SIGN_OFF.md` Gate 0.5 → ☑ SIGNED (Owner row signed, outcome closed).
- ADR-006 §4 supersession pointer (both copies) → "Accepted 2026-07-01, Gate 0.5".
- `DECISION_LOG.md` → 3 new decision rows; Pending-decisions section resolved (Gate 0 + 0.5 signed,
  Option B decided).
- `PROJECT_STATUS.md` RESUME HERE → pivot + Gate 0.5 recorded; next action = build phase.
**Spec is now FROZEN.** Build phase (ADR-008 same-PR checklist) is authorised: create `warehouse/`
T-SQL tree, retire `dbt_fabric/`, rewrite FB5 + add FB7 in both boundary-contract copies, amend
DATA_MODEL/CLAUDE/ARCHITECTURE, fix the pre-existing doc-reference drift + mis-stated status line,
regenerate REPO_MAP. Grain-proof conditions C3/C4/C5 (side-by-side dbt comparison) are due in that
same PR per @data-architect's contingent signature.
**Still unverified until a real Fabric workspace (Gate 1):** Warehouse MERGE maturity, Spark pool
memory vs 27M-row baseline, idempotency re-run, PII order under native `sha2()`.
**Status:** Gate 0.5 CLOSED. Ready for build phase / Gate 1 provisioning (separate, unsigned).

## J-010 · 2026-07-01 · Build phase executed — ADR-008/009 same-PR checklist complete
**Step:** Executed the ADR-008 same-PR checklist on `gate-0.5-option-b-adr-008-009`: created
`warehouse/` T-SQL tree (staging/intermediate views, `dim_applicant` + 3 fact mart procs, primary
MERGE SCD2 proc + 2-step atomic fallback, THROW-based DQ procs for C4/C8), deleted `dbt_fabric/`
in full, rewrote FB5 (dbt-absence check) and added FB7 (capacity-lifecycle carve-out) identically
in both `tests/boundary_contract.py` and `migration/governance/boundary_contract_fabric.py`,
retargeted `tests/identity_contract.py`/`tests/doc_reference_contract.py` from `dbt_fabric/` to
`warehouse/`, amended `docs/DATA_MODEL.md`/`CLAUDE.md`/`docs/ARCHITECTURE.md`, fixed the
pre-existing J-001 doc-reference drift + mis-stated contract-status line, and regenerated
`architecture/REPO_MAP.md`. Also swept residual dbt references beyond the named 3 docs
(`requirements.txt`, `.env.example`, `.gitignore`, `pipelines/gold_dbt.json` →
`gold_warehouse.json`, `.claude/hooks/governance_guard.py`, `scripts/gen_repo_map.py`,
`.github/workflows/ci.yml`, remaining `docs/*.md`, `.claude/agents/*.md`) since a half-retired
dbt reference is a correctness bug, not a style choice, once dbt no longer exists on disk.
**Grain-proof delivered:** `warehouse/PROOF_C3_C4_C5.md` — worked NULL-transition example proving
the T-SQL NULL-safe comparison (C3) matches dbt's own generated `check`-strategy SQL, plus the
C4/C5 failure-mode reasoning.
**Verification:** all 4 static gates green (`boundary_contract.py`, `identity_contract.py`,
`doc_reference_contract.py`, `gen_repo_map.py --check`). Spawned @data-architect and
@scope-guardian (read-only review, no file edits) against the finished diff:
- @data-architect: **final, non-conditional APPROVE** — verified C1–C8 file:line against disk,
  not narrative; one non-blocking note (fallback proc swap is a manual edit, documented, fine).
- @scope-guardian: no scope creep found in everything it could inspect; flagged 3 mechanical
  checks it lacks Bash tooling to run itself (`dbt_fabric/` actually deleted vs. archived,
  `warehouse/` tree has no stray extra marts, `boundary_contract.py` genuinely green). All 3
  independently confirmed via shell this session.
**One item deferred, not silently dropped:** `.mcp.json`'s stale `dbt` MCP server block — its
removal was blocked by the permission classifier as an unrequested self-modification; left
in place, flagged to the owner for manual removal.
**Status:** Build phase CLOSED. `docs/ADR/ADR-008`'s contingent grain-proof condition is
satisfied. Next: Gate 1 (real Fabric provisioning) — still separate, still unsigned.

## J-011 · 2026-07-02 · Gate 2 provisioning — Fabric Trial capacity, workspace, lakehouse live
**Step:** Owner executed the first real Fabric provisioning step per ADR-010 D4 sequencing
(Trial capacity first, paid $200 credit still untouched). Owner action (browser, portal):
started Fabric Trial (60-day, East Asia region), created workspace `home-credit-risk-dev`
(type: **Fabric Trial**, not Pro/PPU) with the trial capacity assigned, created Lakehouse
`home_credit_lakehouse` inside it, registered an Entra ID App Registration
(`home-credit-fabric-sp`) with a client secret, and granted that SP **Contributor** access to
the workspace via Manage access.
**Tooling installed this session:** Azure CLI (`az` 2.87.0, via Microsoft apt repo) and Fabric
CLI (`fab` 1.6.1, via `pip install ms-fabric-cli`) — both in the dev container, not on any
Fabric compute. `fab config set encryption_fallback_enabled true` was required (sandbox has no
OS credential-manager backend for `fab`'s default encrypted token cache).
**Verified, not assumed** — both CLIs authenticated as the service principal and confirmed live
state via direct API calls (not from memory/portal screenshots):
- `az login --service-principal ... --allow-no-subscriptions` → succeeded (tenant-level account,
  no Azure subscription attached to the SP — expected, not needed for Fabric-API-only work).
- `fab auth login -u <client_id> -p <secret> -t <tenant_id>` → succeeded, tokens issued for
  Fabric/PowerBI, Storage, and Azure scopes.
- `fab api -X get workspaces/<FABRIC_WORKSPACE_ID>` → `200`, `capacityAssignmentProgress:
  Completed`, capacity region East Asia.
- `fab api -X get workspaces/<id>/lakehouses/<FABRIC_LAKEHOUSE_ID>` → `200`,
  `sqlEndpointProperties.provisioningStatus: Success` (SQL Analytics Endpoint
  auto-provisioned, confirming the Warehouse T-SQL entry point exists ahead of ADR-008 work).
**`.env` populated** (not committed — `.gitignore:5` already covers it) with real
`FABRIC_WORKSPACE_ID`, `FABRIC_LAKEHOUSE_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
`AZURE_CLIENT_SECRET`; `ONELAKE_ENDPOINT` corrected from the generic default to the tenant's
actual regional endpoint (`https://eastasia-onelake.dfs.fabric.microsoft.com`), read back from
the workspace API response rather than guessed.
**Parked, not blocking:** `TEAMS_WEBHOOK_URL` — Teams "Workflows" webhook setup failed with
`Failed to get license information for the user` (tenant/account lacks a full M365 licence
Power Automate's Teams connector requires). Not a dependency for Gate 2 (Silver parity); relevant
again at ADR-009 alerting, post-Gate-4. Left as placeholder in `.env`.
**Not yet done:** the day-60/61 Trial expiry behaviour is still (unverified) per the Gate 1.5 KIV
— nothing about today's provisioning resolves that; capacity should still be treated as
disposable and paused/deallocated between sessions, not left running.
**Status:** Gate 2 infra prerequisites (workspace + lakehouse + SP auth) are live and
API-verified. Gate 2's actual sign-off conditions (G1-G5, G8 in
`migration/governance/SIGN_OFF.md`) are still ☐ Pending — they require the 5 Silver notebooks to
actually run and produce parity evidence, which has not happened yet. Next: port
`glue/glue_silver_*.py` (5 notebooks) to `tests/local/` under FB8, dialect-reviewed against
ADR-004/ADR-006 §3, proven locally before any Trial Warehouse CU is spent (ADR-007 Tier 0).

## J-012 · 2026-07-02 · Real Kaggle sample pulled + explicit Landing zone added (ADR-011)
**Step:** Two things, in prep for the Silver-logic work.
**(1) Data pull.** Downloaded the real competition dataset via Kaggle CLI into `data/` (gitignored).
Had to upgrade `kaggle` 1.6.14 → 2.2.3 — the new `KGAT_`-format token in `.env` is not accepted
by the 1.6.x client (`OSError: Could not find kaggle.json`); 2.2.3 reads `KAGGLE_API_TOKEN` from
env correctly. All 7 CSV row counts match the doc/benchmark baseline **exactly** (application_train
307,511; bureau 1,716,428; bureau_balance 27,299,925; previous_application 1,670,214;
installments_payments 13,605,401; POS_CASH_balance 10,001,358; credit_card_balance 3,840,312).
Zip deleted post-extract; `data/` stays gitignored.
**(2) Landing zone decision (ADR-011, Proposed).** Owner asked whether raw should land in OneLake
first, then Bronze. Confirmed the current design had **no separate landing** — Bronze did double
duty (raw capture + first curated Delta). Owner elected to make Landing **explicit**: raw CSV lands
byte-for-byte in the Lakehouse **Files** area (`Files/landing/<batch_id>/`), Bronze materializes
**from Landing** into typed Delta **Tables** — Kaggle hit once, at Landing only. Rationale: raw
immutability/forensic original, replay-without-re-fetch, banking-domain provenance, schema-drift
detection. Cost accepted: ~2× raw storage footprint + one extra pipeline step; "replay from source"
benefit is partly theoretical here since the Kaggle dataset is frozen.
**Boundary check:** Landing = OneLake **Files** in the *same* `home_credit_lakehouse` — no new
service, no new connector, no cross-cloud egress. Refines ADR-006 §2 "one storage surface", does
not reverse it. No grain/SCD2 impact (ingress layer, upstream of modelling).
**Docs touched:** new `docs/ADR/ADR-011-onelake-landing-zone.md` (Proposed); updated
`docs/ARCHITECTURE.md` (Stack table + Data Flow), `docs/PIPELINE_SPEC.md` (new Landing Layer +
pipeline-chain note), `CLAUDE.md` (stack table), `docs/ADR/ADR-006` §2 (refinement cross-ref).
`migration/ADR/ADR-006` left untouched (frozen pre-migration record). `doc_reference_contract.py`
green (23 docs). Owner elected **skip persona sign-off** for this refinement — Owner GO direct.
**Status:** ADR-011 Proposed, docs consistent. Silver-logic work (ADR-010 D1/D2) now unblocked —
real sample data present. Next unchanged: implement Silver transforms in `notebooks/*.py` + FB8
harness in `tests/local/`, prove ADR-007 Tier 0 locally before any Trial CU.

## J-013 · 2026-07-02 · `env` scoping for Landing/Bronze — single workspace, not dev/staging/prod
**Step:** Owner asked whether Landing needs separate dev/staging/production folders (the classic
env-tier pattern). Checked current design: `env` was already named as a Bronze metadata column in
`docs/PIPELINE_SPEC.md` but its value/path convention was never defined.
**Decision:** `env` is a **metadata tag, not a workspace split**. Added `ENV=dev` to `.env`/
`.env.example`. Landing path becomes `Files/landing/<env>/<batch_id>/<file>.csv`; Bronze keeps
`env` as a Delta column (one `bronze.{table}`, filterable by env), not a separate table/path.
Explicitly **rejected** separate dev/staging/prod Fabric workspaces: this is a single-dev
portfolio project, no second team, no promote-across-env workflow — a 2nd/3rd workspace would be
a 2nd/3rd Fabric capacity paid for with the same $200 trial credit @finops-agent already flagged
as tight (ADR-010, Gate 0). One workspace + an `env` column demonstrates env-awareness honestly
without paying for isolation nobody exercises.
**Docs touched:** `docs/ADR/ADR-011-onelake-landing-zone.md` (new "`env` — single workspace,
metadata-level separation" subsection + Alternatives entry), `docs/PIPELINE_SPEC.md`,
`docs/ARCHITECTURE.md`, `CLAUDE.md` (path strings updated to `{env}`), `.env` + `.env.example`
(`ENV=dev` added). `doc_reference_contract.py` green (23 docs).
**Status:** ADR-011 still Proposed, now with `env` scheme concrete. No further doc gaps found for
this decision. Next unchanged: Silver notebook logic + `tests/local/` FB8 harness (ADR-010 D1/D2).
