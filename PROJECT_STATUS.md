# Project Status — Home Credit Risk Pipeline (Fabric)

## ▶ RESUME HERE
**Where we are (2026-07-02, `gate-0.5-option-b-adr-008-009`):** Gate 2 infra provisioning is
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

**Next action:** port the 5 Silver notebooks (`glue/glue_silver_*.py` in the parent repo) into
`tests/local/` under FB8 — dialect review per ADR-004/ADR-006 §3, proven locally (PySpark +
delta-spark) before touching the Trial Warehouse. Then run ADR-007 Tier 0 (local pre-parity
sample) before spending any real CU. Gate 2's actual conditions (G1-G5, G8 in
`migration/governance/SIGN_OFF.md`) stay ☐ Pending until that produces parity evidence — today's
work provisioned the infra, it did not run any Silver logic against it.

**Do NOT:** leave the Fabric Trial capacity running between sessions — pause/deallocate it; the
day-60/61 expiry behaviour is still (unverified), unchanged by today's provisioning.

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
