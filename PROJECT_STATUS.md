# Project Status — Home Credit Risk Pipeline (Fabric)

## ▶ RESUME HERE
**Where we are (2026-06-30, `fabric-framework-init` branch):** Full governance-framework port
from the parent repo `home-credit-pipeline` is complete — CLAUDE.md, 3 static contracts, 11
agents, 8 docs, ADR-001..004 (Fabric versions), `scripts/gen_repo_map.py`,
`architecture/REPO_MAP.md`, root logs, `learning/`, `.github/workflows/ci.yml`, `dbt_fabric/`
stubs, and `migration/` (the pre-migration design record: ADR-005/006/007, benchmarks, parity
plan, sign-off gates, copied verbatim from the parent repo's `fabric-migration/` folder).

**What has NOT happened:** no Fabric workspace provisioned, no OneLake Lakehouse created, no
Fabric Spark notebook has run against real data, no dbt-fabric build has executed against a
real Fabric Warehouse. `migration/governance/SIGN_OFF.md` Gate 0 is unsigned — this is the
prerequisite for any real provisioning.

**Next action:** Owner (or @scope-guardian + @data-architect + @finops-agent) signs Gate 0 in
`migration/governance/SIGN_OFF.md`. Only after that: create the real Fabric workspace (Gate 1),
port the 5 Silver notebooks from the parent repo's `glue/glue_silver_*.py` (dialect review per
ADR-004/ADR-006 §3), then the dbt-fabric Gold models (T-SQL dialect review per ADR-006 §4).

**Do NOT:** provision any real Fabric resource before Gate 0 is signed. Do NOT assume a Fabric
Spark node pool sized smaller than the parent repo's proven AWS Glue G.1X×2 headroom
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
