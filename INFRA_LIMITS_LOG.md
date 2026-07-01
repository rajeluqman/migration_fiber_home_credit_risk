# Infra Limits Log — Home Credit Risk Pipeline (Fabric)

> Owner: @infra-reality-agent. Every entry is an observed or projected resource ceiling with
> the actual number, not a guess.

## Baseline to beat (parent repo, real measured run)
Full detail: `migration/benchmarks/INFRA_BASELINE.md`.

| Metric | Value | Source |
|--------|-------|--------|
| AWS Glue job config | G.1X × 2 workers ≈ 32 GB total executor memory | Parent repo `README.md` "Stack" table |
| Real run: bureau_balance (27M rows) + bureau (1.7M rows) | SUCCEEDED in 96s | Parent repo real Glue run, `migration/benchmarks/INFRA_BASELINE.md` |
| Peak JVM heap on that run | 2.90 GB (9% of the 32 GB ceiling) | Parent repo CloudWatch metric, cited in `migration/benchmarks/INFRA_BASELINE.md` |
| Real run: installments_payments (13.6M rows) | SUCCEEDED in 90s | Parent repo real Glue run |

**Rule:** the Fabric Spark node pool provisioned for this pipeline must be sized to deliver at
least this proven headroom (9% of ceiling on the largest table). Do not assume a smaller pool
is safe just because Fabric Runtime 1.3 (Spark 3.5) is a newer engine version than Glue 4.0
(Spark 3.3) — re-verify against a real Fabric run before trusting any smaller sizing.

## Fabric-side entries (not yet measured)
No Fabric Spark notebook has run against real data yet. This section populates once
`migration/governance/SIGN_OFF.md` Gate 0 is signed and a real notebook run against the full
58.4M-row dataset (or a representative sample) produces an actual peak-memory number.
