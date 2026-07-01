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
