# ADR-010: Local-First Development Workflow + Fabric Trial Capacity as First Provisioning Target

**Status:** **Accepted 2026-07-01** (Gate 1.5 signed — @scope-guardian + @finops-agent
APPROVE-CONDITIONAL, conditions applied; Owner GO). See `migration/governance/SIGN_OFF.md`.
**Date:** 2026-07-01
**Owner:** Raja Ahmad Luqman (single-dev).

## Context
Gate 0 + Gate 0.5 are signed; the design is locked (Fabric-native, dbt retired, capacity
lifecycle automated). The next real work is **writing and proving pipeline logic**. A Fabric F2
capacity bills a flat ~$262/month whenever Running (`migration/benchmarks/COST_BASELINE.md`), and
the Owner has only a **$200 one-time trial credit**. Burning that credit on *logic-development
iteration* — the write/run/fix loop, which is where most compute-hours die — would be wasteful:
the credit should pay for **parity/scale validation**, not for debugging a typo in a MERGE clause.

The Owner's three explicit requirements for the dev loop:
1. **Free** to iterate.
2. **Zero-rewrite** transfer to Fabric — write the code once, don't maintain two dialects.
3. Easy to move from local → cloud.

These three pull in different directions **per layer**, because the two compute engines carry
different dialect-drift risk on the way to Fabric:

| Layer | Engine | Dialect drift local → Fabric | Free local option that satisfies "zero rewrite" |
|-------|--------|------------------------------|--------------------------------------------------|
| Silver | Spark 3.5 (PySpark + delta-spark) | **~zero** — Fabric Runtime 1.3 = Spark 3.5 vanilla (`ADR-005:32`) | Local PySpark 3.5 + `delta-spark` — same API, copy-paste to notebook |
| Gold | Fabric Warehouse **T-SQL** | **non-trivial** — Fabric Warehouse is a *subset* of SQL Server T-SQL (`IDENTITY`, some `SELECT INTO`, historical `MERGE` gaps) | **None that is faithful.** Local SQL Server / Azure SQL Edge approximates but drifts → violates requirement #2 |

The consequence: **one tool for both layers cannot satisfy all three requirements.** A local
SQL-Server-family engine would make the T-SQL "free" but reintroduce a dialect-touch-up step on
transfer — exactly the rewrite the Owner wants to avoid. So the workflow is **split by drift
risk**, not unified.

## Decision

### D1 — Silver logic: develop locally, in `notebooks/`, against local Spark
The Silver Spark notebooks are **authored and iterated locally** using PySpark 3.5 + `delta-spark`
against **sampled** source CSVs (50k–100k rows, not the full 58.4M). Because Fabric Runtime 1.3 is
vanilla Spark 3.5, the notebook `.py` files are the *same artifact* that later runs in Fabric —
no port, no rewrite. This is already boundary-legal: `notebooks/*.py` may import `pyspark`
(FB6). No new rule is needed for the notebook code itself.

### D2 — Silver **test harness**: fenced local carve-out (new rule FB8)
Proving Silver logic locally needs a test harness that spins up a local `SparkSession`
(fixtures, parity spot-checks, the ADR-007 idempotency re-run). Such a file imports `pyspark`
and does **not** belong in `notebooks/` (it is a test, not a pipeline step). Under the current
contract that would trip **FB6**. ADR-010 introduces a narrow, fenced carve-out:

> **FB8** — standalone PySpark is permitted in **`tests/local/`** (and any subdirectory
> thereof — the ONLY location outside `notebooks/` where it is allowed), provided **every file
> under `tests/local/` cites ADR-010**. These files are **development/test-only**: they must
> never be referenced by a Data Factory pipeline (`pipelines/*.json`, statically enforced) and
> are never deployed to Fabric. The FB1–FB3 SDK bans (no AWS/Snowflake/Airflow) still
> apply inside `tests/local/` (FB4 Slack ban lifted 2026-07-06 per ADR-013). Any PySpark elsewhere, or any `tests/local/` file that omits the
> ADR-010 citation, is a hard FB6/FB8 violation and presumed scope creep.
>
> *Enforcement honesty (cf. FB7):* the citation is a string-containment check — it proves a file
> *claims* the carve-out, not that it was reviewed as genuinely dev-only. @scope-guardian review
> at build time is the semantic gate. The "never referenced by a pipeline" clause **is**
> statically enforced (`_scan_fb8` greps `pipelines/*.json`).

Mirror of the FB7/ADR-009 pattern: one fenced location, cite-the-ADR, same underlying platform
bans, reviewed by @scope-guardian at build time.

### D3 — Gold T-SQL: develop directly on Fabric **Trial** capacity, not a local SQL engine
The Gold Warehouse procs (`warehouse/{staging,intermediate,mart,scd2,dq}`) are authored **directly
against the Microsoft Fabric 60-day Trial capacity** — the *real* Warehouse engine — using a small
sample dataset to keep CU draw negligible. This is the only way to honour requirement #2
(zero-rewrite): the dialect the Owner writes against *is* the production dialect, so promotion to
paid capacity changes **zero lines of SQL**. A local SQL-Server-family engine is explicitly
**rejected** for this layer because its dialect drift reintroduces the rewrite step.

### D4 — Fabric Trial capacity is the **first** provisioning target (not paid F2)
When Gate 1 authorises provisioning, the first capacity provisioned is a **Fabric Trial capacity**
(work/school Entra account — the Owner confirmed they will use their work email; personal Gmail is
not trial-eligible). The $200 paid credit stays untouched until the Trial is exhausted or a
scale/parity run genuinely needs paid F2. This sequences spend: **free trial for logic + small-
sample parity; paid credit only for full-scale validation.**

## Workflow (end-to-end)
```
1. Silver logic     → local PySpark 3.5 + delta-spark, sampled CSV      [free, offline]  (D1)
                       authored in notebooks/*.py = the deployable artifact
2. Silver local test→ tests/local/*.py harness, local SparkSession       [free]           (D2/FB8)
                       ADR-007 idempotency re-run + PII-mask spot-check on sample
3. Gate: local pre-parity — logic correct on sample BEFORE any Fabric CU is spent
4. Gold T-SQL       → authored directly on Fabric TRIAL Warehouse, sample [free 60 days]   (D3/D4)
                       dialect == production → zero rewrite on promote
5. Fabric parity    → ADR-007 Tier 1-5 at scale (trial first, paid credit only if needed) (D4)
6. Gate 2/3 sign-off→ then, and only then, steady-state paid F2 + ADR-009 lifecycle
```

## Scope — what this ADR does and does NOT change
- **Does NOT touch grain/SCD2/identity** (ADR-001/008 unchanged) — this is a *workflow* decision.
- **Does NOT reopen the stack** — local PySpark is the same Spark family already chosen; it is a
  dev-time convenience, never a deployed component. No new platform is introduced.
- **Does NOT relax FB1–FB3** — the AWS/Snowflake/Airflow bans hold everywhere, including
  `tests/local/`. (FB4 Slack ban was later lifted by ADR-013, 2026-07-06, for alerting only —
  independent of this ADR.)
- **Adds FB8** — one fenced local-dev carve-out, @scope-guardian veto (parallel to FB7).
- **Adds a local pre-parity checkpoint** to ADR-007 (Tier 0, see amendment note in that ADR).

## Trial-capacity operational conditions (from @finops-agent, pre-Gate-1.5 hygiene)
These must be answered before Gate 1.5 fully closes — provisioning hygiene, not workflow blockers:
- **Day-60/61 expiry.** If Gold dev/parity is unfinished when the 60-day Trial expires, the plan
  is: artifacts (T-SQL procs) live in git, not only in the Trial workspace, so expiry loses **no
  code** — worst case is re-running against a fresh capacity. The Trial must be treated as
  disposable compute, never as the source of truth. Confirm Fabric's actual day-61 behaviour
  (auto-suspend vs. auto-delete vs. silent bill-through) before relying on it. **(unverified)**
- **ADR-009 lifecycle coverage.** ADR-009's resume/suspend/watchdog automation was designed for
  the **paid F2**. During the Trial phase it is **not** required (Trial is free), but the Trial
  capacity should still be manually paused between sessions as hygiene. ADR-009 automation is
  wired only when paid F2 is provisioned (Gate 2/3), not against the Trial.
- **CU budget line.** Log a rough Gold-Trial-dev CU/day figure in `COST_LOG.md` from the first
  real Trial run so "extends runway" is a number, not an adjective (carries forward the ADR-009
  early-CU-logging condition).
- **Trial-capacity throughput ceiling.** Fabric Trial capacity is throttled below F64; sample-
  scale Gold dev fits, but full-scale parity (ADR-007 Tiers 1–5) may need paid F2 — that is the
  intended trigger for touching the $200 credit (D4).
- **Work-account eligibility fallback.** If the work/school tenant becomes unavailable mid-project,
  the fallback is: reopen ADR-010, provision paid F2 directly (accepting the earlier spend).

## Consequences
**(+)** Logic-development iteration costs **$0** — the trial/paid credit is reserved for validation
  at scale, materially extending runway beyond the ADR-009 estimate.
**(+)** Zero-rewrite promotion for both layers: Silver because Spark 3.5 == Spark 3.5; Gold because
  the dev engine *is* the Fabric Warehouse.
**(−)** A second permitted PySpark location (`tests/local/`) widens the boundary surface — fenced
  by FB8 + @scope-guardian review, but it is one more thing to police.
**(−)** Gold logic cannot be developed fully offline (needs the trial capacity online) — accepted,
  because the alternative (local SQL engine) breaks the zero-rewrite requirement.
**(−)** Trial-capacity eligibility depends on a work/school account — a hard external dependency
  outside the repo's control (Owner confirmed available).

## Sign-off (drafted-text review — Owner GO pending)
- [x] **@scope-guardian** — 2026-07-01 **APPROVE-CONDITIONAL**. FB8 concept sound and narrower
  than the FB7 precedent. Three fixes required and now applied: (1) pipeline-isolation clause
  statically enforced in `_scan_fb8` (greps `pipelines/*.json`); (2) code/doc agree on
  subdirectory nesting; (3) citation-is-string-match limitation disclosed in the contract
  docstring. D3/D4 keep the Gold data plane 100% Fabric-native — no veto.
- [x] **@finops-agent** — 2026-07-01 **APPROVE-CONDITIONAL**. Trial-first + local-first sequencing
  is a real (not cosmetic) credit-protection win; finops economics of D1/D2/D4 signed. Conditions
  carried forward as pre-Gate-1.5 provisioning hygiene (day-60/61 expiry, ADR-009-covers-Trial?,
  CU-budget line, throughput ceiling, work-account fallback) — see "Trial-capacity operational
  conditions" above. ADR-009 ~$18–22/mo figure noted (unverified) this session.
- [x] **Owner** — GO 2026-07-01.
