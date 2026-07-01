# OPS Runbook: Home Credit Risk Pipeline (Fabric)
> Status: DRAFT — governance-framework port, pending Phase 5 sign-off

## Monitoring
| Tool | Where |
|------|-------|
| Data Factory | Fabric Workspace → Data Factory → Pipeline runs |
| Fabric Spark Notebook | Fabric Workspace → Notebooks → Run history |
| Purview DQ | Microsoft Purview → Data Catalog → Quality scores |
| Fabric Warehouse | Fabric Workspace → Warehouse → Query history |
| Power BI | Power BI Service → Direct Lake semantic model refresh log |

## Scenarios

### Bronze fail
Check : OneLake Bronze Lakehouse — did the Fabric Notebook ingestion activity complete?
Fix   : Rerun the Kaggle-download Fabric Notebook activity → rerun the Data Factory Bronze
        pipeline

### Silver notebook fail
Check : Fabric Workspace → Notebooks → run output/logs
Fix 1 : Schema mismatch → update Silver notebook
Fix 2 : Node-pool memory limit → resize Spark pool (see `migration/benchmarks/INFRA_BASELINE.md`
        for the parent repo's proven headroom to match)
Rerun : Data Factory → clear failed activity → rerun pipeline

### dbt-fabric test fail
Check : `dbt test` output against Fabric Warehouse
Fix 1 : FK violation → check Silver quarantine
Fix 2 : SCD is_current > 1 per applicant → check `snap_applicant.sql` / `dim_applicant.sql`

## Provisioning a Fabric Workspace (not yet done — Gate 0 unsigned)

This is a placeholder for the real provisioning runbook once
`migration/governance/SIGN_OFF.md` Gate 0 is signed. Expected steps once that happens:

1. Create Fabric Workspace, assign F-SKU capacity.
2. Create OneLake Lakehouse items (Bronze, Silver, Gold).
3. Create a Fabric Warehouse for Gold, configure `dbt_fabric/profiles.yml` `type: fabric`
   pointing at its SQL endpoint.
4. Register a Microsoft Entra ID service principal (`AZURE_CLIENT_ID`/`AZURE_CLIENT_SECRET`)
   with Contributor role on the workspace — see `.env.example`.
5. Create the 3 chained Data Factory pipelines per `docs/PIPELINE_SPEC.md` §5.
6. Wire Teams webhook / Data Activator reflex actions for pass/fail alerting.

Do NOT provision any of the above until Gate 0 in `migration/governance/SIGN_OFF.md` shows
all four sign-off boxes checked.
