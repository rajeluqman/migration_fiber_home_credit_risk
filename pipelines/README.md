# Data Factory Pipelines (real, deployed — Gate 4, J-023)

Real, deployed Fabric Data Factory pipeline JSON, fetched via the item `getDefinition` REST API
(not hand-written) — see `MIGRATION_JOURNEY.md` J-023 for the full build/validation trail.
These files are point-in-time exports for repo visibility; the live Fabric items are the
authoritative source (same relationship `warehouse/*.sql` has to the deployed Warehouse procs).

Chain: `bronze_ingestion` → (`InvokePipeline`) → `silver_transforms` → (`InvokePipeline`) →
`gold_warehouse`. See `docs/PIPELINE_SPEC.md` §5 for the design.

- `bronze_ingestion.json` — `nb_bronze_ingest` (Kaggle → Landing → Bronze), then triggers Silver.
- `silver_transforms.json` — 5 Silver notebooks, **serial** (not the parallel fan-out in
  `docs/PIPELINE_SPEC.md` §5.2 — changed after a real concurrency-limit finding on the
  `SmallFixedPool`'s single fixed node, see J-023), then triggers Gold.
- `gold_warehouse.json` — 4 `Script` activities (`EXEC` the Gold build procs) against the real
  Fabric Warehouse via a `SQL`-type Connection.

Real end-to-end run verified 2026-07-06: Gold row counts (`dim_applicant` 307,511,
`fact_bureau_credit` 1,716,428, `fact_installment_payment` 12,861,994) match the J-022 baseline
exactly, confirming the Data-Factory-triggered rebuild is idempotent.
