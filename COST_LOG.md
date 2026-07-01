# Cost Log — Home Credit Risk Pipeline (Fabric)

> Owner: @finops-agent. Estimate-only — never real account-linked $ figures in committed files.

## Pre-migration baseline (parent repo, real spend)
See `migration/benchmarks/COST_BASELINE.md` for the full AWS + Snowflake baseline this
migration must compare against before Gate 0 sign-off (`migration/governance/SIGN_OFF.md`
condition: "@finops-agent — Fabric CU cost estimate vs. benchmarks/COST_BASELINE.md current
spend is acceptable").

## Fabric cost surface (post-migration, not yet measured)
| Surface | Status |
|---------|--------|
| Fabric capacity unit (CU) consumption per notebook/pipeline run | Not yet measured — no Fabric workspace provisioned |
| OneLake storage growth (Bronze + Silver + Gold Delta) | Not yet measured |
| dbt-fabric Warehouse query CU usage | Not yet measured |

## Eliminated cost lines (confirmed by the migration decision, ADR-005/006)
- AWS (S3 + Glue DPU-hours) — eliminated
- Snowflake compute credits — eliminated
- Databricks Serverless SQL — eliminated

**No entries below this line yet** — this log populates once a real Fabric workspace exists
and the first notebook/pipeline run produces an actual CU consumption number.
