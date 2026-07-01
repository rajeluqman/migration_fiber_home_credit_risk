# Cost Baseline — Pre-Migration Economics

> Real figures from `COST_LOG.md` (parent repo). These are the "before" numbers.
> @finops-agent's Gate 0 sign-off condition (governance/SIGN_OFF.md Gate 0, row 3) is
> a Fabric CU cost estimate that is acceptable COMPARED TO these numbers, not just in
> isolation. Every figure here is cited back to a source.

## AWS costs to date (2026-06-30)

| Item | Amount | Basis | Source |
|---|---|---|---|
| AWS Glue — all Phase-2 full-scale runs (1,017 DPU-sec) | **≈$0.124** | ~$0.44/DPU-hr estimate | `COST_LOG.md` Phase-2 entry |
| AWS Glue — CloudWatch metrics re-run (502 DPU-sec) | **≈$0.061** | same basis | `COST_LOG.md` final entry |
| **Total Glue compute** | **≈$0.186** | — | — |
| S3 storage (landing + Bronze + Silver, ~6.5 GB across buckets) | **~$0** | within/near free tier | `INFRA_LIMITS_LOG.md` |
| IAM / CloudWatch / SQS | **~$0** | metadata only, no per-request cost at this scale | `COST_LOG.md` |
| **Total AWS to date** | **≈$0.186** | — | estimate only, not from AWS Billing console |

## Snowflake costs to date (2026-06-30)

| Item | Amount | Basis | Source |
|---|---|---|---|
| Dev Snowpipe (4 pipes) — all-time credit consumption | **8.4×10⁻⁸ credits** (≈$0.0000003) | `PIPE_USAGE_HISTORY` SELECT, `role=ACCOUNTADMIN` | `COST_LOG.md` + `PROJECT_STATUS.md` ~1361-1368 |
| Silver→Snowflake STAGING COPY INTO (4 tables, ~20s, `HOME_CREDIT_WH` X-Small) | **effectively $0** | well under 1-min minimum billing increment | `COST_LOG.md` STAGING bridge entry |
| dbt Gold run (HOME_CREDIT_WH X-Small) | not separately itemised | sub-minute, effectively $0 | `PROJECT_STATUS.md` gate sections |
| **Total Snowflake to date** | **≈$0** | — | — |

## What this baseline tells the Fabric CU estimate

The entire pipeline (58.4M rows, Bronze+Silver+Gold, all GX suites, all gate runs) was
proven on the current stack for **under $0.20 total real spend**. This is a portfolio
project on free-tier / near-zero infrastructure — the economics comparison for Fabric is
therefore not "cheaper than a $500/month production stack"; it is:

> "Does Fabric's CU-based pricing make sense for a proof/portfolio workload at this scale,
> or does the CU commitment charge more than the pay-per-use AWS/Snowflake cost did?"

The current free-tier structure means AWS/Snowflake is essentially free at proof scale.
Fabric is not pay-per-use in the same way — a Fabric capacity (F2 minimum) costs a flat
monthly fee (~$262/month as of 2026) regardless of whether you run 1 job or 10,000.
@finops-agent's Gate 0 condition must weigh this CU-vs-free-tier trade-off explicitly:
for a portfolio project, Fabric's value is the breadth-of-ecosystem demonstration and
Power BI Direct Lake, not cost savings over an already-nearly-free baseline.

## Ongoing cost accruals (not yet shut down as of 2026-06-30)
Source: `PROJECT_STATUS.md` ~1613-1619: "ADR-004 dev-Snowpipe teardown deferred again —
owner wants to capture screenshots of live AWS/Snowflake infra first."

| Item | Status | Ongoing cost risk |
|---|---|---|
| 4 dev Snowpipe objects (`PIPE_SILVER_*`) | ARMED, not yet torn down | Near-zero (8.4×10⁻⁸ credits total all-time, no new auto-fire since Gate-1 test) |
| `HOME_CREDIT_SILVER_INT` storage integration | Active, policy widened to staging | Near-zero metadata cost |
| `HOME_CREDIT_WH` (X-Small) | Active, auto-suspend 60s idle | Near-zero (only billed when active) |
| S3 buckets (`dev-1`, `staging`) | Non-empty, ~6.5 GB | Within / just over 5 GB free tier; marginal overage cost |

These accruals are part of Gate 5 teardown in `governance/SIGN_OFF.md` — they get cleaned
up as part of the Fabric cutover, not before Fabric parity is proven.
