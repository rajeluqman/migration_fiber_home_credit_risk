# Project Status — Home Credit Risk Pipeline (Fabric)

## ▶ RESUME HERE
**Where we are (2026-07-01, `main`, PR #1 merged):** Full governance-framework port from the
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

**Next action is now the BUILD PHASE** (ADR-008 "Same-PR execution checklist"), NOT Gate 1
directly: create `warehouse/` T-SQL tree, retire `dbt_fabric/`, rewrite boundary contract FB5
(dbt-absence) + add FB7, amend DATA_MODEL/CLAUDE/ARCHITECTURE in the same PR, fix the pre-existing
doc-reference drift (2 violations at ADR-005:92) + the mis-stated contract-status line below,
regenerate REPO_MAP. This is Sonnet-appropriate spec-driven work against the frozen ADRs. Gate 1
(real Fabric provisioning) still follows and is still unsigned. Full trail: `MIGRATION_JOURNEY.md`
J-001…J-009.

**What has NOT happened:** no Fabric workspace provisioned, no OneLake Lakehouse created, no
Fabric Spark notebook has run against real data, no dbt-fabric build has executed against a
real Fabric Warehouse. `.env.example` lists the vars a real workspace will need
(`FABRIC_WORKSPACE_ID`, `FABRIC_LAKEHOUSE_ID`, `AZURE_TENANT_ID`/`AZURE_CLIENT_ID`/
`AZURE_CLIENT_SECRET`, `ONELAKE_ENDPOINT`) — none are populated with real values yet.

**Next action — Gate 1 (New Repo + Contract Setup)**, per `migration/governance/SIGN_OFF.md`:
this repo itself already satisfies "new dedicated repo created" and "`fabric-migration/`
folder lifted in" (as `migration/`). Remaining Gate 1 conditions: wire
`migration/governance/boundary_contract_fabric.py` into `.claude/hooks/` + CI (currently only
`tests/boundary_contract.py` is wired), and confirm the parent repo's contracts are still green
(no side-effects from this repo's work). Only after Gate 1 is signed: create the real Fabric
workspace/capacity (mind the $200 credit — pause when idle), port the 5 Silver notebooks from
the parent repo's `glue/glue_silver_*.py` (dialect review per ADR-004/ADR-006 §3), then the
dbt-fabric Gold models (T-SQL dialect review per ADR-006 §4).

**Do NOT:** provision any real Fabric resource before Gate 1 is signed. Do NOT leave a real
Fabric capacity running continuously — it burns the $200 trial credit at a flat monthly rate
regardless of usage; pause/deallocate between sessions. Do NOT assume a Fabric Spark node pool
sized smaller than the parent repo's proven AWS Glue G.1X×2 headroom
(`migration/benchmarks/INFRA_BASELINE.md`) is safe without re-verifying against real Fabric
Spark memory behavior.

## Contract status (as of framework-init commit)
- `python tests/boundary_contract.py` — ✅ green
- `python tests/identity_contract.py` — ✅ green
- `python tests/doc_reference_contract.py` — ✅ green
- `python scripts/gen_repo_map.py --check` — ✅ green

## Open items carried forward from `migration/PROJECT_STATUS.md` (design-phase notes)
1. **dbt exception (ADR-006 §4):** dbt Core retained as a named, flagged exception to
   "Fabric-only." If the owner wants zero third-party tooling, ADR-006's "Option B — native
   rebuild" is the fallback and needs its own sign-off.
2. **Purview DQ is catalog-only, not a gate** — the inline notebook assertion is the real gate
   (ADR-006 §5). Do not treat a green Purview DQ scan as equivalent to a passing assertion.
3. **Snowflake STAGING parity baseline is incomplete** — only 4 of 7 Silver tables have a
   captured baseline (`migration/benchmarks/SNOWFLAKE_STAGING_BASELINE.md` gap note). The
   remaining 3 tables' Fabric parity target is not yet established anywhere.
4. Every Fabric-specific resume/interview claim is "(unverified)" until a real parity run
   (`migration/validation/parity_check.py`) passes — see `INTERVIEW_GUIDE.md`.
