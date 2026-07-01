# Decision Log — Home Credit Risk Pipeline (Fabric)

| Date | Decision | Owner | Reference |
|------|----------|-------|-----------|
| 2026-06-30 | Migrate fully to Microsoft Fabric ecosystem (no AWS, no Snowflake, no standalone Databricks) | Owner + @scope-guardian + @data-architect | `migration/ADR/ADR-005-fabric-full-migration-decision.md` |
| 2026-06-30 | Per-layer Fabric service mapping decided; dbt Core retained as named exception | Owner + @data-architect | `migration/ADR/ADR-006-fabric-native-service-mapping.md` |
| 2026-06-30 | Validation/parity/idempotency protocol defined before any AWS/Snowflake teardown | @senior-data-engineer + @data-architect | `migration/ADR/ADR-007-validation-parity-protocol.md` |
| 2026-06-30 | Governance framework lifted from `fabric-migration/` design folder into a dedicated repo, branch `fabric-framework-init` | Owner | This commit |
| 2026-06-30 | OneLake Delta MERGE adopted for Silver idempotency, replacing the parent repo's Snowpipe COPY-INTO-only workaround | @senior-data-engineer | `docs/ADR/ADR-004-onelake-merge-idempotency.md` |

## Pending decisions
- Gate 0 sign-off (`migration/governance/SIGN_OFF.md`) — required before any real Fabric
  provisioning. Not yet signed by @scope-guardian / @data-architect / @finops-agent / Owner.
- Whether to pursue ADR-006's "Option B" (zero-third-party native rebuild, no dbt) if the
  owner decides "Fabric-only" should be read literally rather than pragmatically.
