# Migration Sign-Off Register

> Every gate row must be **positively signed** before the work it guards proceeds.
> "Not yet started" is not a sign-off. An unsigned gate blocks the next gate.
> Pattern mirrors the parent repo's ADR sign-off convention
> (`docs/ADR/ADR-004-snowpipe-silver-gold-bridge.md:183-193`).

## Gate 0 — Design Approval (required before any Fabric provisioning)
Nothing gets provisioned, no Fabric workspace created, no CU capacity committed, until
Gate 0 is fully signed. ADR-005 stays Proposed until all four boxes below are checked.

| Role | Sign-off required | Status | Date | Notes |
|---|---|---|---|---|
| @scope-guardian | ADR-005 scope does not creep beyond what's listed; `tests/boundary_contract.py` in parent repo stays green throughout dual-run | ☑ Signed | 2026-07-01 | Contract passes clean, no banned platforms reintroduced, Spark confined to `notebooks/`. APPROVE. |
| @data-architect | Kimball grain/SCD2 design genuinely survives the re-platform unchanged (verify ADR-006 Gold-layer mapping) | ☑ Signed | 2026-07-01 | Grain/SCD2 verified 1:1 against DATA_MODEL.md. APPROVE (conditional — dim_loan_type/dim_credit_status not yet built, tracked as follow-up). |
| @finops-agent | Fabric CU cost estimate vs. `benchmarks/COST_BASELINE.md` current spend is acceptable | ☑ Signed | 2026-07-01 | F2 (~$262/mo) vs ~$0.19 lifetime baseline is a real cost increase, not a saving. Owner has a $200 USD Fabric trial credit, covering ~76% of month one; accepted with pause/deallocate-when-idle expectation. See ADR-005 sign-off for full reasoning. |
| Owner | Final go/no-go, single-dev portfolio project decision | ☑ Signed | 2026-07-01 | GO — accepts finops trade-off in exchange for Fabric-native consolidation/portfolio narrative. |

**Gate 0 outcome:** ☑ SIGNED 2026-07-01 — ADR-005 status = Accepted. Framework/governance
code authorised to merge to main. Real Fabric provisioning still requires Gate 1 below.

---

## Gate 0.5 — Option B Design Amendment (ADR-008 + ADR-009)
Post-Gate-0 amendment: the Owner ruled "Fabric-only" **absolute**, exercising ADR-006 §4's
pre-authorised "Option B" (retire dbt → Fabric Warehouse T-SQL) and adding capacity-lifecycle
automation. This materially amends the Gate-0 ADR-005/006 decisions, so it carries its own
sign-off. ADR-008 + ADR-009 stay **Proposed** until all boxes below are checked. See
`MIGRATION_JOURNEY.md` J-002…J-008 for the full trail.

| Role | Sign-off required | Status | Date | Notes |
|---|---|---|---|---|
| @data-architect | ADR-008 preserves grain/SCD2/identity; C1–C8 present in drafted text | ☑ Signed | 2026-07-01 | APPROVE of drafted text; C1–C8 verified line-by-line. Signature contingent on the C3 NULL-safe + C4 invariant + C5 atomicity side-by-side dbt proof landing in the build PR. |
| @scope-guardian | ADR-008 (dbt retire, FB5) + ADR-009 (FB7 carve-out) are scope-compliant | ☑ Signed | 2026-07-01 | APPROVE both. FB7 widened to "capacity-lifecycle control-plane actions only" re-confirmed; hard-cap 3 actions / 1 resource; no banned platform reintroduced. |
| @finops-agent | ADR-009 satisfies the Gate-0 pause condition; cost acceptable | ☑ Signed | 2026-07-01 | APPROVE. Pause condition satisfied by automation. Billing-increment + early CU-logging carried forward as pre-build verification items. Economic case watchdog+kill-switch-dependent, accepted. |
| Owner | Final go/no-go on the Option B pivot | ☑ Signed | 2026-07-01 | GO — Option B pivot authorised (retire dbt → Warehouse T-SQL; capacity lifecycle automation). |

**Gate 0.5 outcome:** ☑ SIGNED 2026-07-01 — ADR-008/009 = Accepted. Build-phase execution
(same-PR checklist in ADR-008) authorised. Real Fabric provisioning still requires Gate 1.

---

## Gate 1 — New Repo + Contract Setup (required before any Fabric code is written)
After Gate 0 is signed:
- New dedicated repo created (`home-credit-fabric` or equivalent).
- `fabric-migration/` folder from this parent repo lifted into the new repo root.
- `governance/boundary_contract_fabric.py` wired into `.claude/hooks/` and CI.
- All 4 parent repo contracts still passing in the parent repo (no side-effects from
  branch work on the parent).

| Condition | Evidence | Status |
|---|---|---|
| New repo initialised, `fabric-migration/` contents committed | GitHub repo URL | ☐ Pending |
| `boundary_contract_fabric.py` exits 0 in CI | CI run link | ☐ Pending |
| Parent `tests/boundary_contract.py` still exits 0 | Parent CI run link | ☐ Pending |
| ADR-005 status updated to **Accepted** in new repo | Commit hash | ☐ Pending |

**Gate 1 outcome:** ☐ OPEN

---

## Gate 2 — Fabric Silver Parity (required before Gold/mart work begins)
All 7 Silver tables must pass Tiers 1–5 of ADR-007's parity protocol before any
dbt-fabric mart model is run. PII mask check (Tier 4) must pass before any Gold run.

| Condition (ADR-007 reference) | Evidence | Owner | Status |
|---|---|---|---|
| G1: All 7 Silver tables row-count match baseline | `parity_check.py` output | @senior-data-engineer | ☐ Pending |
| G2: PK uniqueness on all keyed Silver tables | `parity_check.py` output | @senior-data-engineer | ☐ Pending |
| G3: Null-PK count = 0 on all keyed Silver tables | `parity_check.py` output | @senior-data-engineer | ☐ Pending |
| G4: silver_application PII mask verified | Notebook assertion log | @data-quality-steward | ☐ Pending |
| G5: Dedup counts match for bureau_balance + installments | `parity_check.py` output | @senior-data-engineer | ☐ Pending |
| G8: Idempotency re-run test passes | `parity_check.py --idempotency` output | @senior-data-engineer | ☐ Pending |

**Gate 2 outcome:** ☐ OPEN

---

## Gate 3 — Fabric Gold/Mart Parity (required before any cutover planning)
dbt-fabric run complete, mart tables + SCD2 snapshot verified against the Kimball design.

| Condition (ADR-007 reference) | Evidence | Owner | Status |
|---|---|---|---|
| G6: Gold mart tables in Fabric Warehouse, same grain as Snowflake equivalents | dbt run output + row counts | @data-architect | ☐ Pending |
| G7: SCD2 snapshot — exactly 1 is_current=TRUE row per applicant | dbt test output (equivalent of `assert_scd2_one_current_per_applicant.sql`) | @data-architect | ☐ Pending |

**Gate 3 outcome:** ☐ OPEN

---

## Gate 4 — End-to-End Validation + Alerting (required before cutover authorised)
Full pipeline run in Fabric, alerting live, BI confirmed.

| Condition (ADR-007 reference) | Evidence | Owner | Status |
|---|---|---|---|
| G9: Data Activator + Teams alert fires on simulated failure | Screenshot/Teams message log | @data-platform-engineer | ☐ Pending |
| G10: Power BI Direct Lake report loads without error | Report screenshot + semantic model log | Owner | ☐ Pending |
| G11: Fabric CU cost post-first-run within estimate from Gate 0 | CU usage screenshot from Fabric admin | @finops-agent | ☐ Pending |
| G12: `boundary_contract_fabric.py` exits 0 in new repo CI | CI run link | @scope-guardian | ☐ Pending |

**Gate 4 outcome:** ☐ OPEN

---

## Gate 5 — AWS/Snowflake Teardown Authorisation
**Nothing below gets executed until all of Gates 1–4 show CLOSED.**
Teardown is irreversible. The dual-run plan (`staging/DUAL_RUN_PLAN.md`) governs the
parallel-run period between Fabric being proven and the old stack being switched off.

| Resource to decommission | Teardown action | Pre-condition | Owner | Status |
|---|---|---|---|---|
| Dev Snowpipe (4 pipes) | `DROP PIPE` ×4 + remove S3 event notification on `home-credit-risk-dev-1` | Gate 4 CLOSED + ADR-004 rescoped teardown re-confirmed | Owner | ☐ Pending |
| `snowflake_silver_loader` IAM inline policy | Narrow to remove `home-credit-risk-dev-1/silver/*` only — do NOT remove `home-credit-risk-staging/silver/*` entry per `ADR-004:148-163` correction | Gate 4 CLOSED | Owner | ☐ Pending |
| Snowflake schemas (DEV, STAGING) | `DROP SCHEMA` after Fabric Gold confirmed | Gate 3 + Gate 4 CLOSED | Owner | ☐ Pending |
| AWS Glue jobs (5) | `glue.delete_job()` ×5 | Gate 2 CLOSED | Owner | ☐ Pending |
| S3 buckets (`home-credit-risk-dev-1`, `-staging`) | Empty + delete, after Glue jobs deleted | Gate 2 CLOSED + S3 contents archived/not needed | Owner | ☐ Pending |
| Airflow standalone instance | Kill process, remove `airflow/` virtualenv | Gate 4 CLOSED | Owner | ☐ Pending |

**Gate 5 outcome:** ☐ OPEN — gates 1-4 must all show CLOSED first.

---

## Sign-off log (append-only once gates start closing)
_No entries yet — all gates Pending as of 2026-06-30 design pass._
