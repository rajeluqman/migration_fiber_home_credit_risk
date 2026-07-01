# ADR-009: Fabric Capacity Lifecycle Automation — Nightly Batch, Azure-Native Resume, In-Fabric Suspend + Watchdog + Daily Kill-Switch

**Status:** **Accepted 2026-07-01** (Gate 0.5 signed — @scope-guardian + @finops-agent + Owner;
`migration/governance/SIGN_OFF.md`). Finops billing-increment + early CU-logging carried forward
as pre-build verification items.
**Date:** 2026-07-01
**Owner:** Raja Ahmad Luqman (single-dev).
**Design-gate review:** @scope-guardian + @finops-agent both APPROVE-conditional 2026-07-01
(`MIGRATION_JOURNEY.md` J-006). One cross-reviewer tension is flagged for joint reconciliation
(see "Open reconciliation" below).

## Context
A Fabric F2 capacity bills a **flat rate (~$262/month per `migration/benchmarks/COST_BASELINE.md`)
whenever it is Running**, regardless of usage. @finops-agent's Gate-0 approval was explicitly
conditional on "F-SKU capacity paused/deallocated between work sessions, not left running
continuously" (`migration/governance/SIGN_OFF.md`). The Owner has a $200 USD Azure/Fabric trial
credit and accepts that serving (Power BI Direct Lake / SQL Analytics Endpoint) goes cold while
the capacity is paused.

**The chicken-and-egg constraint (J-005):** a suspended F-capacity cannot be resumed from inside
Fabric — the Data Factory scheduler runs *on* that same capacity, so it is dead too. The first
`/resume` call must therefore originate from **outside** Fabric.

## Decision
Run the pipeline as a **nightly batch (~00:00, bank-sleep window, ~1h)** with a capacity that is
paused ~22.5 hours/day:

1. **Resume — Azure-native, outside Fabric.** Locked mechanism: **one Azure Logic App
   (Consumption tier)** with a 00:00 recurrence trigger → ARM REST `/resume` on the named
   F-capacity → then triggers the named Data Factory pipeline. (Automation runbook / Function
   timer were the alternatives — one mechanism is locked per @scope-guardian; a change requires an
   ADR amendment.)
2. **Batch — inside Fabric.** Data Factory pipeline: Bronze → Silver → Gold → DQ THROW gates.
3. **Suspend — inside Fabric.** Final Data Factory activity calls `/suspend` (capacity is still
   live at that moment) + posts a Teams alert "batch done, compute OFF".
4. **Watchdog — inside Fabric.** A Fabric-scheduled pipeline (every 15–30 min) force-suspends the
   capacity if it is found Running outside the 00:00–01:30 window + Teams alert.
5. **Daily kill-switch — outside Fabric.** An unconditional daily force-suspend (hosted on the same
   external Azure component as the resume) as a second, independent layer in case the in-Fabric
   watchdog cannot fire (see @finops-agent failure mode below).
6. **Budget — notify-only.** Azure Cost Management budget alerts (50/80/100% → Teams). This is
   reactive notification, **not** a control; the watchdog + kill-switch are the actual controls.

**Auth:** Managed Identity / Service Principal with Contributor scoped narrowly to the capacity
resource only. No secrets/API keys in the repo; no third-party secrets manager.

## Scope carve-out — FB7 (from @scope-guardian)
"Fabric-only" is relaxed to **"Fabric-only data plane + one minimal Azure-native control-plane
component for capacity lifecycle"** — still zero third-party (all Microsoft/Azure). A new boundary
rule fences it:

> **FB7** — the ONLY permitted component outside the Fabric workspace boundary is the single
> capacity-lifecycle control-plane component named in ADR-009 (one Logic App, calling ARM
> `/resume` + `/suspend` + triggering one named Data Factory pipeline — control-plane only,
> nothing touching data). Any other external Azure infra file/resource must cite ADR-009 or is
> presumed scope creep, and remains subject to the FB1–FB4 bans (no AWS/Snowflake/Airflow/Slack).

If a new `automation/` or `infra/` directory appears, it must contain only resume/suspend/trigger
logic, import no non-Azure SDK, and be reviewed against FB7.

## Open reconciliation (@scope-guardian ↔ @finops-agent) — resolve at final sign-off
@scope-guardian capped the external component at **exactly two actions** (resume + trigger).
@finops-agent requires a **daily unconditional kill-switch outside Fabric** (a third action) as
insurance, because an in-Fabric watchdog cannot fire if the capacity is wedged at 100% CU.
**Proposed resolution:** allow the single external component to perform **capacity-lifecycle
control-plane actions only** (resume, suspend, trigger-pipeline) — still zero data, zero business
logic, so it honours the spirit of the two-action cap while closing the finops single-point-of-
failure. This widening of FB7 needs @scope-guardian's explicit re-confirmation.

## Conditions (from @finops-agent — pre-Gate-1-build verification items)
- Confirm the watchdog's execution channel fires **independent of capacity health** (else it is
  subject to the same J-005 chicken-and-egg bug as resume). If Data-Factory-hosted, explain why not.
- Add the daily unconditional hard-stop kill-switch (above) as a second independent layer.
- Log actual CU/hour draw from the first real Fabric run into `COST_LOG.md` before build continues
  at volume — validate the ~$18–22/month happy-path estimate against reality early.
- Confirm the F2 **minimum billing increment** (per-second vs. per-minute vs. coarser) — it
  materially changes the estimate at this small a footprint. Currently **unverified**.
- Track build-time CU (parity/idempotency test cycles outside the nightly window, ADR-007)
  separately from steady-state nightly CU in `COST_LOG.md`.

## Cost estimate (happy path — estimate, not billed)
~1.5h/day at F2 flat-rate-prorated ≈ **$16–22/month** (capacity + negligible Logic App + <$1
OneLake storage) → **~9–10 months of runway** on the $200 credit — better than the Gate-0 sizing
($62/month out-of-pocket), because true 1h/day usage is far cheaper than near-continuous running.
**This entire case rests on the watchdog + kill-switch never both failing**; one missed suspend at
full F2 run-rate can burn the credit in under a month.

## What this is NOT
Not a reopening of orchestration — Data Factory remains the orchestrator for all data movement
(FB3 still bans Airflow). Not a general-purpose external Functions app for pipeline logic. Not a
precedent for moving Fabric-internal logic outside Fabric — only capacity lifecycle, which has the
logical necessity. No data, no PII, no transformation ever touches the external component.

## Consequences
**(+)** Satisfies the @finops-agent Gate-0 pause condition as automation, not manual discipline.
**(+)** Capacity paused ~22.5h/day → the $200 credit stretches to months, not weeks.
**(−)** Serving is cold when idle (accepted by Owner) — dashboards need a resume before use.
**(−)** One Azure-native control-plane component is introduced — a narrow, fenced (FB7) relaxation
  of strict "Fabric-only", justified by the J-005 logical necessity.
**(−)** The economic case is watchdog/kill-switch-dependent; both are load-bearing, not optional.

## Sign-off (drafted-text review complete 2026-07-01; Owner GO pending)
- [x] **@scope-guardian** — 2026-07-01 APPROVE; FB7 widened to "capacity-lifecycle control-plane
  actions only" explicitly re-confirmed. Hard-cap: these 3 actions on the one named capacity only —
  a 4th action or a 2nd external resource requires a fresh ADR, not an amendment.
- [x] **@finops-agent** — 2026-07-01 APPROVE; Gate-0 pause condition satisfied by design. Billing
  increment + early CU-logging correctly carried forward as pre-build verification items (not yet
  closed — no real workspace exists). Economic case is watchdog+kill-switch-dependent, accepted.
- [x] **Owner** — GO 2026-07-01.
