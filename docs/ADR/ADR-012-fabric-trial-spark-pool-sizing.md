# ADR-012: Fabric Trial Spark Pool Sizing — Small, Fixed-Node Custom Pool (mandatory workspace default)

**Status:** **Accepted 2026-07-05** — live-proven, not a proposal. The fix below is already the
workspace's operational reality (`SmallFixedPool` is the default pool, verified via the real API)
and cleared the throttle end-to-end on the first attempt after it was applied. See
`MIGRATION_JOURNEY.md` J-019 for the full live-execution evidence trail.
**Date:** 2026-07-05
**Owner:** Raja Ahmad Luqman (single-dev).
**Purview:** infra / compute-sizing — @scope-guardian + @infra-reality-agent (NOT @data-architect;
this touches no grain, SCD2, or model).

## Context
Every one of the first **8** `RunNotebook` Spark-job submissions against real Fabric compute
failed identically (J-016 / J-017 / J-018 — attempts 1–7), each rejected in **under 2.5 seconds**
at **Livy-session creation**, before any Spark executor was allocated and before any notebook cell
ran:

```
Exception: Failed to create Livy session for executing notebook. Error:
[TooManyRequestsForCapacity] HTTP Response code 430: This Spark job can't be run because
you've hit a Spark compute or API rate limit... choose a larger capacity SKU, or try again
later. isRetriable: false
```

The failure was `isRetriable: false` and recurred across gaps ranging from ~4 minutes to ~3 days
(attempt 6), so it was **not** a transient burst/cooldown limit — the "just wait longer"
hypothesis was falsified by the 3-day gap failing identically (J-018). The Fabric Trial capacity
itself was confirmed healthy throughout: `state: Active`, `sku: FTL4` (= **64 CU /
F64-equivalent / 8 Power BI v-cores**, per `migration/benchmarks/INFRA_BASELINE.md` and
`learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity`), capacity-usage meter near zero.

## Root cause (confirmed before acting, not assumed)
A live `GET workspaces/{id}/spark/pools` showed the workspace had exactly one pool — the
auto-provisioned **"Starter Pool"**:

- `nodeSize: Medium`, `nodeFamily: MemoryOptimized`
- `autoScale: {enabled: true, minNodeCount: 1, maxNodeCount: 10}`
- `dynamicExecutorAllocation: {enabled: true, minExecutors: 1, maxExecutors: 9}`

`GET workspaces/{id}/spark/settings` confirmed this Starter Pool was also the workspace
**default** (`pool.defaultPool.id: 00000000-0000-0000-0000-000000000000`) used by every notebook
run. So every prior attempt was implicitly requesting **up to 10 Medium / MemoryOptimized nodes**
against a 64-CU Trial capacity. The Trial SKU rejects that node-count request at Livy admission —
it never gets far enough to run. This matches a Microsoft Fabric Community thread ("PYSPARK
notebook issue", KUMARCH) reporting the **identical** symptom (HTTP 430
`TooManyRequestsForCapacity`, near-zero usage meter, instant pre-executor failure) on Trial
capacity, with the same accepted fix from two independent users.

The default Starter Pool is sized for a paid F64+ capacity, **not** for the throttled Trial tier.
The mismatch — oversized default pool vs. a Trial-tier admission ceiling — is the defect.

## Decision
Create a **custom, Small, autoscale-disabled, single-fixed-node** Spark pool and set it as the
**workspace default**. Do NOT run notebooks against the Starter Pool on this Trial capacity.

**Exact pool spec (the binding spec — do not drift from it):**
```json
{
  "name": "SmallFixedPool",
  "nodeFamily": "MemoryOptimized",
  "nodeSize": "Small",
  "autoScale":                 { "enabled": false, "minNodeCount": 1, "maxNodeCount": 1 },
  "dynamicExecutorAllocation": { "enabled": false, "minExecutors": 1, "maxExecutors": 1 }
}
```

**Applied live (real API calls, J-019):**
- `POST workspaces/{id}/spark/pools` with the body above → `201`, pool created
  (`id: 18c24a87-e291-477c-b74c-5dc2837d6595`).
- `PATCH workspaces/{id}/spark/settings` with
  `{"pool":{"defaultPool":{"name":"SmallFixedPool","type":"Workspace","id":"18c24a87-e291-477c-b74c-5dc2837d6595"}}}`
  → `200`, confirmed via a follow-up `GET .../spark/settings` that `defaultPool` now points at
  `SmallFixedPool` (not the Starter Pool) **before** any job was submitted — persisted, not assumed.

**Result — first success in 8 attempts:** retry attempt 8 (`nb_bronze_ingest`, job
`c91bcee4-f5d3-4824-810e-0ef2a091a276`) ran `NotStarted → InProgress → Completed`, ~9.5 minutes of
real Spark execution, **no throttle error at any point**. Bronze materialized all 7 `bronze_*`
Delta tables with exact row-count parity to the source CSVs (307,511 / 1,716,428 / 27,299,925 /
1,670,214 / 13,605,401 / 10,001,358 / 3,840,312) — **Gate 2 condition G1 PASSED** against real
Fabric compute (`migration/governance/SIGN_OFF.md`, `MIGRATION_JOURNEY.md` J-019).

## MANDATORY going forward (read this before running ANY notebook on `home-credit-risk-dev`)
This is a binding operational constraint, not a one-off note:

1. **Every** Fabric Spark notebook run on the `home-credit-risk-dev` workspace — the 5 Silver
   notebooks, any re-run of Bronze, any throwaway verification notebook — **MUST** execute against
   `SmallFixedPool` (`id: 18c24a87-e291-477c-b74c-5dc2837d6595`).
2. **Do NOT revert the workspace default to the Starter Pool**, and do NOT create a
   larger/autoscaling pool, while this workspace runs on the FTL4 Trial capacity. Doing so
   reintroduces the exact HTTP 430 `TooManyRequestsForCapacity` admission failure that cost 7
   attempts to diagnose.
3. **Verify before submitting.** Before the first `RunNotebook` of a session, confirm the default
   is still `SmallFixedPool`: `GET workspaces/{id}/spark/settings` → `pool.defaultPool.name ==
   "SmallFixedPool"`. If it has drifted back to the Starter Pool, re-apply the `PATCH` above
   before spending CU on a job that will otherwise fail at admission.
4. **Trial-tier only.** This sizing is a workaround for the Trial capacity's admission ceiling, not
   a permanent architectural choice. If/when the workspace is moved to a paid F-SKU with real
   Spark-VCore headroom (ADR-010 D4), the pool sizing should be re-evaluated for the 27M-row
   `bureau_balance` table against the parent repo's AWS Glue G.1X×2 headroom baseline
   (`migration/benchmarks/INFRA_BASELINE.md`, @infra-reality-agent) — a single Small node may be a
   throughput floor, not a target, at full scale. Revisiting is a new ADR / amendment, not a
   silent change here.

## Scope — what this ADR does and does NOT change
- **Refines `docs/ADR/ADR-006-fabric-native-service-mapping.md` §3** ("Silver transform
  compute") — it pins the **pool sizing** that §3 left unspecified (§3 chose *Fabric Spark
  Notebooks on Runtime 1.3*; it never sized the pool those notebooks run on). ADR-006 §3 is
  refined by reference, **not reversed**: the engine, notebook count, and Delta-MERGE approach are
  all unchanged. The refinement breadcrumb is placed in the `docs/ADR/` copy of ADR-006 (the
  `migration/ADR/` copy stays frozen as the pre-migration record, per the ADR-011 precedent).
  Mirrors how ADR-011 refined §2 and ADR-008 exercised §4.
- **Does NOT touch grain / SCD2 / identity** (ADR-001 / ADR-008 unchanged) — this is a
  compute-sizing decision, no @data-architect veto surface.
- **Does NOT reopen the stack** — a Spark pool is native Fabric Spark compute inside the existing
  workspace; no new service, no new connector, no relaxation of FB1–FB8. Spark still runs only
  inside `notebooks/` (FB6).
- **Does NOT change the notebook code** — `notebooks/*.py` transform logic is untouched; the pool
  is a workspace-level runtime setting, not a code artifact.

## Consequences
**(+)** Clears the Trial-tier Livy-admission throttle — real Spark execution is possible on the
  free Trial capacity, so Gate 2 (G1–G5, G8) can be worked without spending the $200 paid credit.
**(+)** Single fixed Small node keeps CU draw minimal and predictable (@finops-agent): ~9.5 min for
  full-scale Bronze across all 7 tables; no autoscale surprise. Real billed CU is still unverified
  against a Capacity Metrics API in this sandbox — wall-clock logged in `COST_LOG.md` instead.
**(−)** A single Small node is a modest amount of compute. Bronze at full scale ran fine (~9.5 min),
  but the 27M-row `bureau_balance` Silver transform is the real memory-pressure test
  (`migration/benchmarks/INFRA_BASELINE.md`) — if a Silver notebook OOMs or runs unacceptably long
  on one Small node, the response is **not** to revert to the autoscaling Starter Pool (that
  reintroduces the 430) but to file a follow-up sizing decision (slightly larger fixed pool, still
  within Trial admission limits, or the paid-F-SKU trigger in ADR-010 D4).
**(−)** The pool default is a workspace-level setting outside git — it can be changed in the portal
  or by an API call and is not version-controlled. Condition #3 (verify-before-submit) is the
  guard against silent drift.

## Alternatives Rejected
- **Keep the Starter Pool, wait longer / retry.** Rejected — falsified by 7/7 identical failures
  across gaps up to ~3 days (J-016/017/018). The throttle is structural to the oversized-default /
  Trial-ceiling mismatch, not a transient cooldown.
- **Size up to a paid F-SKU immediately (ADR-010 D4).** Deferred, not rejected outright — it would
  also clear the throttle, but it spends the $200 credit before the free Trial is exhausted, which
  ADR-010 D4 explicitly sequences *last*. The Small-pool fix keeps logic/parity work on the free
  Trial; the paid F-SKU is reserved for genuine full-scale validation.
- **Medium fixed single node (autoscale off, but Medium).** Not needed — the Small fixed node
  already admits and completed full-scale Bronze; escalating node size is a follow-up only if a
  Silver notebook actually proves it necessary (see the second `(−)` above). Start at the smallest
  thing that works.

## Sign-off
Compute-sizing refinement within an already-signed stack decision (ADR-006 §3) — **not a new
gate**, and no grain/model surface, so no @data-architect veto applies. Handled per the ADR-011
refinement precedent (Owner-direct for a within-scope refinement). Recorded here as governance of
record; formal @scope-guardian / @infra-reality-agent persona sign-off is **not** self-stamped in
this session — it is deferred to the Owner to run (or waive, as with ADR-011) rather than
rubber-stamped by the author.
- [ ] **@scope-guardian** — pending (expected clean: native Fabric Spark compute, no FB1–FB8 surface touched).
- [ ] **@infra-reality-agent** — pending (owns the single-Small-node vs. 27M-row `bureau_balance` headroom question above).
- [ ] **Owner** — to confirm or waive per ADR-011 precedent.
