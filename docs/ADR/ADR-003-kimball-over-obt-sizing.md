# ADR-003: Kimball-over-OBT Sizing Math (Fabric Spark node-pool memory risk)

Status: Accepted (carried forward from parent repo, retargeted to Fabric Spark node-pool sizing)
Date  : 2026-06-28 (parent repo, AWS Glue math); retargeted 2026-06-30 for Fabric
Owner : Data Architect + Infra Reality Agent

## Context
ADR-001 already locked Kimball star schema over One-Big-Table (OBT), citing
"bureau_balance (27M rows) + installments (13M rows) as OBT nested arrays → memory OOM risk on
a bounded Spark node pool" — originally derived against the parent repo's AWS Glue free-tier
ceiling. This ADR carries the arithmetic forward and re-frames it against whatever Fabric Spark
node pool gets provisioned, so a future "why not OBT, it'd save joins" re-litigation has real
numbers to check against.

## The sizing math (parent repo baseline — the number to beat)
Parent repo's AWS Glue job config: **G.1X workers × 2** = 2 workers × 16 GB ≈ **32 GB total
executor memory**. Real run against bureau_balance (27M rows) + bureau (1.7M rows): SUCCEEDED
in 96s, **peak JVM heap 2.90 GB (9% of the 32 GB ceiling)** — see
`migration/benchmarks/INFRA_BASELINE.md` for the full citation trail.

OBT-as-nested-array would require, per `SK_ID_CURR`, collecting:
- `bureau_balance.csv`: 27,299,925 rows total, keyed via `bureau.csv` (1,716,428 rows) →
  averages ~16 balance-history rows per bureau record, themselves fan-out per applicant
- `installments_payments.csv`: 13,605,401 rows, keyed via `previous_application.csv`
  (1,670,214 rows) → averages ~8 installment rows per previous-application record

Collecting these as nested array/struct columns on a 307,511-row `application_train.csv` base
means the **widest rows** (applicants with many bureau records, each with many balance-history
entries) carry a multiplicatively larger in-memory footprint than the table-average suggests —
a small number of "fat" applicant rows can dominate a single Spark partition's memory. This
failure mode is not AWS-Glue-specific — it applies equally to a Fabric Spark node pool sized
with comparable headroom. Kimball avoids this because each table caps its grain (1 row = 1
bureau record / 1 installment record) — no row's memory footprint depends on a *fan-out*, only
deferred Fabric Warehouse-side joins do.

## Decision
Kimball star schema (re-affirmed from ADR-001). Joins deferred to Fabric Warehouse (T-SQL)
compute, which has no comparable node-pool executor-memory ceiling for the join step
(warehouse-scale joins, not in-Spark-executor-memory joins).

## Consequences
(+) Each Silver Fabric Spark notebook (`notebooks/nb_silver_bureau.py`,
    `notebooks/nb_silver_installments.py`, etc.) processes one flat table at a time — bounded
    memory per notebook, independent of any other table's fan-out
(+) Fabric Warehouse absorbs the join cost in Gold
    (`dbt_fabric/models/intermediate/int_bureau_with_balance.sql`,
    `int_installment_payments.sql`) where compute scales independently of the Spark node-pool
    ceiling
(-) More join steps in dbt vs a single denormalized OBT query
(-) The parent repo's 2.90 GB / 32 GB (9%) is a real measured number, not a Fabric-specific
    measurement — @infra-reality-agent must re-verify against the actual Fabric Spark node
    pool once provisioned (`migration/governance/SIGN_OFF.md` Gate 0/1), not assume parity

## Alternatives Rejected
- OBT with nested arrays in Fabric Spark: rejected per the sizing math above.
- Undersized Fabric Spark pool "to save capacity units": rejected — must deliver at least the
  parent repo's proven 9%-of-ceiling headroom; revisit only with @finops-agent +
  @infra-reality-agent sign-off.
