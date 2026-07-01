# ADR-001: Data Modelling Paradigm — Kimball Star Schema

Status: Accepted (carried forward from parent repo, unchanged by the Fabric migration)
Date  : 2026-05-12 (parent repo); re-affirmed 2026-06-30 per ADR-005 "re-platform, not re-grain"
Owner : Data Architect + Data Platform Engineer

## Context
Home Credit dataset: 7 CSV files, 300k+ applicants, analytics use case. This decision predates
the Fabric migration and is explicitly out of scope for it — see
`migration/ADR/ADR-005-fabric-full-migration-decision.md` "Scope (out)".

## Decision
Paradigm: Kimball — Star Schema

## Consequences
(+) Standard analytics pattern — joins manageable in Fabric Spark notebooks
(+) Fabric Warehouse query cost predictable
(+) SCD Type 2 directly proves resume bullet point
(-) More joins vs OBT
(-) bureau_balance (27M rows) needs careful partitioning

## Alternatives Rejected
OBT: rejected — bureau_balance 27M rows + installments 13M rows nested Array/Struct = memory
risk on any bounded Spark node pool, Fabric or otherwise. Sizing math in ADR-003.
