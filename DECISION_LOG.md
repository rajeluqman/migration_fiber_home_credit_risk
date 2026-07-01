# Decision Log — Home Credit Risk Pipeline (Fabric)

| Date | Decision | Owner | Reference |
|------|----------|-------|-----------|
| 2026-06-30 | Migrate fully to Microsoft Fabric ecosystem (no AWS, no Snowflake, no standalone Databricks) | Owner + @scope-guardian + @data-architect | `migration/ADR/ADR-005-fabric-full-migration-decision.md` |
| 2026-06-30 | Per-layer Fabric service mapping decided; dbt Core retained as named exception | Owner + @data-architect | `migration/ADR/ADR-006-fabric-native-service-mapping.md` |
| 2026-06-30 | Validation/parity/idempotency protocol defined before any AWS/Snowflake teardown | @senior-data-engineer + @data-architect | `migration/ADR/ADR-007-validation-parity-protocol.md` |
| 2026-06-30 | Governance framework lifted from `fabric-migration/` design folder into a dedicated repo, branch `fabric-framework-init` | Owner | This commit |
| 2026-06-30 | OneLake Delta MERGE adopted for Silver idempotency, replacing the parent repo's Snowpipe COPY-INTO-only workaround | @senior-data-engineer | `docs/ADR/ADR-004-onelake-merge-idempotency.md` |
| 2026-07-01 | "Fabric-only" ruled ABSOLUTE — retire dbt entirely; Gold/mart = Fabric Warehouse T-SQL stored procs (exercises ADR-006 §4 Option B). Gate 0.5 signed | Owner + @data-architect + @scope-guardian | `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` |
| 2026-07-01 | SCD2 engine = A1 (T-SQL MERGE proc; 2-step UPDATE-expire+INSERT fallback); tracked cols + one-current invariant preserved 1:1 | Owner + @data-architect | `docs/ADR/ADR-008-retire-dbt-warehouse-tsql.md` |
| 2026-07-01 | Capacity lifecycle automation — nightly batch, Azure-native resume, in-Fabric suspend/watchdog + daily kill-switch; FB7 carve-out. Gate 0.5 signed | Owner + @scope-guardian + @finops-agent | `docs/ADR/ADR-009-capacity-lifecycle-automation.md` |

## Pending decisions
- Gate 0 — ☑ SIGNED 2026-07-01. Gate 0.5 (Option B pivot, ADR-008/009) — ☑ SIGNED 2026-07-01.
- ADR-006 §4 "Option B" — DECIDED 2026-07-01 (Owner ruled Fabric-only absolute; dbt retired).
- **Next: build phase** (ADR-008 same-PR checklist), then Gate 1 before any real Fabric
  provisioning. Four items stay (unverified) until a real workspace exists: Fabric Warehouse
  MERGE maturity, Spark pool memory vs the 27M-row baseline, idempotency re-run equivalence,
  PII order under native `sha2()`.
